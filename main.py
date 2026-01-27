import asyncio
import json
import logging
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
import os

# ==================== НАСТРОЙКА ====================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен бота (получи у @BotFather)
BOT_TOKEN = "8556723456:AAFeT0XjYIF9yEYNJnyKH6VWniFLllb6nq4"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ==================== ХРАНЕНИЕ ДАННЫХ ====================
class DataStorage:
    def __init__(self):
        self.data_file = 'bot_data.json'
        self.load_data()
    
    def load_data(self):
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
        else:
            self.data = {
                'greetings': {
                    'привет': {
                        'text': 'Приветик! 😊',
                        'sticker_id': None,
                        'enabled': True
                    }
                },
                'follow_up': {
                    'text': 'Как твои дела?',
                    'delay_minutes': 3,
                    'enabled': True
                },
                'auto_reply_enabled': True
            }
            self.save_data()
    
    def save_data(self):
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

storage = DataStorage()

# ==================== СОСТОЯНИЯ FSM ====================
class Form(StatesGroup):
    waiting_greeting_trigger = State()
    waiting_greeting_text = State()
    waiting_greeting_sticker = State()
    waiting_followup_text = State()
    waiting_followup_delay = State()

# ==================== ИНЛАЙН-КЛАВИАТУРЫ ====================
def get_main_menu() -> InlineKeyboardMarkup:
    """Главное меню с инлайн-кнопками[citation:5]"""
    builder = InlineKeyboardBuilder()
    
    status_icon = "✅" if storage.data['auto_reply_enabled'] else "❌"
    
    builder.row(
        InlineKeyboardButton(text=f"Автоответы: {status_icon}", 
                           callback_data="toggle_auto_reply")
    )
    builder.row(
        InlineKeyboardButton(text="✏️ Триггеры и ответы", callback_data="menu_greetings"),
        InlineKeyboardButton(text="⏱ Настройка задержки", callback_data="menu_followup")
    )
    builder.row(
        InlineKeyboardButton(text="📊 Статистика", callback_data="stats"),
        InlineKeyboardButton(text="🆘 Помощь", callback_data="help")
    )
    
    return builder.as_markup()

def get_greetings_menu() -> InlineKeyboardMarkup:
    """Меню управления триггерами"""
    builder = InlineKeyboardBuilder()
    
    # Показываем существующие триггеры
    greetings = storage.data['greetings']
    for trigger, data in greetings.items():
        status = "✅" if data['enabled'] else "❌"
        builder.row(
            InlineKeyboardButton(
                text=f"{status} '{trigger}' → '{data['text'][:15]}...'",
                callback_data=f"edit_greeting:{trigger}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(text="➕ Добавить триггер", callback_data="add_greeting"),
        InlineKeyboardButton(text="« Назад", callback_data="main_menu")
    )
    
    return builder.as_markup()

def get_followup_menu() -> InlineKeyboardMarkup:
    """Меню настройки follow-up сообщений"""
    builder = InlineKeyboardBuilder()
    
    followup = storage.data['follow_up']
    status = "✅" if followup['enabled'] else "❌"
    
    builder.row(
        InlineKeyboardButton(
            text=f"Follow-up: {status}",
            callback_data="toggle_followup"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=f"Текст: {followup['text'][:20]}...",
            callback_data="edit_followup_text"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=f"Задержка: {followup['delay_minutes']} мин",
            callback_data="edit_followup_delay"
        )
    )
    builder.row(
        InlineKeyboardButton(text="« Назад", callback_data="main_menu")
    )
    
    return builder.as_markup()

def get_back_button(menu: str = "main_menu") -> InlineKeyboardMarkup:
    """Кнопка 'Назад'"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="« Назад", callback_data=menu))
    return builder.as_markup()

# ==================== ОБРАБОТЧИКИ КОМАНД ====================
@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start[citation:5]"""
    await message.answer(
        "🤖 **Бот-автоответчик активирован!**\n\n"
        "Я буду автоматически отвечать на сообщения с триггерными словами.\n"
        "Используйте меню ниже для настройки:",
        reply_markup=get_main_menu(),
        parse_mode="Markdown"
    )

@dp.message(Command("settings"))
async def cmd_settings(message: Message):
    """Обработчик команды /settings"""
    await message.answer(
        "⚙️ **Панель управления**\nВыберите раздел для настройки:",
        reply_markup=get_main_menu(),
        parse_mode="Markdown"
    )

# ==================== ОБРАБОТЧИКИ CALLBACK-ЗАПРОСОВ ====================
@dp.callback_query(F.data == "main_menu")
async def main_menu_handler(callback: CallbackQuery):
    """Главное меню"""
    await callback.message.edit_text(
        "🤖 **Главное меню**\nВыберите раздел:",
        reply_markup=get_main_menu(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data == "toggle_auto_reply")
async def toggle_auto_reply_handler(callback: CallbackQuery):
    """Включение/выключение автоответов"""
    storage.data['auto_reply_enabled'] = not storage.data['auto_reply_enabled']
    storage.save_data()
    
    status = "включены" if storage.data['auto_reply_enabled'] else "выключены"
    await callback.message.edit_text(
        f"✅ **Автоответы {status}**\n\n"
        f"Статус изменен. Автоматические ответы теперь {status}.",
        reply_markup=get_main_menu(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data == "menu_greetings")
async def menu_greetings_handler(callback: CallbackQuery):
    """Меню триггеров"""
    await callback.message.edit_text(
        "✏️ **Управление триггерами**\n\n"
        "Список ваших триггерных слов и ответов:",
        reply_markup=get_greetings_menu(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data == "menu_followup")
async def menu_followup_handler(callback: CallbackQuery):
    """Меню follow-up сообщений"""
    followup = storage.data['follow_up']
    
    await callback.message.edit_text(
        "⏱ **Настройка отложенных ответов**\n\n"
        f"• Статус: {'Включено ✅' if followup['enabled'] else 'Выключено ❌'}\n"
        f"• Текст: {followup['text']}\n"
        f"• Задержка: {followup['delay_minutes']} минут\n\n"
        "Выберите параметр для изменения:",
        reply_markup=get_followup_menu(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("edit_greeting:"))
async def edit_greeting_handler(callback: CallbackQuery, state: FSMContext):
    """Редактирование конкретного триггера"""
    trigger = callback.data.split(":")[1]
    greeting_data = storage.data['greetings'].get(trigger)
    
    if not greeting_data:
        await callback.answer("Триггер не найден!")
        return
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📝 Изменить текст", 
                           callback_data=f"change_text:{trigger}"),
        InlineKeyboardButton(text="🖼 Изменить стикер", 
                           callback_data=f"change_sticker:{trigger}")
    )
    builder.row(
        InlineKeyboardButton(
            text=f"{'❌ Выключить' if greeting_data['enabled'] else '✅ Включить'}",
            callback_data=f"toggle_greeting:{trigger}"
        ),
        InlineKeyboardButton(text="🗑 Удалить", 
                           callback_data=f"delete_greeting:{trigger}")
    )
    builder.row(
        InlineKeyboardButton(text="« Назад", callback_data="menu_greetings")
    )
    
    sticker_info = f"\nСтикер: {'есть' if greeting_data['sticker_id'] else 'нет'}" 
    
    await callback.message.edit_text(
        f"✏️ **Редактирование триггера**\n\n"
        f"• Триггер: `{trigger}`\n"
        f"• Ответ: {greeting_data['text']}\n"
        f"• Статус: {'Включен ✅' if greeting_data['enabled'] else 'Выключен ❌'}"
        f"{sticker_info}\n\n"
        f"Выберите действие:",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data == "add_greeting")
async def add_greeting_handler(callback: CallbackQuery, state: FSMContext):
    """Добавление нового триггера"""
    await callback.message.edit_text(
        "📝 **Добавление нового триггера**\n\n"
        "Отправьте мне слово-триггер (например, 'привет'):",
        reply_markup=get_back_button("menu_greetings"),
        parse_mode="Markdown"
    )
    await state.set_state(Form.waiting_greeting_trigger)
    await callback.answer()

@dp.callback_query(F.data.startswith("change_text:"))
async def change_text_handler(callback: CallbackQuery, state: FSMContext):
    """Изменение текста ответа"""
    trigger = callback.data.split(":")[1]
    await state.update_data(editing_trigger=trigger)
    
    await callback.message.edit_text(
        f"📝 **Изменение текста ответа**\n\n"
        f"Текущий текст: `{storage.data['greetings'][trigger]['text']}`\n\n"
        f"Отправьте новый текст ответа для триггера '{trigger}':",
        reply_markup=get_back_button(f"edit_greeting:{trigger}"),
        parse_mode="Markdown"
    )
    await state.set_state(Form.waiting_greeting_text)
    await callback.answer()

@dp.callback_query(F.data.startswith("change_sticker:"))
async def change_sticker_handler(callback: CallbackQuery, state: FSMContext):
    """Изменение стикера"""
    trigger = callback.data.split(":")[1]
    await state.update_data(editing_trigger=trigger)
    
    await callback.message.edit_text(
        "🖼 **Добавление стикера**\n\n"
        "Отправьте мне стикер, который будет отправляться вместе с текстом "
        "(или отправьте 'удалить', чтобы убрать стикер):",
        reply_markup=get_back_button(f"edit_greeting:{trigger}"),
        parse_mode="Markdown"
    )
    await state.set_state(Form.waiting_greeting_sticker)
    await callback.answer()

@dp.callback_query(F.data == "edit_followup_text")
async def edit_followup_text_handler(callback: CallbackQuery, state: FSMContext):
    """Изменение текста follow-up сообщения"""
    await callback.message.edit_text(
        "📝 **Изменение текста follow-up**\n\n"
        f"Текущий текст: `{storage.data['follow_up']['text']}`\n\n"
        "Отправьте новый текст для отложенного ответа:",
        reply_markup=get_back_button("menu_followup"),
        parse_mode="Markdown"
    )
    await state.set_state(Form.waiting_followup_text)
    await callback.answer()

@dp.callback_query(F.data == "edit_followup_delay")
async def edit_followup_delay_handler(callback: CallbackQuery, state: FSMContext):
    """Изменение задержки follow-up"""
    await callback.message.edit_text(
        "⏱ **Изменение задержки**\n\n"
        f"Текущая задержка: {storage.data['follow_up']['delay_minutes']} минут\n\n"
        "Отправьте новую задержку в минутах (от 1 до 60):",
        reply_markup=get_back_button("menu_followup"),
        parse_mode="Markdown"
    )
    await state.set_state(Form.waiting_followup_delay)
    await callback.answer()

@dp.callback_query(F.data == "stats")
async def stats_handler(callback: CallbackQuery):
    """Статистика бота"""
    greetings = storage.data['greetings']
    followup = storage.data['follow_up']
    
    stats_text = (
        "📊 **Статистика бота**\n\n"
        f"• Автоответы: {'✅ Включены' if storage.data['auto_reply_enabled'] else '❌ Выключены'}\n"
        f"• Количество триггеров: {len(greetings)}\n"
        f"• Follow-up: {'✅ Включен' if followup['enabled'] else '❌ Выключен'}\n"
        f"• Задержка follow-up: {followup['delay_minutes']} мин\n\n"
        "**Активные триггеры:**\n"
    )
    
    for trigger, data in greetings.items():
        if data['enabled']:
            stats_text += f"• `{trigger}` → {data['text'][:20]}...\n"
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="« Назад", callback_data="main_menu"))
    
    await callback.message.edit_text(
        stats_text,
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data == "help")
async def help_handler(callback: CallbackQuery):
    """Помощь"""
    help_text = (
        "🆘 **Помощь по боту**\n\n"
        "🤖 **Основные функции:**\n"
        "1. Автоматические ответы на триггерные слова\n"
        "2. Отложенные ответы (follow-up)\n"
        "3. Настройка стикеров\n\n"
        "⚙️ **Как настроить:**\n"
        "1. Добавьте триггеры в разделе 'Триггеры и ответы'\n"
        "2. Настройте текст и стикеры для каждого триггера\n"
        "3. Включите автоответы в главном меню\n\n"
        "⏱ **Follow-up сообщения:**\n"
        "После ответа собеседника бот отправит отложенное сообщение через указанное время\n\n"
        "💡 **Примечание:** Бот работает в личных чатах и группах (если добавлен в группу)"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="« Назад", callback_data="main_menu"))
    
    await callback.message.edit_text(
        help_text,
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )
    await callback.answer()

# ==================== ОБРАБОТЧИКИ СОСТОЯНИЙ FSM ====================
@dp.message(Form.waiting_greeting_trigger)
async def process_greeting_trigger(message: Message, state: FSMContext):
    """Обработка нового триггера"""
    trigger = message.text.strip().lower()
    
    if trigger in storage.data['greetings']:
        await message.answer(
            f"⚠️ Триггер '{trigger}' уже существует!",
            reply_markup=get_back_button("menu_greetings")
        )
        return
    
    # Создаем новый триггер
    storage.data['greetings'][trigger] = {
        'text': f"Ответ на '{trigger}'",
        'sticker_id': None,
        'enabled': True
    }
    storage.save_data()
    
    await state.clear()
    await message.answer(
        f"✅ Триггер '{trigger}' добавлен!\n"
        f"Теперь настройте текст ответа для него.",
        reply_markup=get_greetings_menu()
    )

@dp.message(Form.waiting_greeting_text)
async def process_greeting_text(message: Message, state: FSMContext):
    """Обработка текста ответа"""
    data = await state.get_data()
    trigger = data['editing_trigger']
    
    storage.data['greetings'][trigger]['text'] = message.text
    storage.save_data()
    
    await state.clear()
    await message.answer(
        f"✅ Текст ответа для '{trigger}' обновлен!",
        reply_markup=get_greetings_menu()
    )

@dp.message(Form.waiting_greeting_sticker)
async def process_greeting_sticker(message: Message, state: FSMContext):
    """Обработка стикера"""
    if message.text and message.text.lower() == 'удалить':
        # Удаляем стикер
        data = await state.get_data()
        trigger = data['editing_trigger']
        storage.data['greetings'][trigger]['sticker_id'] = None
        storage.save_data()
        
        await state.clear()
        await message.answer(
            f"✅ Стикер для '{trigger}' удален!",
            reply_markup=get_greetings_menu()
        )
        return
    
    if not message.sticker:
        await message.answer("❌ Пожалуйста, отправьте стикер!")
        return
    
    data = await state.get_data()
    trigger = data['editing_trigger']
    storage.data['greetings'][trigger]['sticker_id'] = message.sticker.file_id
    storage.save_data()
    
    await state.clear()
    await message.answer(
        f"✅ Стикер для '{trigger}' сохранен!",
        reply_markup=get_greetings_menu()
    )

@dp.message(Form.waiting_followup_text)
async def process_followup_text(message: Message, state: FSMContext):
    """Обработка текста follow-up"""
    storage.data['follow_up']['text'] = message.text
    storage.save_data()
    
    await state.clear()
    await message.answer(
        "✅ Текст follow-up обновлен!",
        reply_markup=get_followup_menu()
    )

@dp.message(Form.waiting_followup_delay)
async def process_followup_delay(message: Message, state: FSMContext):
    """Обработка задержки follow-up"""
    try:
        delay = int(message.text.strip())
        if 1 <= delay <= 60:
            storage.data['follow_up']['delay_minutes'] = delay
            storage.save_data()
            
            await state.clear()
            await message.answer(
                f"✅ Задержка изменена на {delay} минут!",
                reply_markup=get_followup_menu()
            )
        else:
            await message.answer(
                "❌ Введите число от 1 до 60!",
                reply_markup=get_back_button("menu_followup")
            )
    except ValueError:
        await message.answer(
            "❌ Введите число от 1 до 60!",
            reply_markup=get_back_button("menu_followup")
        )

# ==================== АВТООТВЕТЧИК ====================
@dp.message()
async def auto_reply_handler(message: Message):
    """Основной обработчик автоответов"""
    # Проверяем, включены ли автоответы
    if not storage.data['auto_reply_enabled']:
        return
    
    # Игнорируем служебные сообщения
    if not message.text or message.text.startswith('/'):
        return
    
    # Проверяем триггеры (регистронезависимо)
    user_text = message.text.lower()
    
    for trigger, data in storage.data['greetings'].items():
        if data['enabled'] and trigger in user_text:
            # Имитируем набор текста[citation:6]
            await bot.send_chat_action(
                chat_id=message.chat.id,
                action="typing"
            )
            
            # Отправляем текстовый ответ
            await message.answer(data['text'])
            
            # Отправляем стикер, если он есть
            if data['sticker_id']:
                await message.answer_sticker(data['sticker_id'])
            
            # Планируем follow-up сообщение, если включено
            if storage.data['follow_up']['enabled']:
                await schedule_followup(message.chat.id)
            
            break

async def schedule_followup(chat_id: int):
    """Планирование отложенного ответа"""
    delay = storage.data['follow_up']['delay_minutes']
    text = storage.data['follow_up']['text']
    
    await asyncio.sleep(delay * 60)  # Преобразуем минуты в секунды
    
    # Имитируем чтение сообщения (галочки)[citation:6]
    await bot.send_chat_action(chat_id=chat_id, action="typing")
    await asyncio.sleep(2)  # Имитация набора текста
    
    # Отправляем follow-up сообщение
    await bot.send_message(chat_id=chat_id, text=text)

# ==================== ЗАПУСК БОТА ====================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
