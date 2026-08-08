# SweepRunner

Local sweepstakes automation dashboard. Chrome-powered form filler with entry tracking, win logging, and scheduling.

---

## Setup (One Time)

1. Make sure **Python 3.10+** is installed: https://python.org
2. Double-click **SETUP.bat** — installs Flask, Playwright, and the Chrome browser engine
3. Done.

---

## Launch

Double-click **START.bat** — opens the dashboard at http://localhost:5050

---

## How It Works

### Adding a Sweepstakes
- Click **+ Add Sweepstakes** in the top right
- Paste the URL of the entry page (not the homepage — the actual form page)
- Set frequency: Once / Daily / Weekly / Monthly
- Add a category and notes if you want

### Running Entries
- **▶ RUN DUE** — runs all eligible sweepstakes in one shot (daily ones only if you haven't entered today, etc.)
- **▶ Enter** button on any row — runs just that one
- Runs automatically every day at 9:00 AM while the app is open

### CAPTCHA Handling
- If a CAPTCHA appears, the browser window will stay open and wait for you to solve it (up to 2 minutes)
- After you solve it, click submit — the script will detect completion and move on
- The Live Log panel shows exactly what's happening

### Logging Wins
- Go to the **Wins** tab
- Click **+ Log Win**, pick the sweepstakes, enter prize details and value
- Tracked separately from entries

---

## Your Profile (config.json)

Your info is hardcoded in `config.json`. Edit it anytime to update your details.

The autofill matches form fields by common patterns (name, email, phone, address, zip, dob, gender, state, country). It won't catch every form — some sites use unusual field names. Those will need manual fill.

---

## Files

```
sweepstakes/
├── app.py           ← Flask backend + Playwright automation
├── config.json      ← Your profile (hardcoded)
├── sweepstakes.db   ← SQLite database (created on first run)
├── templates/
│   └── index.html   ← Dashboard UI
├── SETUP.bat        ← First-time setup
├── START.bat        ← Launch the app
└── README.md
```
