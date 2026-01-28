import asyncio
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import ReplyKeyboardRemove

# ТОКЕН ВАШЕГО БОТА
API_TOKEN = '8556723456:AAFw-r-WKOC4A1kNw9ovHBdVF0Cd08Fbk7E'

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Временное хранилище настроек (в идеале использовать БД)
settings = {
    "trigger_word": "привет",
    "greeting_text": "Приветик! 😊",
    "sticker_id": None,
    "follow_up_text": "Как твои дела? Что нового?",
    "min_delay": 20,
    "max_delay": 60
}

class SetupStates(StatesGroup):
    waiting_for_trigger = State()
    waiting_for_greeting = State()
    waiting_for_sticker = State()
    waiting_for_followup = State()
    waiting_for_delay = State()

# --- КЛАВИАТУРА НАСТРОЕК ---
def get_settings_kb():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="Слово-триггер", callback_data="set_trigger"))
    builder.row(types.InlineKeyboardButton(text="Текст приветствия", callback_data="set_greeting"))
    builder.row(types.InlineKeyboardButton(text="Установить стикер", callback_data="set_sticker"))
    builder.row(types.InlineKeyboardButton(text="Второй текст (follow-up)", callback_data="set_followup"))
    builder.row(types.InlineKeyboardButton(text="Настроить задержку", callback_data="set_delay"))
    builder.row(types.InlineKeyboardButton(text="Посмотреть настройки", callback_data="show_settings"))
    return builder.as_markup()

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer("🤖 Бот для Telegram Business запущен.\nНастройте ответы ниже:", reply_markup=get_settings_kb())

# --- ОБРАБОТКА НАСТРОЕК (FSM) ---
@dp.callback_query(F.data == "set_trigger")
async def set_trigger(cb: types.CallbackQuery, state: FSMContext):
    await cb.message.answer("Введите слово, на которое бот будет реагировать (например: привет):")
    await state.set_state(SetupStates.waiting_for_trigger)

@dp.message(SetupStates.waiting_for_trigger)
async def save_trigger(message: types.Message, state: FSMContext):
    settings["trigger_word"] = message.text.lower()
    await message.answer(f"✅ Триггер сохранен: {settings['trigger_word']}", reply_markup=get_settings_kb())
    await state.clear()

@dp.callback_query(F.data == "set_sticker")
async def set_sticker_req(cb: types.CallbackQuery, state: FSMContext):
    await cb.message.answer("Пришлите мне стикер, который нужно отправлять:")
    await state.set_state(SetupStates.waiting_for_sticker)

@dp.message(SetupStates.waiting_for_sticker, F.sticker)
async def save_sticker(message: types.Message, state: FSMContext):
    settings["sticker_id"] = message.sticker.file_id
    await message.answer("✅ Стикер сохранен!", reply_markup=get_settings_kb())
    await state.clear()

# (Остальные настройки текста делаются аналогично...)

# --- ЛОГИКА БИЗНЕС-БОТА ---

# 1. Реагируем на ваше сообщение (Trigger)
@dp.business_message(F.text)
async def business_trigger_handler(message: types.Message):
    # Проверяем, что это мы написали триггер
    if message.text.lower() == settings["trigger_word"]:
        # Отправляем текст и стикер от вашего имени
        await message.answer(settings["greeting_text"], business_connection_id=message.business_connection_id)
        if settings["sticker_id"]:
            await message.answer_sticker(settings["sticker_id"], business_connection_id=message.business_connection_id)

# 2. Реагируем на ответ собеседника
@dp.business_message()
async def business_reply_handler(message: types.Message):
    # Если сообщение пришло от другого человека (не от нас)
    if message.from_user.id != message.business_connection_id:
        # 1. Читаем сообщение (в Business API это происходит автоматически при получении через бота)
        
        # 2. Ждем заданное время
        delay = random.randint(settings["min_delay"], settings["max_delay"])
        await asyncio.sleep(delay)
        
        # 3. Визуально "печатает"
        await bot.send_chat_action(
            chat_id=message.chat.id, 
            action="typing", 
            business_connection_id=message.business_connection_id
        )
        await asyncio.sleep(3) # Печатаем 3 секунды для реализма
        
        # 4. Отправляем второй текст
        await message.answer(settings["follow_up_text"], business_connection_id=message.business_connection_id)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
