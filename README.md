# Cheetah Chat Bot — MVP (Время по темпу + Назад)

Функции:
1) % пульса — по HRmax и процентам (с «⬅ Назад»)
2) Время по темпу — вводишь дистанцию в метрах (любую) и темп мм:сс/км → получаешь время отрезка
3) Калькулятор — любые 2 из 3: dist / pace / time
4) Прогноз (Ригель) — на 5/10/21.1/42.2 и по target
5) Дорожка ↔ Темп — speed км/ч ↔ pace мин/км

## Запуск локально
1. Python 3.11+
2. `pip install -r requirements.txt`
3. Создай `.env` и внеси `BOT_TOKEN=...` (или задай переменные окружения)
4. `python main.py`

## Railway (как worker)
- Repo: этот проект
- Variables: `BOT_TOKEN`, `ADMIN_USERNAME`
- Build: `pip install -r requirements.txt`
- Start: `python main.py`
- Без домена, Serverless выкл.
