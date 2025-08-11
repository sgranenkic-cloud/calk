
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Athletics Calculator Bot — production-ready.
Функции:
1) % пульса — расчёт диапазона ЧСС по HRmax и процентам.
2) Время по темпу — время по дистанции и темпу.
3) Калькулятор — вычисляет недостающий параметр (дистанция/темп/время).
4) Прогноз (Ригель) — перевод результатов между дистанциями.
5) Дорожка ↔ Темп — конвертер скорости (км/ч, mph, м/с) и темпа (мин/км, мин/ми).

Во всех сценариях есть кнопка «⬅ Назад».
"""
import os
import logging
from typing import Optional, Tuple

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

# -------------------- ЛОГИРОВАНИЕ --------------------
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("athletics-bot")

# -------------------- УТИЛИТЫ --------------------
def _norm_num(s: str) -> str:
    return s.strip().replace(",", ".")

def parse_float(s: str) -> Optional[float]:
    try:
        return float(_norm_num(s))
    except Exception:
        return None

def parse_time_to_seconds(s: str) -> Optional[int]:
    """Принимает 'm:ss', 'h:mm:ss' или целые секунды. Возвращает секунды."""
    s = s.strip()
    if not s:
        return None
    if s.isdigit():
        return int(s)
    parts = s.split(":")
    if not all(p.isdigit() for p in parts):
        return None
    if len(parts) == 2:
        m, sec = map(int, parts)
        return m * 60 + sec
    if len(parts) == 3:
        h, m, sec = map(int, parts)
        return h * 3600 + m * 60 + sec
    return None

def format_seconds_to_hhmmss(total_seconds: float) -> str:
    total_seconds = int(round(total_seconds))
    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    s = total_seconds % 60
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"

def km_to_miles(km: float) -> float:
    return km * 0.621371192

def miles_to_km(mi: float) -> float:
    return mi / 0.621371192

def meters_to_km(m: float) -> float:
    return m / 1000.0

def km_to_m(km: float) -> float:
    return km * 1000.0

def parse_distance(token: str) -> Optional[Tuple[float, str]]:
    """Возвращает (дистанция_в_км, исходная_единица: 'm'|'km'|'mi') или None."""
    if not token:
        return None
    t = token.strip().lower().replace(" ", "")
    if t.endswith(("км", "km")):
        val = parse_float(t[:-2]);   return (float(val), "km") if val is not None else None
    if t.endswith(("м", "m")):
        val = parse_float(t[:-1]);   return (meters_to_km(float(val)), "m") if val is not None else None
    if t.endswith(("mi", "mile", "miles")):
        if "mile" in t:
            val = parse_float(t.split("m")[0])
        else:
            val = parse_float(t[:-2])
        return (miles_to_km(float(val)), "mi") if val is not None else None
    # без суффикса — трактуем как км
    val = parse_float(t)
    return (float(val), "km") if val is not None else None

def parse_pace(token: str):
    """Возвращает (секунд_на_единицу, '/km'|'/mi'). Если единицы не указаны — считаем '/km'."""
    if not token:
        return None
    t = token.strip().lower()
    unit = "/km"
    if "/mi" in t or "/mile" in t:
        unit = "/mi"; t = t.split("/")[0].strip()
    elif "/км" in t or "/km" in t:
        unit = "/km"; t = t.split("/")[0].strip()
    secs = parse_time_to_seconds(t)
    if secs is None:
        return None
    return secs, unit

def convert_speed_to_pace(speed_value: float, unit: str = "kmh", pace_unit: str = "/km") -> float:
    """Возвращает секунд/км или секунд/ми по заданной скорости (kmh|mph|mps)."""
    if speed_value <= 0:
        raise ValueError("Скорость должна быть > 0.")
    if unit == "kmh":
        mps = speed_value * 1000.0 / 3600.0
    elif unit == "mph":
        mps = speed_value * 1609.344 / 3600.0
    elif unit == "mps":
        mps = speed_value
    else:
        raise ValueError("Неподдерживаемая единица скорости.")
    if pace_unit == "/km":
        return 1000.0 / mps
    return 1609.344 / mps

def convert_pace_to_speed(pace_seconds: int, pace_unit: str = "/km", out_unit: str = "kmh") -> float:
    """Возвращает скорость (kmh|mph|mps) по темпу (сек/км или сек/ми)."""
    if pace_seconds <= 0:
        raise ValueError("Темп должен быть > 0.")
    if pace_unit == "/km":
        mps = 1000.0 / pace_seconds
    else:
        mps = 1609.344 / pace_seconds
    if out_unit == "kmh":
        return mps * 3.6
    if out_unit == "mph":
        return mps * 3600.0 / 1609.344
    if out_unit == "mps":
        return mps
    raise ValueError("Неподдерживаемая единица скорости.")

def riegel(t1_sec: int, d1_km: float, d2_km: float, exp: float = 1.06) -> float:
    """T2 = T1 × (D2/D1)^exp"""
    if d1_km <= 0 or d2_km <= 0:
        raise ValueError("Дистанции должны быть > 0.")
    return t1_sec * ((d2_km / d1_km) ** exp)

# -------------------- КЛАВИАТУРЫ --------------------
MAIN_MENU = InlineKeyboardMarkup([
    [InlineKeyboardButton("% пульса", callback_data="menu_hr")],
    [InlineKeyboardButton("Время по темпу", callback_data="menu_time_by_pace")],
    [InlineKeyboardButton("Калькулятор (дист/темп/время)", callback_data="menu_calc")],
    [InlineKeyboardButton("Прогноз (Ригель)", callback_data="menu_riegel")],
    [InlineKeyboardButton("Дорожка ↔ Темп", callback_data="menu_tread")],
])
BACK_BTN = InlineKeyboardMarkup([[InlineKeyboardButton("⬅ Назад", callback_data="back_main")]])

WELCOME_TEXT = (
    "Выберите инструмент:\n\n"
    "• % пульса — диапазон ЧСС по HRmax и %\n"
    "• Время по темпу — время по дистанции и темпу\n"
    "• Калькулятор — вычислить недостающий параметр\n"
    "• Прогноз (Ригель) — оценка на другую дистанцию\n"
    "• Дорожка ↔ Темп — км/ч⇄мин/км и mph⇄мин/ми"
)

# -------------------- КОМАНДЫ --------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text(WELCOME_TEXT, reply_markup=MAIN_MENU)
    else:
        await update.callback_query.message.edit_text(WELCOME_TEXT, reply_markup=MAIN_MENU)

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "Форматы:\n"
        "• Время: m:ss или h:mm:ss\n"
        "• Дистанция: 1000м | 3км | 10km | 1mi\n"
        "• Темп: 4:10/км | 6:30/mi (если без единиц — считаем /км)\n"
        "• Ригель: '10км, 41:30 -> 21.1км' | '3000м, 10:00 -> 5000м, exp=1.07'\n"
        "• Дорожка: speed=12.5kmh | 7.5mph | 3.5mps  или  pace=4:48/км | 7:30/mi"
    )
    await update.message.reply_text(text, reply_markup=MAIN_MENU)

async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.clear()
    await start(update, context)

# -------------------- МЕНЮ-СЦЕНАРИИ --------------------
async def menu_hr(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.clear(); context.user_data["mode"] = "hr"
    txt = (
        "Введите HRmax и проценты. Примеры:\n"
        "• 196, 72-83\n"
        "• 190, 70\n"
        "Формат: HRmax, проценты"
    )
    await update.callback_query.message.edit_text(txt, reply_markup=BACK_BTN)

async def menu_time_by_pace(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.clear(); context.user_data["mode"] = "time_by_pace"
    txt = (
        "Введите дистанцию и темп. Примеры:\n"
        "• 1000м, 4:00\n"
        "• 1mi, 6:00/mi\n"
        "• 3км, 3:45\n"
        "Формат: дистанция, темп"
    )
    await update.callback_query.message.edit_text(txt, reply_markup=BACK_BTN)

async def menu_calc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.clear(); context.user_data["mode"] = "calc"
    txt = (
        "Калькулятор: укажите ДВА параметра, третий посчитаю.\n"
        "Примеры:\n"
        "• dist=10км, pace=3:45\n"
        "• 5000м, time=18:30\n"
        "• pace=4:10, time=45:00"
    )
    await update.callback_query.message.edit_text(txt, reply_markup=BACK_BTN)

async def menu_riegel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.clear(); context.user_data["mode"] = "riegel"
    txt = (
        "Ригель: '10км, 41:30 -> 21.1км' или '3000м, 10:00 -> 5000м, exp=1.07'"
    )
    await update.callback_query.message.edit_text(txt, reply_markup=BACK_BTN)

async def menu_tread(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.clear(); context.user_data["mode"] = "tread"
    txt = (
        "Пересчёт: speed=12.5kmh | 7.5mph | 3.5mps  ИЛИ  pace=4:48/км | 7:30/mi"
    )
    await update.callback_query.message.edit_text(txt, reply_markup=BACK_BTN)

# -------------------- РОУТЕР --------------------
async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    mode = context.user_data.get("mode")
    if not mode:
        await start(update, context)
        return
    text = update.message.text.strip()
    try:
        if mode == "hr":
            await handle_hr(text, update)
        elif mode == "time_by_pace":
            await handle_time_by_pace(text, update)
        elif mode == "calc":
            await handle_calc(text, update)
        elif mode == "riegel":
            await handle_riegel(text, update)
        elif mode == "tread":
            await handle_tread(text, update)
        else:
            await update.message.reply_text("Не понял. Нажмите кнопку в меню.", reply_markup=MAIN_MENU)
    except Exception as e:
        logger.exception("Ошибка обработки")
        await update.message.reply_text(f"Ошибка: {e}", reply_markup=BACK_BTN)

# -------------------- ИМПЛЕМЕНТАЦИИ --------------------
async def handle_hr(text: str, update: Update) -> None:
    line = text.replace("%", "").replace(" ", "")
    if "," in line:
        left, right = line.split(",", 1)
    elif ";" in line:
        left, right = line.split(";", 1)
    else:
        await update.message.reply_text("Формат: HRmax, проценты (напр. 196, 72-83)", reply_markup=BACK_BTN)
        return

    hrmax = parse_float(left)
    if hrmax is None or hrmax <= 0:
        await update.message.reply_text("Не удалось распознать HRmax (>0).", reply_markup=BACK_BTN)
        return

    if "-" in right:
        p1s, p2s = right.split("-", 1)
        p1 = parse_float(p1s); p2 = parse_float(p2s)
        if p1 is None or p2 is None:
            await update.message.reply_text("Проблема с процентами. Пример: 72-83.", reply_markup=BACK_BTN)
            return
        low = int(round(hrmax * min(p1, p2) / 100.0))
        high = int(round(hrmax * max(p1, p2) / 100.0))
        await update.message.reply_text(
            f"Диапазон: {low}–{high} уд/мин (из {p1:.0f}–{p2:.0f}% от {hrmax:.0f}).",
            reply_markup=BACK_BTN
        )
    else:
        p1 = parse_float(right)
        if p1 is None:
            await update.message.reply_text("Процент не распознан.", reply_markup=BACK_BTN)
            return
        val = int(round(hrmax * p1 / 100.0))
        await update.message.reply_text(f"{p1:.0f}% от {hrmax:.0f} = {val} уд/мин.", reply_markup=BACK_BTN)

async def handle_time_by_pace(text: str, update: Update) -> None:
    if "," in text:
        ds, pace_s = text.split(",", 1)
    elif ";" in text:
        ds, pace_s = text.split(";", 1)
    else:
        await update.message.reply_text("Формат: дистанция, темп (например 1000м, 4:00)", reply_markup=BACK_BTN)
        return

    dist = parse_distance(ds)
    if dist is None:
        await update.message.reply_text("Дистанция не распознана.", reply_markup=BACK_BTN)
        return
    dist_km, _ = dist

    pace = parse_pace(pace_s)
    if pace is None:
        await update.message.reply_text("Темп не распознан (ожидал m:ss[/км|/mi]).", reply_markup=BACK_BTN)
        return
    pace_sec, pace_unit = pace

    sec_per_km = pace_sec if pace_unit == "/km" else pace_sec * (1 / 0.621371192)
    time_sec = sec_per_km * dist_km
    await update.message.reply_text(f"Время: {format_seconds_to_hhmmss(time_sec)}", reply_markup=BACK_BTN)

def extract_named(parts, keys):
    for p in parts:
        pl = p.lower().strip()
        for k in keys:
            if pl.startswith(k):
                return p.split("=", 1)[1].strip()
    return None

async def handle_calc(text: str, update: Update) -> None:
    raw = [t for chunk in text.replace(";", ",").split(",") for t in chunk.strip().split() if t.strip()]

    dist_tok = extract_named(raw, ("dist=", "дист=", "distance="))
    pace_tok = extract_named(raw, ("pace=", "темп="))
    time_tok = extract_named(raw, ("time=", "время=", "t="))

    if dist_tok is None:
        for p in raw:
            if p.lower().endswith(("км", "km", "м", "m", "mi", "mile", "miles")) or p.replace(",", ".").replace(".", "", 1).isdigit():
                dist_tok = p; break
    if pace_tok is None:
        for p in raw:
            if ":" in p and ("/" in p or "pace" in p.lower() or "темп" in p.lower()):
                pace_tok = p; break
    if time_tok is None:
        for p in raw:
            if ":" in p and (("pace" not in p.lower()) and ("/" not in p)):
                time_tok = p; break

    dist_km = parse_distance(dist_tok)[0] if dist_tok and parse_distance(dist_tok) else None
    pace_parsed = parse_pace(pace_tok) if pace_tok else None
    pace_sec = pace_parsed[0] if pace_parsed else None
    pace_unit = pace_parsed[1] if pace_parsed else "/km"
    time_sec = parse_time_to_seconds(time_tok) if time_tok else None

    known = sum(x is not None for x in (dist_km, pace_sec, time_sec))
    if known < 2:
        await update.message.reply_text("Нужно указать любые ДВА параметра из: дистанция, темп, время.", reply_markup=BACK_BTN)
        return

    if dist_km is None:
        sec_per_km = pace_sec if pace_unit == "/km" else pace_sec * (1 / 0.621371192)
        dist_km = time_sec / sec_per_km
        await update.message.reply_text(
            f"Дистанция: {dist_km:.3f} км ({int(round(km_to_m(dist_km)))} м, {km_to_miles(dist_km):.3f} mi)",
            reply_markup=BACK_BTN
        )
        return

    if pace_sec is None:
        sec_per_km = time_sec / dist_km
        await update.message.reply_text(
            f"Темп: {format_seconds_to_hhmmss(sec_per_km)}/км  |  {format_seconds_to_hhmmss(sec_per_km / (1/0.621371192))}/mi",
            reply_markup=BACK_BTN
        )
        return

    if time_sec is None:
        sec_per_km = pace_sec if pace_unit == "/km" else pace_sec * (1 / 0.621371192)
        time_sec = sec_per_km * dist_km
        await update.message.reply_text(
            f"Время: {format_seconds_to_hhmmss(time_sec)}",
            reply_markup=BACK_BTN
        )
        return

async def handle_riegel(text: str, update: Update) -> None:
    t = text.replace("→", "->")
    parts = [p.strip() for p in t.split("->")]
    if len(parts) < 2:
        await update.message.reply_text("Ожидал формат: dist1, time1 -> dist2[, exp=x.xx]", reply_markup=BACK_BTN)
        return

    left, right = parts[0], parts[1]
    if "," not in left and ";" not in left:
        await update.message.reply_text("Слева укажите 'дистанция, время' (например '10км, 41:30').", reply_markup=BACK_BTN)
        return
    ldist_tok, ltime_tok = [x.strip() for x in left.replace(";", ",").split(",", 1)]
    dist1 = parse_distance(ldist_tok)
    if dist1 is None:
        await update.message.reply_text("Первая дистанция не распознана.", reply_markup=BACK_BTN); return
    d1_km, _ = dist1
    t1 = parse_time_to_seconds(ltime_tok)
    if t1 is None:
        await update.message.reply_text("Время слева не распознано.", reply_markup=BACK_BTN); return

    rparts = [p.strip() for p in right.split(",")]
    dist2_tok = rparts[0]
    dist2 = parse_distance(dist2_tok)
    if dist2 is None:
        await update.message.reply_text("Целевая дистанция не распознана.", reply_markup=BACK_BTN); return
    d2_km, _ = dist2

    exp = 1.06
    for rp in rparts[1:]:
        if rp.lower().startswith("exp="):
            maybe = parse_float(rp.split("=", 1)[1])
            if maybe and 0.9 <= maybe <= 1.2:
                exp = maybe

    t2 = riegel(t1, d1_km, d2_km, exp)
    pace2_per_km = t2 / d2_km
    pace2_per_mi = pace2_per_km / (1/0.621371192)
    await update.message.reply_text(
        "Прогноз:\n"
        f"• Время: {format_seconds_to_hhmmss(t2)}\n"
        f"• Темп: {format_seconds_to_hhmmss(pace2_per_km)}/км  |  {format_seconds_to_hhmmss(pace2_per_mi)}/mi\n"
        f"(exp={exp:.2f})",
        reply_markup=BACK_BTN
    )

async def handle_tread(text: str, update: Update) -> None:
    q = text.strip().lower().replace(" ", "")
    if q.startswith("speed="):
        val = q.split("=", 1)[1]
        unit = "kmh"
        if val.endswith("kmh"):
            v = parse_float(val[:-3]); unit = "kmh"
        elif val.endswith("mph"):
            v = parse_float(val[:-3]); unit = "mph"
        elif val.endswith("mps"):
            v = parse_float(val[:-3]); unit = "mps"
        else:
            v = parse_float(val); unit = "kmh"
        if v is None or v <= 0:
            await update.message.reply_text("Скорость не распознана (>0).", reply_markup=BACK_BTN); return
        pace_km = convert_speed_to_pace(v, unit, "/km")
        pace_mi = convert_speed_to_pace(v, unit, "/mi")
        await update.message.reply_text(
            f"Темп: {format_seconds_to_hhmmss(pace_km)}/км  |  {format_seconds_to_hhmmss(pace_mi)}/mi",
            reply_markup=BACK_BTN
        )
        return

    if q.startswith("pace=") or ":" in q:
        val = q.split("=", 1)[1] if q.startswith("pace=") else q
        pace = parse_pace(val)
        if pace is None:
            await update.message.reply_text("Темп не распознан.", reply_markup=BACK_BTN); return
        p_sec, p_unit = pace
        s_kmh = convert_pace_to_speed(p_sec, p_unit, "kmh")
        s_mph = convert_pace_to_speed(p_sec, p_unit, "mph")
        s_mps = convert_pace_to_speed(p_sec, p_unit, "mps")
        await update.message.reply_text(
            f"Скорость: {s_kmh:.2f} км/ч  |  {s_mph:.2f} mph  |  {s_mps:.2f} м/с",
            reply_markup=BACK_BTN
        )
        return

    await update.message.reply_text(
        "Укажите либо speed=12.5kmh|7.5mph|3.5mps, либо pace=4:48/км|7:30/mi.",
        reply_markup=BACK_BTN
    )

# -------------------- ИНИЦИАЛИЗАЦИЯ --------------------
def build_app() -> Application:
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise RuntimeError("Переменная окружения BOT_TOKEN не задана.")
    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CallbackQueryHandler(back_to_main, pattern="^back_main$"))
    app.add_handler(CallbackQueryHandler(menu_hr, pattern="^menu_hr$"))
    app.add_handler(CallbackQueryHandler(menu_time_by_pace, pattern="^menu_time_by_pace$"))
    app.add_handler(CallbackQueryHandler(menu_calc, pattern="^menu_calc$"))
    app.add_handler(CallbackQueryHandler(menu_riegel, pattern="^menu_riegel$"))
    app.add_handler(CallbackQueryHandler(menu_tread, pattern="^menu_tread$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))
    return app

def main():
    app = build_app()
    logger.info("Bot started.")
    app.run_polling(allowed_updates=None)

if __name__ == "__main__":
    main()
