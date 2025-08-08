
import os, re
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ConversationHandler,
    ContextTypes, filters
)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_TOKEN_HERE")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "grondkind")

# States
HR_MAX, HR_PERCENT = range(2)
SEG_DIST, SEG_PACE = range(2)

BACK_TEXT = "⬅ Назад"

def kb_main():
    return ReplyKeyboardMarkup(
        [["% пульса", "Время по темпу"],
         ["Калькулятор", "Прогноз темпа"],
         ["Дорожка ↔ Темп"]],
        resize_keyboard=True
    )

def kb_back():
    return ReplyKeyboardMarkup([[KeyboardButton(BACK_TEXT)]], resize_keyboard=True, one_time_keyboard=True)

# ---------- Helpers ----------
def parse_time_to_seconds(s: str) -> int:
    s = s.strip()
    parts = s.split(":")
    if not all(p.isdigit() for p in parts):
        raise ValueError("Неверный формат времени")
    if len(parts) == 3:
        h, m, sec = map(int, parts)
        return h*3600 + m*60 + sec
    elif len(parts) == 2:
        m, sec = map(int, parts)
        return m*60 + sec
    elif len(parts) == 1:
        return int(parts[0])
    else:
        raise ValueError("Неверный формат времени")

def fmt_time(seconds: int) -> str:
    seconds = int(round(seconds))
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

def parse_pace_to_sec_per_km(s: str) -> int:
    # pace in mm:ss per km
    return parse_time_to_seconds(s)

def get_val(text: str, key: str):
    m = re.search(rf"{key}\s*=\s*([^\s]+)", text)
    return m.group(1) if m else None

# ---------- Start / Menu ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🐆 Привет!\n"
        "Ты в боте бегового клуба Cheetah.Club — месте, где пробежки превращаются в привычку, а привычка — в результат.\n\n"
        "Здесь ты можешь:\n"
        "▫️ Узнать, как попасть в команду и стать настоящим гепардом.\n"
        "▫️ Понять, что нужно для первых шагов в беге.\n"
        "▫️ Найти, где проходят наши тренировки.\n"
        "▫️ Посмотреть тарифы и формат занятий.\n\n"
        "Мы тренируем:\n"
        "🏃‍♀️ От первых  километров до марафона и дальше.\n"
        "💬 В Новосибирске и онлайн.\n"
        "📅 По расписанию и в удобное тебе время.\n\n"
        "Жмяк на кнопку в меню и начинаем!"
    )
    await update.message.reply_text(text, reply_markup=kb_main())

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Выбирай инструмент:", reply_markup=kb_main())

# ---------- Universal BACK handler ----------
async def go_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Окей, вернулись в меню.", reply_markup=kb_main())
    return ConversationHandler.END

# ---------- 1) % пульса ----------
async def hr_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введи свой максимальный пульс (HRmax), например: 190", reply_markup=kb_back())
    return HR_MAX

async def hr_got_max(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text.strip()
    if txt == BACK_TEXT:
        return await go_back(update, context)
    try:
        hrmax = int(txt)
        if not (80 <= hrmax <= 240):
            raise ValueError
    except Exception:
        await update.message.reply_text("Нужно целое число, например 190. Попробуй ещё раз:", reply_markup=kb_back())
        return HR_MAX
    context.user_data["hrmax"] = hrmax
    await update.message.reply_text("Теперь проценты (один или диапазон). Примеры: 75  или  70-85", reply_markup=kb_back())
    return HR_PERCENT

async def hr_calc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == BACK_TEXT:
        return await go_back(update, context)
    hrmax = context.user_data.get("hrmax")
    text = update.message.text.replace("%","").strip()
    m = re.match(r"^\s*(\d{1,3})(?:\s*-\s*(\d{1,3}))?\s*$", text)
    if not m or hrmax is None:
        await update.message.reply_text("Формат не распознан. Примеры: 75  или  70-85", reply_markup=kb_back())
        return HR_PERCENT
    p1 = int(m.group(1))
    p2 = int(m.group(2) or p1)
    lo = round(hrmax * p1 / 100)
    hi = round(hrmax * p2 / 100)
    if p1 == p2:
        await update.message.reply_text(f"{p1}% от {hrmax} → ≈ {lo} уд/мин", reply_markup=kb_main())
    else:
        await update.message.reply_text(f"{p1}-{p2}% от {hrmax} → ≈ {lo}–{hi} уд/мин", reply_markup=kb_main())
    return ConversationHandler.END

# ---------- 2) Время по темпу (distance meters + pace) ----------
async def seg_time_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введи дистанцию в метрах (например: 400, 1000, 352):", reply_markup=kb_back())
    return SEG_DIST

async def seg_time_get_dist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text.strip().replace(",", ".")
    if txt == BACK_TEXT:
        return await go_back(update, context)
    try:
        # принимаем любую дистанцию в метрах (не ругаемся за не кратность 100)
        meters = float(txt)
        if meters <= 0:
            raise ValueError
    except Exception:
        await update.message.reply_text("Нужно число метров, например 400 или 352. Попробуй ещё раз:", reply_markup=kb_back())
        return SEG_DIST
    context.user_data["seg_m"] = meters
    await update.message.reply_text("Теперь темп в формате мм:сс (на км), например 4:20:", reply_markup=kb_back())
    return SEG_PACE

def parse_pace_to_sec_per_km(s: str) -> int:
    parts = s.strip().split(":")
    if len(parts) != 2 or not all(p.isdigit() for p in parts):
        raise ValueError("Темп должен быть в формате мм:сс")
    m, sec = map(int, parts)
    return m*60 + sec

def fmt_time(seconds: int) -> str:
    seconds = int(round(seconds))
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

async def seg_time_calc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == BACK_TEXT:
        return await go_back(update, context)
    try:
        pace_sec = parse_pace_to_sec_per_km(update.message.text)
        meters = context.user_data.get("seg_m", 0.0)
        # время отрезка = (метры/1000) * темп(сек/км)
        t_sec = (meters / 1000.0) * pace_sec
        await update.message.reply_text(f"⏱ Время на {int(meters)} м при темпе {update.message.text}/км: {fmt_time(t_sec)}", reply_markup=kb_main())
        return ConversationHandler.END
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {e}. Пример темпа: 4:20", reply_markup=kb_back())
        return SEG_PACE

# ---------- 3) Калькулятор dist/pace/time ----------
async def calc_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "Калькулятор (введи 2 из 3 параметров):\n"
        "• dist=10  time=45:00  → темп\n"
        "• dist=21.1 pace=5:00  → время\n"
        "• pace=4:30 time=40:00 → дистанция\n"
        "Поддержка дистанций 5..42.2 км.\n\n"
        "Нажми «⬅ Назад», чтобы вернуться в меню."
    )
    await update.message.reply_text(help_text, reply_markup=kb_back())

def parse_time_to_seconds_any(s: str) -> int:
    s = s.strip()
    parts = s.split(":")
    if not all(p.isdigit() for p in parts):
        raise ValueError("Неверный формат времени")
    if len(parts) == 3:
        h, m, sec = map(int, parts)
        return h*3600 + m*60 + sec
    elif len(parts) == 2:
        m, sec = map(int, parts)
        return m*60 + sec
    elif len(parts) == 1:
        return int(parts[0])
    else:
        raise ValueError("Неверный формат времени")

async def calc_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == BACK_TEXT:
        return await go_back(update, context)
    text = update.message.text.lower().replace(",", ".")
    def get_val(key):
        m = re.search(rf"{key}\s*=\s*([^\s]+)", text)
        return m.group(1) if m else None

    dist = get_val("dist")
    pace = get_val("pace")
    time = get_val("time")

    try:
        dist_f = float(dist) if dist else None
        pace_s = parse_time_to_seconds_any(pace) if pace else None
        time_s = parse_time_to_seconds_any(time) if time else None
    except Exception as e:
        return await update.message.reply_text(f"Не удалось разобрать параметры: {e}", reply_markup=kb_back())

    if dist_f and time_s and not pace_s:
        if not (5.0 <= dist_f <= 42.2):
            return await update.message.reply_text("Дистанция вне диапазона 5..42.2 км", reply_markup=kb_back())
        pace_s = round(time_s / dist_f)
        return await update.message.reply_text(f"Темп: {fmt_time(pace_s)}/км", reply_markup=kb_main())

    if dist_f and pace_s and not time_s:
        if not (5.0 <= dist_f <= 42.2):
            return await update.message.reply_text("Дистанция вне диапазона 5..42.2 км", reply_markup=kb_back())
        time_s = int(pace_s * dist_f)
        return await update.message.reply_text(f"Время: {fmt_time(time_s)}", reply_markup=kb_main())

    if pace_s and time_s and not dist_f:
        dist_f = round(time_s / pace_s, 2)
        return await update.message.reply_text(f"Дистанция: {dist_f} км", reply_markup=kb_main())

    await update.message.reply_text("Нужно указать РОВНО 2 параметра: dist, pace, time. Пример: dist=10 time=45:00", reply_markup=kb_back())

# ---------- 4) Прогноз темпа (Ригель) ----------
def riegel(t1_sec: int, d1: float, d2: float, k: float = 1.06) -> int:
    return int(round(t1_sec * (d2 / d1) ** k))

async def predict_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = (
        "Прогноз по Ригелю. Введи исходный результат:\n"
        "Примеры:\n"
        "• dist=10 time=40:00\n"
        "• dist=5 time=19:30\n"
        "• dist=21.1 time=1:35:00\n"
        "Можно добавить цель: target=42.2\n\n"
        "Нажми «⬅ Назад», чтобы вернуться в меню."
    )
    await update.message.reply_text(txt, reply_markup=kb_back())

async def predict_calc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == BACK_TEXT:
        return await go_back(update, context)
    text = update.message.text.lower().replace(",", ".")
    def get_val(key):
        m = re.search(rf"{key}\s*=\s*([^\s]+)", text)
        return m.group(1) if m else None

    dist = get_val("dist")
    time = get_val("time")
    target = get_val("target")

    if not (dist and time):
        return  # пусть другие хэндлеры заберут

    try:
        d1 = float(dist)
        t1 = parse_time_to_seconds_any(time)
    except Exception as e:
        return await update.message.reply_text(f"Ошибка разбора: {e}", reply_markup=kb_back())

    targets = [5.0, 10.0, 21.1, 42.2]
    if target:
        try:
            targets = [float(target)]
        except:
            pass

    lines = [f"Исходник: {d1} км за {fmt_time(t1)}"]
    for d2 in targets:
        t2 = riegel(t1, d1, d2)
        pace2 = int(t2 / d2)
        lines.append(f"{d2:>5} км → {fmt_time(t2)}  ({fmt_time(pace2)}/км)")
    await update.message.reply_text("\n".join(lines), reply_markup=kb_main())

# ---------- 5) Дорожка ↔ Темп ----------
async def treadmill_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введи один параметр: speed=12  (км/ч)  или  pace=5:00 (/км)\n\nНажми «⬅ Назад», чтобы вернуться в меню.", reply_markup=kb_back())

async def treadmill_calc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == BACK_TEXT:
        return await go_back(update, context)
    text = update.message.text.lower().replace(",", ".")
    m_speed = re.search(r"speed\s*=\s*([0-9.]+)", text)
    m_pace = re.search(r"pace\s*=\s*([0-9:]+)", text)

    try:
        if m_speed and not m_pace:
            speed = float(m_speed.group(1))  # км/ч
            if speed <= 0:
                raise ValueError
            pace_sec = int(round(3600 / (speed)))
            return await update.message.reply_text(f"Темп: {fmt_time(pace_sec)}/км", reply_markup=kb_main())
        elif m_pace and not m_speed:
            pace_sec = parse_pace_to_sec_per_km(m_pace.group(1))
            speed = 3600 / pace_sec
            return await update.message.reply_text(f"Скорость дорожки: {speed:.2f} км/ч", reply_markup=kb_main())
        else:
            return await update.message.reply_text("Нужно указать ОДИН параметр: speed=км/ч  или  pace=мм:сс", reply_markup=kb_back())
    except Exception:
        await update.message.reply_text("Проверь формат. Пример: speed=12  или  pace=5:00", reply_markup=kb_back())

# ---------- App ----------
def build_app():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Start/menu
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu))

    # Universal back
    app.add_handler(MessageHandler(filters.Regex(f"^{re.escape(BACK_TEXT)}$"), go_back))

    # % пульса
    conv_hr = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^% пульса$"), hr_start),
                      CommandHandler("hr", hr_start)],
        states={
            HR_MAX: [MessageHandler(filters.TEXT & ~filters.COMMAND, hr_got_max)],
            HR_PERCENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, hr_calc)]
        },
        fallbacks=[MessageHandler(filters.Regex(f"^{re.escape(BACK_TEXT)}$"), go_back)]
    )
    app.add_handler(conv_hr)

    # Время по темпу (distance m + pace)
    conv_seg = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^Время по темпу$"), seg_time_start),
                      CommandHandler("segment", seg_time_start)],
        states={
            SEG_DIST: [MessageHandler(filters.TEXT & ~filters.COMMAND, seg_time_get_dist)],
            SEG_PACE: [MessageHandler(filters.TEXT & ~filters.COMMAND, seg_time_calc)]
        },
        fallbacks=[MessageHandler(filters.Regex(f"^{re.escape(BACK_TEXT)}$"), go_back)]
    )
    app.add_handler(conv_seg)

    # Калькулятор
    app.add_handler(MessageHandler(filters.Regex("^Калькулятор$"), calc_entry))
    app.add_handler(CommandHandler("pace", calc_entry))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, calc_process))

    # Прогноз
    app.add_handler(MessageHandler(filters.Regex("^Прогноз темпа$"), predict_entry))
    app.add_handler(CommandHandler("predict", predict_entry))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, predict_calc))

    # Дорожка
    app.add_handler(MessageHandler(filters.Regex("^Дорожка ↔ Темп$"), treadmill_entry))
    app.add_handler(CommandHandler("treadmill", treadmill_entry))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, treadmill_calc))

    return app

def main():
    app = build_app()
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
