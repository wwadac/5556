import json
from aiogram import types
from keyboards import main_menu

STORAGE = "storage.json"

def load():
    with open(STORAGE, "r", encoding="utf-8") as f:
        return json.load(f)

def save(data):
    with open(STORAGE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

async def start_handler(message: types.Message):
    await message.answer(
        "🤖 Business AutoReply Bot\n\nНастрой автоответы 👇",
        reply_markup=main_menu()
    )
