# CoverFlow live SMS demo

Runs the CoverFlow demo on your laptop and sends real texts through your Twilio account.
Staff reply YES or NO from their real phones. The first YES gets the shift.
No public URL or webhook needed: the app checks Twilio for replies every 2 seconds.

## 1. Install (once)

```
pip install flask twilio python-dotenv
```

## 2. Add your details

Copy `.env.example` to a new file called `.env` in the same folder, then fill in:

- `TWILIO_SID`, `TWILIO_TOKEN`, `TWILIO_NUMBER` from console.twilio.com
- `MARIA_PHONE`: the phone playing Maria (the manager)
- `STAFF_PHONES`: which demo staff are real phones, for example
  `sam=+61412345678,priya=+61498765432`
  (use the names sam, priya, leo, grace, noah; every number must be verified in Twilio)

Keep `.env` private. Don't share it or upload it anywhere.

## 3. Run

```
python app.py
```

Open http://localhost:5050 in your browser.
The tag at the top says **Live SMS** when real texts will be sent, or **Dry run** if `.env` is missing details.

## 4. Demo flow

1. Click **Send 6:03am sick text**.
2. Eligibility runs, then every eligible staff member gets the offer at once.
   Real phones (marked with an orange "Real phone" badge) get an actual SMS.
3. A teammate replies **YES** on their real phone. Within a few seconds the dashboard
   shows them as covering, the other real phones get "This shift has been filled",
   and Maria's real phone gets "Your 7am opening shift has been covered by ...".
4. You can still tap Accept or Decline on screen for the staff without real phones.
5. If everyone declines, Maria's phone gets an "Action needed" text.
6. Click **Reset demo** before each new run.

## Test without sending texts

Set `DRY_RUN=true` in `.env`. The texts are printed in the terminal instead.

## Tips

- Trial accounts add "Sent from your Twilio trial account" to every text. That's expected.
- SMS can take 2 to 10 seconds. Do a full test run in the room before you present.
- Keep phones off silent so the judges hear the ping.
