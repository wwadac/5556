import asyncio
import json
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from aiogram.filters import Command
from aiogram.enums import ChatAction
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

BOT_TOKEN = "8556723456:AAFw-r-WKOC4A1kNw9ovHBdVF0Cd08Fbk7E"
DATA_FILE = "settings.json"

bot = Bot(BOT_TOKEN)
dp = Dispatcher()


# ---------- STORAGE ----------
def load():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

db = load()


def cfg(chat_id):
    chat_id = str(chat_id)
    if chat_id not in db:
        db[chat_id] = {
            "enabled": True,
            "greet": "приветик 😊",
            "sticker": None,
            "follow": "Как могу помочь?",
            "delay": 20,
            "business_id": None
        }
        save(db)
    return db[chat_id]


# ---------- FSM ----------
class SetState(StatesGroup):
    greet = State()
    sticker = State()
    follow = State()
    delay = State()


# ---------- UI ----------
def menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔁 Вкл / Выкл", callback_data="toggle")],
        [InlineKeyboardButton(text="✏️ Привет-текст", callback_data="greet")],
        [InlineKeyboardButton(text="🎭 Стикер", callback_data="sticker")],
        [InlineKeyboardButton(text="💬 Follow-up", callback_data="follow")],
        [InlineKeyboardButton(text="⏱ Задержка", callback_data="delay")]
    ])


@dp.message(Command("start"))
async def start(msg: Message):
    cfg(msg.chat.id)
    await msg.answer("⚙️ Business Bot настройки:", reply_markup=menu())


@dp.callback_query(F.data == "toggle")
async def toggle(cb):
    c = cfg(cb.message.chat.id)
    c["enabled"] = not c["enabled"]
    save(db)
    await cb.message.edit_text(
        f"Автоответ: {'✅ ВКЛ' if c['enabled'] else '❌ ВЫКЛ'}",
        reply_markup=menu()
    )


@dp.callback_query(F.data.in_(["greet", "sticker", "follow", "delay"]))
async def set_any(cb, state: FSMContext):
    await state.set_state(getattr(SetState, cb.data))
    await cb.message.answer("Отправь новое значение")


@dp.message(SetState.greet)
async def set_greet(msg: Message, state: FSMContext):
    cfg(msg.chat.id)["greet"] = msg.text
    save(db)
    await msg.answer("✅ Привет сохранён")
    await state.clear()


@dp.message(SetState.follow)
async def set_follow(msg: Message, state: FSMContext):
    cfg(msg.chat.id)["follow"] = msg.text
    save(db)
    await msg.answer("✅ Follow-up сохранён")
    await state.clear()


@dp.message(SetState.delay)
async def set_delay(msg: Message, state: FSMContext):
    cfg(msg.chat.id)["delay"] = int(msg.text)
    save(db)
    await msg.answer("⏱ Задержка сохранена")
    await state.clear()


@dp.message(SetState.sticker, F.sticker)
async def set_sticker(msg: Message, state: FSMContext):
    cfg(msg.chat.id)["sticker"] = msg.sticker.file_id
    save(db)
    await msg.answer("🎭 Стикер сохранён")
    await state.clear()


# ---------- BUSINESS LOGIC ----------
@dp.message()
async def business_handler(msg: Message):
    c = cfg(msg.chat.id)

    if msg.business_connection_id:
        c["business_id"] = msg.business_connection_id
        save(db)

    if not c["enabled"]:
        return

    text = (msg.text or "").lower()

    # Ты написал "привет"
    if msg.outgoing and ("привет" in text):
        await bot.send_message(
            chat_id=msg.chat.id,
            text=c["greet"],
            business_connection_id=c["business_id"]
        )

        if c["sticker"]:
            await bot.send_sticker(
                chat_id=msg.chat.id,
                sticker=c["sticker"],
                business_connection_id=c["business_id"]
            )

    # Ответ собеседника
    if not msg.outgoing and msg.reply_to_message:
        await bot.read_business_message(
