
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes

BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"

MENU, PULSE = range(2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["% пульса", "Время по темпу"],
                ["Круг 400 м из темпа", "Калькулятор"],
                ["Прогноз темпа", "Дорожка ↔ темп"]]
    await update.message.reply_text(
        "🐆 Привет!\nВыбери функцию:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return MENU

async def pulse_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введи максимальный пульс и процент через пробел (пример: 196 70):")
    return PULSE

async def pulse_calc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        max_hr, percent = map(float, update.message.text.split())
        result = max_hr * percent / 100
        await update.message.reply_text(f"Твой пульс: {result:.0f} уд/мин")
    except:
        await update.message.reply_text("Ошибка ввода. Формат: 196 70")
    return await start(update, context)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await start(update, context)

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MENU: [
                MessageHandler(filters.Regex("^% пульса$"), pulse_start),
            ],
            PULSE: [MessageHandler(filters.TEXT & ~filters.COMMAND, pulse_calc)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    app.add_handler(conv)
    app.run_polling()

if __name__ == "__main__":
    main()
