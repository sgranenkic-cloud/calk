## TG Pace Bot (distance buttons -> enter pace -> get time)

Flow:
1) Press a distance button: 200 / 231 / 352 / 400
2) Bot asks for pace (e.g. `4:45` or `4:45/км`)
3) Bot returns time for that distance.

### Run
```bash
pip install -r requirements.txt
# create .env with BOT_TOKEN
python bot.py
```
