import os
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

BOT_TOKEN = os.getenv("BOT_TOKEN", "8472159060:AAEFU7m3nEBkFGcBP2JHDU_xcMbh6gZyQAU")

MENU, HR_MAX, HR_PERCENT, DIST1, TIME1, PACE1, RIEGEL_INPUT, TREADMILL_SPEED, TREADMILL_PACE = range(9)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [["% пульса", "Таблица темпов"],
          ["Калькулятор", "Прогноз темпа"],
          ["Дорожка ↔ Темп"]]
    await update.message.reply_text(
        "🐆 Привет! Ты в боте бегового клуба Cheetah.Club — выбери функцию:",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )

# % Пульса
async def hr_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введи HRmax:")
    return HR_MAX

async def hr_got_max(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["hrmax"] = int(update.message.text)
    await update.message.reply_text("Введи диапазон процентов (например 70-85):")
    return HR_PERCENT

async def hr_calc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    hrmax = context.user_data["hrmax"]
    parts = update.message.text.split("-")
    p1 = int(parts[0]); p2 = int(parts[-1])
    hr1 = round(hrmax * p1 / 100)
    hr2 = round(hrmax * p2 / 100)
    await update.message.reply_text(f"Диапазон {p1}-{p2}% от {hrmax}: {hr1}-{hr2} уд/мин")
    return ConversationHandler.END

# Таблица темпов
async def pace_table(update: Update, context: ContextTypes.DEFAULT_TYPE):
    table = "Темп (мин/км) — Скорость (км/ч)\n"
    for m in range(3, 7):
        for s in [0, 15, 30, 45]:
            pace = m + s/60
            speed = round(60/pace, 2)
            table += f"{m}:{s:02d} — {speed} км/ч\n"
    await update.message.reply_text(table)

# Калькулятор: дистанция/время/темп
async def calc_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введи дистанцию в км:")
    return DIST1

async def calc_dist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["dist"] = float(update.message.text)
    await update.message.reply_text("Введи темп (мм:сс) или время (ч:мм:сс):")
    return TIME1

async def calc_timepace(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dist = context.user_data["dist"]
    txt = update.message.text
    if ":" in txt and txt.count(":") == 1:
        m, s = map(int, txt.split(":"))
        pace = m + s/60
        total_min = pace * dist
        h = int(total_min//60)
        m = int(total_min%60)
        s = int((total_min%1)*60)
        await update.message.reply_text(f"Время: {h}:{m:02d}:{s:02d}")
    elif ":" in txt and txt.count(":") == 2:
        h, m, s = map(int, txt.split(":"))
        total_min = h*60 + m + s/60
        pace_min = total_min/dist
        mp = int(pace_min)
        sp = int((pace_min%1)*60)
        await update.message.reply_text(f"Темп: {mp}:{sp:02d} мин/км")
    return ConversationHandler.END

# Прогноз темпа (Ригель)
async def riegel_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введи результат и дистанцию (пример: 10км 00:40:00):")
    return RIEGEL_INPUT

async def riegel_calc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text.lower().replace("км", "")
    parts = msg.split()
    dist1 = float(parts[0])
    h, m, s = map(int, parts[1].split(":"))
    t1 = h*3600 + m*60 + s
    targets = [5, 10, 21.1, 42.2]
    result = ""
    for d2 in targets:
        t2 = t1 * (d2/dist1)**1.06
        hh = int(t2//3600); mm = int((t2%3600)//60); ss = int(t2%60)
        pace_min = (t2/60)/d2
        p_m = int(pace_min); p_s = int((pace_min%1)*60)
        result += f"{d2} км: {hh}:{mm:02d}:{ss:02d} ({p_m}:{p_s:02d}/км)\n"
    await update.message.reply_text(result)
    return ConversationHandler.END

# Дорожка ↔ Темп
async def treadmill_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введи скорость в км/ч:")
    return TREADMILL_SPEED

async def treadmill_speed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    speed = float(update.message.text)
    pace_min = 60/speed
    m = int(pace_min); s = int((pace_min%1)*60)
    await update.message.reply_text(f"Темп: {m}:{s:02d} мин/км")
    return ConversationHandler.END

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.add_handler(ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^% пульса$"), hr_start)],
        states={HR_MAX: [MessageHandler(filters.TEXT & ~filters.COMMAND, hr_got_max)],
                HR_PERCENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, hr_calc)]},
        fallbacks=[]
    ))
    app.add_handler(MessageHandler(filters.Regex("^Таблица темпов$"), pace_table))
    app.add_handler(ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^Калькулятор$"), calc_start)],
        states={DIST1: [MessageHandler(filters.TEXT & ~filters.COMMAND, calc_dist)],
                TIME1: [MessageHandler(filters.TEXT & ~filters.COMMAND, calc_timepace)]},
        fallbacks=[]
    ))
    app.add_handler(ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^Прогноз темпа$"), riegel_start)],
        states={RIEGEL_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, riegel_calc)]},
        fallbacks=[]
    ))
    app.add_handler(ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^Дорожка ↔ Темп$"), treadmill_start)],
        states={TREADMILL_SPEED: [MessageHandler(filters.TEXT & ~filters.COMMAND, treadmill_speed)]},
        fallbacks=[]
    ))

    app.run_polling()

if __name__ == "__main__":
    main()
