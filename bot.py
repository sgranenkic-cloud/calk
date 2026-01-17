import os
import re
from dataclasses import dataclass
from typing import Optional, Tuple

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is missing. Create .env with BOT_TOKEN=...")

# -----------------------------
# Math & formatting
# -----------------------------

def mmss_to_seconds(s: str) -> Optional[int]:
    """
    Accepts mm:ss or hh:mm:ss, returns total seconds.
    """
    s = s.strip()
    if not re.fullmatch(r"\d{1,2}:\d{2}(:\d{2})?", s):
        return None
    parts = [int(p) for p in s.split(":")]
    if len(parts) == 2:
        mm, ss = parts
        return mm * 60 + ss
    hh, mm, ss = parts
    return hh * 3600 + mm * 60 + ss

def seconds_to_time(sec: float) -> str:
    """
    Formats seconds to mm:ss or hh:mm:ss (rounded to nearest second).
    """
    sec_i = int(round(sec))
    if sec_i < 0:
        sec_i = 0
    hh = sec_i // 3600
    rem = sec_i % 3600
    mm = rem // 60
    ss = rem % 60
    if hh > 0:
        return f"{hh}:{mm:02d}:{ss:02d}"
    return f"{mm}:{ss:02d}"

def pace_seconds_to_str(p_sec_per_km: float) -> str:
    """
    Formats pace seconds/km -> m:ss/км (rounded to nearest second).
    """
    p = int(round(p_sec_per_km))
    if p < 0:
        p = 0
    mm = p // 60
    ss = p % 60
    return f"{mm}:{ss:02d}/км"

def parse_distance(text: str) -> Optional[int]:
    """
    Parses distance in meters.
    Supports:
      - 200м, 352m, 352 м
      - 1.5км, 1,5км, 2km
    """
    t = text.lower().replace(",", ".")
    m_km = re.search(r"(\d+(?:\.\d+)?)\s*(км|km)\b", t)
    if m_km:
        km = float(m_km.group(1))
        return int(round(km * 1000))

    m_m = re.search(r"(\d+(?:\.\d+)?)\s*(м|m)\b", t)
    if m_m:
        meters = float(m_m.group(1))
        return int(round(meters))

    return None

def parse_time(text: str) -> Optional[int]:
    """
    Finds first hh:mm:ss or mm:ss that is NOT a pace (i.e., not followed by /км or /km).
    """
    candidates = re.findall(r"\b(\d{1,2}:\d{2}(?::\d{2})?)\b", text)
    for token in candidates:
        after = re.search(re.escape(token) + r"\s*/\s*(км|km)\b", text.lower())
        if after:
            continue
        sec = mmss_to_seconds(token)
        if sec is not None:
            return sec
    return None

def parse_pace(text: str) -> Optional[int]:
    """
    Parses pace as seconds per km.
    Accepts: 3:45/км, 3:45/km
    """
    t = text.lower()
    m = re.search(r"\b(\d{1,2}:\d{2}(?::\d{2})?)\s*/\s*(км|km)\b", t)
    if not m:
        return None
    return mmss_to_seconds(m.group(1))

@dataclass
class CalcInput:
    d_m: Optional[int] = None
    t_s: Optional[int] = None
    p_s_per_km: Optional[int] = None

def compute_third(ci: CalcInput) -> Tuple[str, CalcInput]:
    d, t, p = ci.d_m, ci.t_s, ci.p_s_per_km
    have = sum(x is not None for x in (d, t, p))
    if have < 2:
        return ("Нужно 2 параметра из 3: дистанция (м), время (мм:сс), темп (м:сс/км).", ci)
    if have > 2:
        return ("Ты прислал все 3 параметра. Убери один — посчитаю недостающий.", ci)

    if d is not None and t is not None and p is None:
        if d <= 0:
            return ("Дистанция должна быть > 0.", ci)
        p_val = (t / d) * 1000.0
        ci.p_s_per_km = int(round(p_val))
        msg = (
            f"Вход:\n"
            f"• Дистанция: {d} м\n"
            f"• Время: {seconds_to_time(t)}\n\n"
            f"Результат:\n"
            f"• Темп: {pace_seconds_to_str(ci.p_s_per_km)}"
        )
        return (msg, ci)

    if d is not None and p is not None and t is None:
        if d <= 0:
            return ("Дистанция должна быть > 0.", ci)
        t_val = (p * d) / 1000.0
        ci.t_s = int(round(t_val))
        msg = (
            f"Вход:\n"
            f"• Дистанция: {d} м\n"
            f"• Темп: {pace_seconds_to_str(p)}\n\n"
            f"Результат:\n"
            f"• Время: {seconds_to_time(ci.t_s)}"
        )
        return (msg, ci)

    if t is not None and p is not None and d is None:
        if p <= 0:
            return ("Темп должен быть > 0.", ci)
        d_val = (t / p) * 1000.0
        ci.d_m = int(round(d_val))
        msg = (
            f"Вход:\n"
            f"• Время: {seconds_to_time(t)}\n"
            f"• Темп: {pace_seconds_to_str(p)}\n\n"
            f"Результат:\n"
            f"• Дистанция: {ci.d_m} м"
        )
        return (msg, ci)

    return ("Не получилось определить, что считать. Проверь формат.", ci)

# -----------------------------
# Bot UI / state (simple in-memory per chat)
# -----------------------------

PRESETS = [200, 231, 352, 400]
user_state: dict[int, CalcInput] = {}

def make_main_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="Выбрать дистанцию", callback_data="pick_dist")
    kb.button(text="Сброс", callback_data="reset")
    kb.adjust(1, 1)
    return kb.as_markup()

def make_dist_kb():
    kb = InlineKeyboardBuilder()
    for d in PRESETS:
        kb.button(text=str(d), callback_data=f"dist:{d}")
    kb.button(text="Другая (ввести текстом)", callback_data="dist:other")
    kb.button(text="Назад", callback_data="back")
    kb.adjust(4, 1, 1)
    return kb.as_markup()

def normalize_help_text(ci: CalcInput) -> str:
    parts = []
    if ci.d_m is not None:
        parts.append(f"Дистанция: {ci.d_m} м")
    if ci.t_s is not None:
        parts.append(f"Время: {seconds_to_time(ci.t_s)}")
    if ci.p_s_per_km is not None:
        parts.append(f"Темп: {pace_seconds_to_str(ci.p_s_per_km)}")
    if not parts:
        return "Пока ничего не задано."
    return "Текущие значения:\n• " + "\n• ".join(parts)

INSTRUCTIONS = (
    "Калькулятор темпа.\n\n"
    "Можно вводить в любом порядке, главное — 2 из 3:\n"
    "• дистанция: `352м` или `400m`\n"
    "• время: `1:02` или `00:01:02`\n"
    "• темп: `3:45/км` или `3:45/km`\n\n"
    "Примеры:\n"
    "• `352м 1:02`\n"
    "• `400m 3:30/км`\n"
    "• `1:02 3:20/км` (посчитает дистанцию)\n"
)

dp = Dispatcher()

@dp.message(Command("start"))
async def start(m: Message):
    user_state[m.chat.id] = CalcInput()
    await m.answer(INSTRUCTIONS, parse_mode="Markdown")
    await m.answer("Меню:", reply_markup=make_main_kb())

@dp.callback_query(F.data == "pick_dist")
async def pick_dist(c: CallbackQuery):
    await c.message.edit_text("Выбери дистанцию (м):", reply_markup=make_dist_kb())
    await c.answer()

@dp.callback_query(F.data.startswith("dist:"))
async def set_dist(c: CallbackQuery):
    chat_id = c.message.chat.id
    ci = user_state.get(chat_id, CalcInput())

    val = c.data.split(":", 1)[1]
    if val == "other":
        await c.message.edit_text(
            "Введи дистанцию текстом, например: `600м` или `1.2км`",
            parse_mode="Markdown",
        )
        await c.answer()
        return

    ci.d_m = int(val)
    user_state[chat_id] = ci
    await c.message.edit_text(
        f"Ок. Дистанция = {ci.d_m} м.\n\n"
        f"{normalize_help_text(ci)}\n\n"
        "Теперь пришли время (`мм:сс`) или темп (`м:сс/км`), или оба параметра в одной строке.",
        reply_markup=make_main_kb(),
    )
    await c.answer()

@dp.callback_query(F.data == "reset")
async def reset(c: CallbackQuery):
    user_state[c.message.chat.id] = CalcInput()
    await c.message.edit_text("Сброшено.\n\n" + INSTRUCTIONS, reply_markup=make_main_kb())
    await c.answer()

@dp.callback_query(F.data == "back")
async def back(c: CallbackQuery):
    await c.message.edit_text("Меню:", reply_markup=make_main_kb())
    await c.answer()

@dp.message()
async def any_text(m: Message):
    chat_id = m.chat.id
    ci = user_state.get(chat_id, CalcInput())

    text = (m.text or "").strip()
    if not text:
        return

    d = parse_distance(text)
    t = parse_time(text)
    p = parse_pace(text)

    updated_any = False
    if d is not None:
        ci.d_m = d
        updated_any = True
    if t is not None:
        ci.t_s = t
        updated_any = True
    if p is not None:
        ci.p_s_per_km = p
        updated_any = True

    user_state[chat_id] = ci

    if not updated_any:
        await m.answer(
            "Не распознал ввод.\n\n" + INSTRUCTIONS + "\n" + normalize_help_text(ci),
            parse_mode="Markdown",
            reply_markup=make_main_kb(),
        )
        return

    msg, ci2 = compute_third(ci)
    user_state[chat_id] = ci2

    await m.answer(msg + "\n\n" + normalize_help_text(ci2), reply_markup=make_main_kb())

async def main():
    bot = Bot(BOT_TOKEN)
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
