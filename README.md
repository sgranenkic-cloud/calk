## TG Pace Bot

### Install
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

### Configure
Copy `.env.example` -> `.env` and set `BOT_TOKEN`.

### Run
```bash
python bot.py
```

### Usage
- /start -> menu
- Choose a preset distance (200/231/352/400) or enter your own
- Then send either:
  - time: `1:12` or `00:01:12`
  - pace: `3:45/км` or `3:45/km`
- Or send everything in one message (auto-parse):
  - `352м 1:02`
  - `400m 3:30/км`
  - `1:02 352м`
  - `1:02 3:20/км` (will compute distance)
