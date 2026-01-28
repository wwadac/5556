import asyncio, json, random
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ChatAction
from config import BOT_TOKEN, ADMIN_ID
from handlers import start_handler, load, save
from keyboards import main_menu

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

# ====== МЕНЮ ======
@dp.message(F.text == "/start")
async def start(msg: Message):
    if msg.from_user.id == ADMIN_ID:
        await start_handler(msg)

# ====== ВКЛ / ВЫКЛ ======
@dp.callback_query(F.data == "toggle")
async def toggle(call: CallbackQuery):
    data = load()
    data["enabled"] = not data["enabled"]
    save(data)

    await call.message.edit_text(
        f"🔴 Состояние бота: {'🟢 ВКЛ' if data['enabled'] else '🔴 ВЫКЛ'}",
        reply_markup=main_menu()
    )

# ====== BUSINESS АВТООТВЕТ ======
@dp.message(F.chat.type == "private")
async def business_autoreply(msg: Message):
    data = load()
    if not data["enabled"]:
        return

    # ТРИГГЕР
    triggers = ["привет", "приветик", "hi", "hello"]
    if msg.text and any(t in msg.text.lower() for t in triggers):

        if data["typing"]:
            await bot.send_chat_action(msg.chat.id, ChatAction.TYPING)

        await msg.answer(data["first_text"])

        if data["sticker_id"]:
            await bot.send_sticker(msg.chat.id, data["sticker_id"])

    # FOLLOW-UP ПОСЛЕ ОТВЕТА
    if msg.reply_to_message:
        delay = random.randint(data["delay_min"], data["delay_max"])
        await asyncio.sleep(delay)

        if data["typing"]:
            await bot.send_chat_action(msg.chat.id, ChatAction.TYPING)

        await msg.answer(data["followup_text"])

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
