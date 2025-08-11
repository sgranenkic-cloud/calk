#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import math
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

# ==== Утилиты ====
def parse_float(s):
    try:
        return float(s.strip().replace(",", "."))
    except:
        return None

def parse_time_to_seconds(s):
    s = s.strip()
    if s.isdigit():
        return int(s)
    parts = s.split(":")
    if len(parts) == 2:
        m, sec = map(int, parts)
        return m * 60 + sec
    if len(parts) == 3:
        h, m, sec = map(int, parts)
        return h * 3600 + m * 60 + sec
    return None

def format_seconds_to_hhmmss(total_seconds):
    total_seconds = int(round(total_seconds))
    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    s = total_seconds % 60
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"

# ==== Клавиатуры ====
MAIN_MENU = InlineKeyboardMarkup([
    [InlineKeyboardButton("% пульса", callback_data="menu_hr")],
    [InlineKeyboardButton("Время по темпу", callback_data="menu_time")],
    [InlineKeyboardButton("Калькулятор", callback_data="menu_calc")],
    [InlineKeyboardButton("Прогноз темпа (Ригель)", callback_data="menu_riegel")],
    [InlineKeyboardButton("Дорожка ↔ Темп", callback_data="menu_tread")]
])

BACK_BTN = InlineKeyboardMarkup([[InlineKeyboardButton("⬅ Назад", callback_data="back_main")]])

# ==== Хендлеры ====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "Выберите инструмент:"
    if update.message:
        await update.message.reply_text(text, reply_markup=MAIN_MENU)
    else:
        await update.callback_query.message.edit_text(text, reply_markup=MAIN_MENU)

async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)

# ==== Меню ====
async def menu_hr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = "hr"
    await update.callback_query.message.edit_text("Введите HRmax, проценты (напр. 196, 72-83)", reply_markup=BACK_BTN)

async def menu_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = "time"
    await update.callback_query.message.edit_text("Введите дистанцию (м) и темп (мин:сек/км)", reply_markup=BACK_BTN)

async def menu_calc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = "calc"
    await update.callback_query.message.edit_text("Введите два параметра: дистанция, темп, время", reply_markup=BACK_BTN)

async def menu_riegel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = "riegel"
    await update.callback_query.message.edit_text("Формат: dist1, time1 → dist2", reply_markup=BACK_BTN)

async def menu_tread(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = "tread"
    await update.callback_query.message.edit_text("Введите скорость (км/ч) или темп (мин/км)", reply_markup=BACK_BTN)

# ==== Обработка текста ====
async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = context.user_data.get("mode")
    if not mode:
        await start(update, context)
        return
    text = update.message.text.strip()
    if mode == "hr":
        try:
            hrmax, perc = text.split(",")
            hrmax = parse_float(hrmax)
            if "-" in perc:
                p1, p2 = perc.split("-")
                p1, p2 = parse_float(p1), parse_float(p2)
                low = int(round(hrmax * p1 / 100))
                high = int(round(hrmax * p2 / 100))
                await update.message.reply_text(f"Диапазон: {low}-{high} уд/мин", reply_markup=BACK_BTN)
            else:
                p1 = parse_float(perc)
                val = int(round(hrmax * p1 / 100))
                await update.message.reply_text(f"{p1}% от {hrmax} = {val} уд/мин", reply_markup=BACK_BTN)
        except:
            await update.message.reply_text("Ошибка формата", reply_markup=BACK_BTN)
    elif mode == "time":
        try:
            dist, pace = text.split(",")
            dist = parse_float(dist)
            pace_sec = parse_time_to_seconds(pace)
            total_time = pace_sec * (dist / 1000)
            await update.message.reply_text(f"Время: {format_seconds_to_hhmmss(total_time)}", reply_markup=BACK_BTN)
        except:
            await update.message.reply_text("Ошибка формата", reply_markup=BACK_BTN)
    elif mode == "tread":
        if "pace" in text.lower() or ":" in text:
            pace_sec = parse_time_to_seconds(text.replace("pace=", "").strip())
            speed = 3600 / (pace_sec / 60)
            await update.message.reply_text(f"Скорость: {speed:.2f} км/ч", reply_markup=BACK_BTN)
        else:
            speed = parse_float(text.replace("speed=", "").strip())
            pace_sec = 3600 / speed * 60
            await update.message.reply_text(f"Темп: {format_seconds_to_hhmmss(pace_sec)} мин/км", reply_markup=BACK_BTN)

# ==== Запуск ====
def main():
    TOKEN = os.environ["BOT_TOKEN"]
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(back_to_main, pattern="back_main"))
    app.add_handler(CallbackQueryHandler(menu_hr, pattern="menu_hr"))
    app.add_handler(CallbackQueryHandler(menu_time, pattern="menu_time"))
    app.add_handler(CallbackQueryHandler(menu_calc, pattern="menu_calc"))
    app.add_handler(CallbackQueryHandler(menu_riegel, pattern="menu_riegel"))
    app.add_handler(CallbackQueryHandler(menu_tread, pattern="menu_tread"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))
    app.run_polling()

if __name__ == "__main__":
    main()
