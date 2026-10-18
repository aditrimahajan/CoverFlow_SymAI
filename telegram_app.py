"""
CoverFlow live demo with real Telegram messages.

Serves the demo page at http://localhost:5050. Eligible staff with a Telegram chat ID
get the shift offer on their real phone with Accept / Decline buttons.
First tap on Accept gets the shift. No public URL needed (uses long polling).

Setup:  pip3 install flask python-dotenv
Config: add BOT_TOKEN, MARIA_CHAT and STAFF_CHATS to .env (see TELEGRAM_SETUP.md)
Run:    python3 telegram_app.py
"""
import json
import os
import threading
import time
import urllib.parse
import urllib.request
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
MARIA_CHAT = os.getenv("MARIA_CHAT", "").strip()
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true" or not BOT_TOKEN
API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# STAFF_CHATS=sam=123456789,noah=987654321
STAFF_CHATS = {}
for pair in os.getenv("STAFF_CHATS", "").split(","):
    if "=" in pair:
        sid, chat = pair.split("=", 1)
        STAFF_CHATS[sid.strip().lower()] = chat.strip()
CHAT_TO_STAFF = {v: k for k, v in STAFF_CHATS.items()}

NAMES = {"sam": "Sam", "priya": "Priya", "leo": "Leo", "grace": "Grace", "noah": "Noah"}

app = Flask(__name__, static_folder="static")
lock = threading.Lock()


def fresh_state(round_id=0):
    return {
        "round": round_id,      # changes every offer, so old buttons are ignored
        "open": False,
        "offered": [],
        "winner": None,
        "declined": set(),
        "messages": {},         # staff id -> (chat id, message id) of their offer
    }


state = fresh_state()


def log(text):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {text}")


def tg(method, **params):
    """Call the Telegram Bot API. Returns the result or None."""
    if DRY_RUN:
        if method in ("sendMessage", "editMessageText"):
            log(f"(dry run) {method} to {params.get('chat_id')}: {params.get('text')}")
        return None
    data = json.dumps(params).encode()
    req = urllib.request.Request(f"{API}/{method}", data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=35) as r:
            body = json.loads(r.read().decode())
            return body.get("result")
    except Exception as exc:
        log(f"Telegram {method} failed: {exc}")
        return None


def name_of(staff_id):
    return NAMES.get(staff_id, staff_id.title())


def send_offer(staff_id):
    chat = STAFF_CHATS.get(staff_id)
    if not chat:
        return
    r = state["round"]
    result = tg("sendMessage", chat_id=chat,
                text=("CoverFlow · Shift available\n\n"
                      "Opening barista shift today, 7:00am–3:00pm at Harbour Café.\n"
                      "First to accept gets it."),
                reply_markup={"inline_keyboard": [[
                    {"text": "Accept shift", "callback_data": f"accept:{r}"},
                    {"text": "Decline", "callback_data": f"decline:{r}"}]]})
    if result:
        state["messages"][staff_id] = (chat, result["message_id"])


def edit_offer(staff_id, text):
    """Replace a staff member's offer (and its buttons) with a final message."""
    if staff_id in state["messages"]:
        chat, msg_id = state["messages"][staff_id]
        tg("editMessageText", chat_id=chat, message_id=msg_id, text=text)


def award(staff_id):
    """First valid acceptance wins. Call with the lock held."""
    state["open"] = False
    state["winner"] = staff_id
    log(f"{name_of(staff_id)} accepted first and gets the shift")
    edit_offer(staff_id, f"CoverFlow · You're confirmed\n\nOpening shift today, 7:00am–3:00pm. Thanks, {name_of(staff_id)}!")
    for other in state["offered"]:
        if other != staff_id and other not in state["declined"]:
            edit_offer(other, "CoverFlow · This shift has been filled. Thanks for responding.")
    if MARIA_CHAT:
        tg("sendMessage", chat_id=MARIA_CHAT,
           text=f"CoverFlow · Good news\n\nYour 7am opening shift has been covered by {name_of(staff_id)}. No action needed.")


def maybe_escalate():
    """Call with the lock held."""
    if state["open"] and state["offered"] and set(state["offered"]) <= state["declined"]:
        state["open"] = False
        log("Everyone eligible declined. Escalated to Maria")
        if MARIA_CHAT:
            tg("sendMessage", chat_id=MARIA_CHAT,
               text="CoverFlow · Action needed\n\nYour 7am opening shift is still uncovered. Everyone eligible declined.")


def handle_update(u):
    # Anyone who taps Start gets their chat ID back, for setup.
    msg = u.get("message")
    if msg and "chat" in msg:
        chat = msg["chat"]["id"]
        who = msg["chat"].get("first_name", "there")
        tg("sendMessage", chat_id=chat,
           text=f"Hi {who}! Your CoverFlow chat ID is {chat}\nGive this number to whoever runs the demo.")
        log(f"{who} messaged the bot. Chat ID: {chat}")
        return

    q = u.get("callback_query")
    if not q:
        return
    tg("answerCallbackQuery", callback_query_id=q["id"])
    chat = str(q["message"]["chat"]["id"])
    action, _, round_id = q.get("data", "").partition(":")
    staff_id = CHAT_TO_STAFF.get(chat)
    with lock:
        if not staff_id or staff_id not in state["offered"] or round_id != str(state["round"]):
            return
        if not state["open"]:
            return
        if action == "accept":
            award(staff_id)
        elif action == "decline":
            state["declined"].add(staff_id)
            log(f"{name_of(staff_id)} declined on Telegram")
            edit_offer(staff_id, "CoverFlow · You declined this shift. Thanks for letting us know.")
            maybe_escalate()


def poll_telegram():
    offset = None
    while True:
        if DRY_RUN:
            time.sleep(5)
            continue
        params = {"timeout": 25}
        if offset is not None:
            params["offset"] = offset
        try:
            url = f"{API}/getUpdates?" + urllib.parse.urlencode(params)
            with urllib.request.urlopen(url, timeout=35) as r:
                updates = json.loads(r.read().decode()).get("result", [])
        except Exception as exc:
            log(f"Could not reach Telegram: {exc}")
            time.sleep(3)
            continue
        for u in updates:
            offset = u["update_id"] + 1
            try:
                handle_update(u)
            except Exception as exc:
                log(f"Could not handle update: {exc}")


@app.get("/")
def index():
    return send_from_directory("static", "index.html")


@app.get("/api/config")
def config():
    return jsonify(dryRun=DRY_RUN, realStaff=sorted(STAFF_CHATS), maria=bool(MARIA_CHAT))


@app.post("/api/offer")
def offer():
    staff = [s.lower() for s in (request.json or {}).get("staff", [])]
    with lock:
        state.update(fresh_state(state["round"] + 1))
        state["open"] = True
        state["offered"] = staff
        log(f"Offer sent to {len(staff)} eligible staff at once")
        for s in staff:
            send_offer(s)
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
            edit_offer(staff_id, "CoverFlow · You declined this shift.")
            maybe_escalate()
    return jsonify(ok=True)


@app.get("/api/status")
def status():
    with lock:
        return jsonify(open=state["open"], winner=state["winner"], declined=sorted(state["declined"]))


@app.post("/api/reset")
def reset():
    with lock:
        state.update(fresh_state(state["round"] + 1))
    return jsonify(ok=True)


if __name__ == "__main__":
    print("CoverFlow demo running at http://localhost:5050")
    print("Mode:", "DRY RUN (no Telegram messages)" if DRY_RUN else "LIVE Telegram")
    print("Real phones:", ", ".join(f"{name_of(k)} (chat {v})" for k, v in STAFF_CHATS.items()) or "none yet")
    print("Maria:", f"chat {MARIA_CHAT}" if MARIA_CHAT else "not set")
    threading.Thread(target=poll_telegram, daemon=True).start()
    app.run(host="127.0.0.1", port=5050, debug=False)
