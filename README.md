# Cheetah Chat Bot — 6 кнопок + Назад

Кнопки:
1) % пульса — по HRmax и процентам (с «⬅ Назад»)
2) Время по темпу — дистанция (м, любая) + темп → время отрезка
3) Круг 400 м из темпа — вводишь темп (мм:сс) → время круга
4) Калькулятор — dist/pace/time (любые 2 из 3)
5) Прогноз (Ригель) — на 5/10/21.1/42.2 и по target
6) Дорожка ↔ Темп — speed км/ч ↔ pace мин/км

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
