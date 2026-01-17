import os
import re
from dataclasses import dataclass
from typing import Optional

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is missing. Create .env with BOT_TOKEN=...")

PRESETS = [200, 231, 352, 400]

# -----------------------------
# Helpers
# -----------------------------

def mmss_to_seconds(s: str) -> Optional[int]:
    # Accepts mm:ss or hh:mm:ss -> seconds.
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
    # Formats seconds -> mm:ss (or hh:mm:ss if needed).
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

def parse_pace_seconds(text: str) -> Optional[int]:
    # Accepts: 4:45, 4:45/км, 4:45/km
    t = (text or "").strip().lower()

    m = re.search(r"\b(\d{1,2}:\d{2}(?::\d{2})?)\s*/\s*(км|km)\b", t)
    if m:
        return mmss_to_seconds(m.group(1))

    m2 = re.search(r"\b(\d{1,2}:\d{2}(?::\d{2})?)\b", t)
    if m2:
        return mmss_to_seconds(m2.group(1))

    return None

def pace_str(pace_s: int) -> str:
    return f"{pace_s//60}:{pace_s%60:02d}/км"

def make_distance_kb():
    kb = InlineKeyboardBuilder()
    # Order exactly: 200-400-231-352
    for d in [200, 400, 231, 352]:
        kb.button(text=f"{d} м", callback_data=f"dist:{d}")
    kb.button(text="Сброс", callback_data="reset")
    kb.adjust(2, 2, 1)
    return kb.as_markup()

def make_reset_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="Выбрать дистанцию", callback_data="pick")
    kb.button(text="Сброс", callback_data="reset")
    kb.adjust(1, 1)
    return kb.as_markup()

# -----------------------------
# Simple per-chat state
# -----------------------------

@dataclass
class ChatState:
    distance_m: Optional[int] = None

state: dict[int, ChatState] = {}

def get_state(chat_id: int) -> ChatState:
    if chat_id not in state:
        state[chat_id] = ChatState()
    return state[chat_id]

# -----------------------------
# Bot
# -----------------------------

dp = Dispatcher()

START_TEXT = (
    "Калькулятор времени по темпу.\n\n"
    "1) Выбери дистанцию кнопкой\n"
    "2) Введи темп (например: 4:45)\n"
    "3) Получишь время\n"
)

ASK_PACE_TEXT = (
    "Введи темп в формате `м:сс` (например `4:45`).\n"
    "Можно также `4:45/км`."
)

@dp.message(Command("start"))
async def start(m: Message):
    st = get_state(m.chat.id)
    st.distance_m = None
    await m.answer(START_TEXT)
    await m.answer("Выбери дистанцию:", reply_markup=make_distance_kb())

@dp.callback_query(F.data == "pick")
async def pick(c: CallbackQuery):
    st = get_state(c.message.chat.id)
    st.distance_m = None
    await c.message.edit_text("Выбери дистанцию:", reply_markup=make_distance_kb())
    await c.answer()

@dp.callback_query(F.data == "reset")
async def reset(c: CallbackQuery):
    st = get_state(c.message.chat.id)
    st.distance_m = None
    await c.message.edit_text("Сброшено.\n\nВыбери дистанцию:", reply_markup=make_distance_kb())
    await c.answer()

@dp.callback_query(F.data.startswith("dist:"))
async def choose_distance(c: CallbackQuery):
    st = get_state(c.message.chat.id)
    d = int(c.data.split(":", 1)[1])
    st.distance_m = d
    await c.message.edit_text(
        f"Дистанция выбрана: {d} м.\n\n{ASK_PACE_TEXT}",
        parse_mode="Markdown",
        reply_markup=make_reset_kb(),
    )
    await c.answer()

@dp.message()
async def handle_text(m: Message):
    st = get_state(m.chat.id)

    if st.distance_m is None:
        await m.answer("Сначала выбери дистанцию кнопкой:", reply_markup=make_distance_kb())
        return

    pace_s = parse_pace_seconds(m.text)
    if pace_s is None:
        await m.answer("Не распознал темп. Пример: `4:45`", parse_mode="Markdown")
        return

    d = st.distance_m
    t_sec = (pace_s * d) / 1000.0

    await m.answer(
        "Вход:\n"
        f"• Дистанция: {d} м\n"
        f"• Темп: {pace_str(pace_s)}\n\n"
        "Результат:\n"
        f"• Время: {seconds_to_time(t_sec)}",
        reply_markup=make_distance_kb(),
    )

async def main():
    bot = Bot(BOT_TOKEN)
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
