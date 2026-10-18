"""
CoverFlow live demo server.

Serves the demo page at http://localhost:5050 and sends real SMS through Twilio.
Replies are picked up by checking Twilio for new inbound messages every 2 seconds,
so no public URL or webhook is needed.

Setup:  pip install flask twilio python-dotenv
Config: copy .env.example to .env and fill it in
Run:    python app.py
"""
import os
import threading
import time
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory

load_dotenv()

SID = os.getenv("TWILIO_SID", "").strip()
TOKEN = os.getenv("TWILIO_TOKEN", "").strip()
FROM = os.getenv("TWILIO_NUMBER", "").strip()
MARIA = os.getenv("MARIA_PHONE", "").strip()
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true" or not (SID and TOKEN and FROM)

# STAFF_PHONES=sam=+61400000001,priya=+61400000002
STAFF_PHONES = {}
for pair in os.getenv("STAFF_PHONES", "").split(","):
    if "=" in pair:
        sid, num = pair.split("=", 1)
        STAFF_PHONES[sid.strip().lower()] = num.strip()
PHONE_TO_STAFF = {v: k for k, v in STAFF_PHONES.items()}

NAMES = {"sam": "Sam", "priya": "Priya", "leo": "Leo", "grace": "Grace", "noah": "Noah"}

client = None
if not DRY_RUN:
    from twilio.rest import Client
    client = Client(SID, TOKEN)

app = Flask(__name__, static_folder="static")
lock = threading.Lock()


def fresh_state():
    return {
        "open": False,
        "offered": [],          # every staff id offered the shift (on screen and by SMS)
        "winner": None,
        "declined": set(),
        "started_at": None,
        "seen": set(),          # Twilio message SIDs already processed
        "events": [],           # text log shown on the dashboard
    }


state = fresh_state()


def log(text):
    stamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{stamp}] {text}")
    state["events"].append(text)


def sms(to, body):
    if not to:
        return
    if DRY_RUN:
        log(f"(dry run) SMS to {to}: {body}")
        return
    try:
        client.messages.create(to=to, from_=FROM, body=body)
    except Exception as exc:  # keep the demo running if one text fails
        log(f"SMS to {to} failed: {exc}")


def name_of(staff_id):
    return NAMES.get(staff_id, staff_id.title())


def award(staff_id):
    """First valid acceptance wins. Call with the lock held."""
    state["open"] = False
    state["winner"] = staff_id
    log(f"{name_of(staff_id)} accepted first and gets the shift")
    winner_phone = STAFF_PHONES.get(staff_id)
    if winner_phone:
        sms(winner_phone, f"CoverFlow: You're confirmed for today's 7:00am opening shift. Thanks, {name_of(staff_id)}!")
    for other in state["offered"]:
        if other != staff_id and STAFF_PHONES.get(other):
            sms(STAFF_PHONES[other], "CoverFlow: This shift has been filled. Thanks for responding.")
    sms(MARIA, f"CoverFlow: Your 7am opening shift has been covered by {name_of(staff_id)}. No action needed.")


def maybe_escalate():
    """Call with the lock held."""
    if state["open"] and state["offered"] and set(state["offered"]) <= state["declined"]:
        state["open"] = False
        log("Everyone eligible declined. Escalated to Maria")
        sms(MARIA, "CoverFlow: Action needed. Your 7am opening shift is still uncovered. Everyone eligible declined.")


def poll_replies():
    """Check Twilio for new replies every 2 seconds while offers are open."""
    while True:
        time.sleep(2)
        if DRY_RUN or not state["open"]:
            continue
        try:
            msgs = client.messages.list(to=FROM, date_sent_after=state["started_at"], limit=50)
        except Exception as exc:
            print(f"Could not check replies: {exc}")
            continue
        for m in sorted(msgs, key=lambda x: x.date_created or datetime.now(timezone.utc)):
            with lock:
                if m.sid in state["seen"] or m.direction != "inbound":
                    continue
                state["seen"].add(m.sid)
                staff_id = PHONE_TO_STAFF.get(m.from_)
                if not staff_id or staff_id not in state["offered"]:
                    continue
                reply = (m.body or "").strip().upper()
                if not state["open"]:
                    sms(m.from_, "CoverFlow: Thanks! This shift has already been filled.")
                elif reply.startswith("Y"):
                    award(staff_id)
                elif reply.startswith("N"):
                    state["declined"].add(staff_id)
                    log(f"{name_of(staff_id)} declined by SMS")
                    maybe_escalate()


@app.get("/")
def index():
    return send_from_directory("static", "index.html")


@app.get("/api/config")
def config():
    return jsonify(dryRun=DRY_RUN, realStaff=sorted(STAFF_PHONES), maria=bool(MARIA))


@app.post("/api/offer")
def offer():
    staff = [s.lower() for s in (request.json or {}).get("staff", [])]
    with lock:
        state.update(fresh_state())
        state["open"] = True
        state["offered"] = staff
        # small buffer so a reply sent in the same second is not missed
        state["started_at"] = datetime.now(timezone.utc) - timedelta(seconds=5)
        log(f"Offer sent to {len(staff)} eligible staff at once")
    for s in staff:
        if STAFF_PHONES.get(s):
            sms(STAFF_PHONES[s], "CoverFlow: Opening shift today, 7:00am-3:00pm at Harbour Cafe. "
                                 "Reply YES to take it or NO to pass. First YES gets the shift.")
    return jsonify(ok=True)


@app.post("/api/accept")
def accept():
    staff_id = (request.json or {}).get("staff", "").lower()
    with lock:
        if state["open"] and staff_id in state["offered"]:
            award(staff_id)
    return jsonify(ok=True)


@app.post("/api/decline")
def decline():
    staff_id = (request.json or {}).get("staff", "").lower()
    with lock:
        if state["open"] and staff_id in state["offered"]:
            state["declined"].add(staff_id)
            log(f"{name_of(staff_id)} declined on screen")
            maybe_escalate()
    return jsonify(ok=True)


@app.get("/api/status")
def status():
    with lock:
        return jsonify(open=state["open"], winner=state["winner"], declined=sorted(state["declined"]))


@app.post("/api/reset")
def reset():
    with lock:
        state.update(fresh_state())
    return jsonify(ok=True)


if __name__ == "__main__":
    print("CoverFlow demo running at http://localhost:5050")
    print("Mode:", "DRY RUN (no real texts)" if DRY_RUN else f"LIVE SMS from {FROM}")
    print("Real phones:", ", ".join(f"{name_of(k)} {v}" for k, v in STAFF_PHONES.items()) or "none")
    threading.Thread(target=poll_replies, daemon=True).start()
    app.run(host="127.0.0.1", port=5050, debug=False)
