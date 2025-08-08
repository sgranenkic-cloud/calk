
# Cheetah Chat Bot — Полный MVP (RU)

Функции:
1) % пульса — по HRmax и процентам
2) Таблица темпов — времена для 5/10/21.1/42.2
3) Калькулятор — любые 2 из 3: dist / pace / time
4) Прогноз (Ригель) — на 5/10/21.1/42.2 и по target
5) Дорожка ↔ Темп — speed км/ч ↔ pace мин/км

## Запуск локально
1. Python 3.11+
2. `pip install -r requirements.txt`
3. Создай `.env` и внеси `BOT_TOKEN=...` (или задайте переменную окружения)
4. `python main.py`

## Railway (как worker)
- Repo: этот проект
- Variables: `BOT_TOKEN`, `ADMIN_USERNAME`
- Build: `pip install -r requirements.txt`
- Start: `python main.py`
- Без домена, Serverless выкл.
