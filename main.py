import math
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = "8472159060:AAEFU7m3nEBkFGcBP2JHDU_xcMbh6gZyQAU"

main_menu = [["% пульса", "Таблица темпов"], ["Дистанция+темп=время", "Прогноз темпа"], ["Скорость дорожки", "Назад"]]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🐆 Привет!\nТы в боте бегового клуба Cheetah.Club.",
        reply_markup=ReplyKeyboardMarkup(main_menu, resize_keyboard=True)
    )

async def percent_pulse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите максимальный пульс и проценты через пробел (например: 196 70 85)")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().lower()
    if text == "% пульса":
        await percent_pulse(update, context)
    elif text == "таблица темпов":
        await update.message.reply_text("Таблица темпов пока в разработке")
    elif text == "дистанция+темп=время":
        await update.message.reply_text("Введите дистанцию (м) и темп (мм:сс)")
    elif text == "прогноз темпа":
        await update.message.reply_text("Введите результат (км время)")
    elif text == "скорость дорожки":
        await update.message.reply_text("Введите скорость дорожки в км/ч")
    elif text == "назад":
        await start(update, context)
    else:
        parts = text.replace(",", ".").split()
        if len(parts) >= 2 and parts[0].isdigit():
            max_hr = int(parts[0])
            try:
                percentages = list(map(float, parts[1:]))
                res = [f"{p}%: {round(max_hr * p / 100)} уд/мин" for p in percentages]
                await update.message.reply_text("\n".join(res))
            except:
                await update.message.reply_text("Ошибка ввода")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()

if __name__ == "__main__":
    main()
