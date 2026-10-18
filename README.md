***CoverFlow
Your staff. Your rules. Your mornings back.***


CoverFlow is a plug-in for rostering tools like Tanda that coordinates last-minute shift cover when managers are off the clock. When a staff member calls in sick before sunrise, CoverFlow finds everyone eligible under the manager's rules, offers them the shift at the same time, gives it to the first person who accepts, and tells the manager the outcome.

Built at the Sym AI Open 2026 hackathon (Macquarie University) by CoverFlow Team (Aditri, Udit, Troy, Ozan)

***The problem***

It's 6:03am. Maria runs a café. Her opener texts that she's sick and can't make the 7am shift. Before her day has started, Maria has to open the rostering app, find the shift, contact staff, chase replies and check the shift is filled.

We interviewed 17 businesses around Macquarie Centre. About 70% raised rostering issues.
Absenteeism costs Australian businesses an estimated $33 billion a year, and 90% of absences are short-term and unplanned (Direct Health Solutions research, via Scale Suite, April 2026).
Hospitality has the highest rate of unplanned absence of any industry: 11.9 days per worker per year (same source).

Tools like Tanda already manage rosters and support shift replacements. What they leave to the manager is the coordination: starting the request, chasing people, and checking it worked. The problem isn't finding the right buttons. It's having to be the person who presses them.

***What CoverFlow does***

1. Reads the absence message and matches it to the affected shift.
2. Checks eligibility against the manager's rules, written as plain code rather than AI guesses:
  - trained for the role
  - available that day
  - no clash with their own shifts
  - stays within the weekly hour limit (38h)
3. Offers the shift to every eligible staff member at once on their real phone, with Accept and Decline buttons.
4. First to accept gets the shift. Everyone else's offer changes to "This shift has been filled".
5. Tells the manager the outcome: "Your 7am opening shift has been covered by Sam. No action needed." If everyone declines, the manager gets an "Action needed" alert instead.


***Part	File	Role***
Dashboard	--> static/index.html	--> The manager console: reads the sick text, runs the eligibility checks, shows offers, the outcome and an activity log
Messaging server --> telegram_app.py --> A small Flask server that serves the dashboard, sends real Telegram offers, listens for taps, and decides the winner
Bot -->	Telegram Bot API --> Delivers offers with Accept / Decline buttons to real phones


_Running it_
1. Requirements: Python 3 and a Telegram bot token from @BotFather.
2. Instructions:
   
pip3 install flask python-dotenv

python3 telegram_app.py

Then open the local host site url. (available in terminal command when 'python3 telegram_app.py' is executed)

***Settings live in a private .env file (never shared):***
BOT_TOKEN=...                         # from @BotFather
MARIA_CHAT=...                        # manager's Telegram chat ID
STAFF_CHATS=sam=...,noah=...          # which demo staff are real phones
DRY_RUN=false                         # true = print messages instead of sending



**What's real and what's simulated**

_Real_
1. Telegram messages to real phones
2. Accept / Decline taps and first-come-first-served logic
3. Manager notifications (covered / action needed)
4. Eligibility rules	

_Simulated for the demo_
1. The roster and staff data (9 staff at "Harbour Café")
2. The connection to Tanda (no live Tanda account is connected)
3. The sick text, which is typed into the dashboard


In this prototype, the absence message is read with keyword and time matching so the demo runs reliably. 

In production, this step would use a language model to understand free-form messages, while eligibility stays as hard-coded rules.


**What's next**

1. Connect to Tanda's API to read real rosters and write confirmed assignments back.
2. Receive absences directly from SMS, WhatsApp or the rostering app instead of a typed message.
3. Use a language model to understand any wording of a sick message, in any language.
4. Expand beyond hospitality and Tanda to any shift-based sector (aged care, healthcare, retail, transport) and any rostering platform with an API.
