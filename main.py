import asyncio
import json
import logging
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
            # Изначальные настройки с триггером "привет"
            self.data = {
                'greetings': {
                    'привет': {
                        'text': 'Приветик! 😊',
                        'sticker_id': None,  # Можно задать ID стикера
                        'enabled': True
                    }
                },
                'follow_up': {
                    'text': 'Как дела?',
                    'delay_seconds': 30,  # Задержка от 10 сек до 300 сек (5 минут)
                    'enabled': True
                },
                'auto_reply_enabled': True,
                'active_chats': {}  # Для отслеживания диалогов
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
    """Главное меню с инлайн-кнопками"""
    builder = InlineKeyboardBuilder()
    
    status_icon = "✅" if storage.data['auto_reply_enabled'] else "❌"
    
    builder.row(
        InlineKeyboardButton(text=f"🤖 Автоответы: {status_icon}", 
                           callback_data="toggle_auto_reply")
    )
    builder.row(
        InlineKeyboardButton(text="✏️ Настройка триггеров", callback_data="menu_greetings"),
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
    
    greetings = storage.data['greetings']
    
    if not greetings:
        builder.row(
            InlineKeyboardButton(text="➕ Добавить первый триггер", callback_data="add_greeting")
        )
    else:
        for trigger, data in greetings.items():
            status = "✅" if data['enabled'] else "❌"
            sticker_icon = "🖼️" if data['sticker_id'] else ""
            builder.row(
                InlineKeyboardButton(
                    text=f"{status} '{trigger}' → '{data['text'][:15]}...'{sticker_icon}",
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
            text=f"✏️ Текст: {followup['text'][:20]}...",
            callback_data="edit_followup_text"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=f"⏱ Задержка: {followup['delay_seconds']} сек",
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

def get_edit_greeting_menu(trigger: str) -> InlineKeyboardMarkup:
    """Меню редактирования конкретного триггера"""
    builder = InlineKeyboardBuilder()
    
    greeting_data = storage.data['greetings'][trigger]
    
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
    
    return builder.as_markup()

# ==================== ОБРАБОТЧИКИ КОМАНД ====================
@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    await message.answer(
        "🤖 **Бот-автоответчик активирован!**\n\n"
        "✨ **Функции:**\n"
        "• Автоответ на триггеры (например, на 'привет')\n"
        "• Отправка текста + стикера\n"
        "• Отложенные ответы (follow-up)\n\n"
        "⚙️ **Используйте меню для настройки:**",
        reply_markup=get_main_menu(),
        parse_mode="Markdown"
    )

@dp.message(Command("settings"))
async def cmd_settings(message: Message):
    """Обработчик команды /settings"""
    await message.answer(
        "⚙️ **Панель управления**\nВыберите раздел:",
        reply_markup=get_main_menu(),
        parse_mode="Markdown"
    )

@dp.message(Command("test"))
async def cmd_test(message: Message):
    """Тестовая команда для проверки автоответа"""
    test_text = "привет"
    if test_text in storage.data['greetings']:
        data = storage.data['greetings'][test_text]
        if data['enabled']:
            await message.answer(f"✅ Тест: на '{test_text}' бот ответит:\n**{data['text']}**")
            if data['sticker_id']:
                await message.answer("...и отправит стикер 🖼")
            else:
                await message.answer("...стикер не настроен")
        else:
            await message.answer(f"❌ Триггер '{test_text}' выключен")
    else:
        await message.answer(f"❌ Триггер '{test_text}' не найден")

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
    count = len(storage.data['greetings'])
    
    await callback.message.edit_text(
        f"✏️ **Управление триггерами**\n\n"
        f"Настроено триггеров: {count}\n"
        "Список ваших триггерных слов и ответов:\n"
        "✅ - включен, ❌ - выключен, 🖼️ - есть стикер",
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
        f"• Статус: {'✅ Включено' if followup['enabled'] else '❌ Выключено'}\n"
        f"• Текст: {followup['text']}\n"
        f"• Задержка: {followup['delay_seconds']} секунд\n\n"
        "_Бот отправит это сообщение после ответа собеседника_",
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
        await callback.answer("Триггер не найден!", show_alert=True)
        return
    
    sticker_info = f"🖼 Стикер: {'есть' if greeting_data['sticker_id'] else 'не настроен'}" 
    
    await callback.message.edit_text(
        f"✏️ **Редактирование триггера**\n\n"
        f"• Триггер: `{trigger}`\n"
        f"• Ответ: {greeting_data['text']}\n"
        f"• Статус: {'✅ Включен' if greeting_data['enabled'] else '❌ Выключен'}\n"
        f"• {sticker_info}\n\n"
        f"Выберите действие:",
        reply_markup=get_edit_greeting_menu(trigger),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data == "add_greeting")
async def add_greeting_handler(callback: CallbackQuery, state: FSMContext):
    """Добавление нового триггера"""
    await callback.message.edit_text(
        "📝 **Добавление нового триггера**\n\n"
        "Введите слово или фразу, на которую бот будет реагировать\n"
        "Пример: `привет`, `здравствуйте`, `добрый день`",
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
        f"Текущий ответ на '{trigger}':\n`{storage.data['greetings'][trigger]['text']}`\n\n"
        f"Введите новый текст ответа:",
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
    
    current_sticker = storage.data['greetings'][trigger]['sticker_id']
    sticker_info = "\n_Пришлите 'удалить' чтобы убрать стикер_" if current_sticker else ""
    
    await callback.message.edit_text(
        f"🖼 **Настройка стикера для '{trigger}'**\n\n"
        f"{'Стикер уже настроен' if current_sticker else 'Стикер не настроен'}"
        f"{sticker_info}\n\n"
        f"Отправьте стикер (не файл, а именно стикер):",
        reply_markup=get_back_button(f"edit_greeting:{trigger}"),
        parse_mode="Markdown"
    )
    await state.set_state(Form.waiting_greeting_sticker)
    await callback.answer()

@dp.callback_query(F.data.startswith("toggle_greeting:"))
async def toggle_greeting_handler(callback: CallbackQuery):
    """Включение/выключение триггера"""
    trigger = callback.data.split(":")[1]
    greeting_data = storage.data['greetings'].get(trigger)
    
    if greeting_data:
        greeting_data['enabled'] = not greeting_data['enabled']
        storage.save_data()
        
        status = "включен" if greeting_data['enabled'] else "выключен"
        await callback.answer(f"✅ Триггер '{trigger}' {status}", show_alert=True)
        
        # Обновляем сообщение
        await edit_greeting_handler(callback, None)
    else:
        await callback.answer("❌ Триггер не найден", show_alert=True)

@dp.callback_query(F.data.startswith("delete_greeting:"))
async def delete_greeting_handler(callback: CallbackQuery):
    """Удаление триггера"""
    trigger = callback.data.split(":")[1]
    
    if trigger in storage.data['greetings']:
        del storage.data['greetings'][trigger]
        storage.save_data()
        
        await callback.answer(f"✅ Триггер '{trigger}' удален", show_alert=True)
        await menu_greetings_handler(callback)
    else:
        await callback.answer("❌ Триггер не найден", show_alert=True)

@dp.callback_query(F.data == "toggle_followup")
async def toggle_followup_handler(callback: CallbackQuery):
    """Включение/выключение follow-up"""
    storage.data['follow_up']['enabled'] = not storage.data['follow_up']['enabled']
    storage.save_data()
    
    status = "включены" if storage.data['follow_up']['enabled'] else "выключены"
    await callback.answer(f"✅ Follow-up сообщения {status}", show_alert=True)
    await menu_followup_handler(callback)

@dp.callback_query(F.data == "edit_followup_text")
async def edit_followup_text_handler(callback: CallbackQuery, state: FSMContext):
    """Изменение текста follow-up сообщения"""
    await callback.message.edit_text(
        "📝 **Изменение текста follow-up**\n\n"
        f"Текущий текст: `{storage.data['follow_up']['text']}`\n\n"
        "Введите новый текст для отложенного ответа:",
        reply_markup=get_back_button("menu_followup"),
        parse_mode="Markdown"
    )
    await state.set_state(Form.waiting_followup_text)
    await callback.answer()

@dp.callback_query(F.data == "edit_followup_delay")
async def edit_followup_delay_handler(callback: CallbackQuery, state: FSMContext):
    """Изменение задержки follow-up"""
    await callback.message.edit_text(
        "⏱ **Настройка задержки**\n\n"
        f"Текущая задержка: {storage.data['follow_up']['delay_seconds']} секунд\n\n"
        "Введите новую задержку в **секундах** (от 10 до 300):\n"
        "_Пример: 30 = 30 секунд, 120 = 2 минуты_",
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
    
    active_count = sum(1 for g in greetings.values() if g['enabled'])
    stickers_count = sum(1 for g in greetings.values() if g['sticker_id'])
    
    stats_text = (
        "📊 **Статистика бота**\n\n"
        f"• 🤖 Автоответы: {'✅ Включены' if storage.data['auto_reply_enabled'] else '❌ Выключены'}\n"
        f"• ✏️ Триггеров всего: {len(greetings)}\n"
        f"• ✅ Активных триггеров: {active_count}\n"
        f"• 🖼 Триггеров со стикерами: {stickers_count}\n"
        f"• ⏱ Follow-up: {'✅ Включен' if followup['enabled'] else '❌ Выключен'}\n"
        f"• 🕐 Задержка follow-up: {followup['delay_seconds']} сек\n\n"
    )
    
    if active_count > 0:
        stats_text += "**Активные триггеры:**\n"
        for trigger, data in greetings.items():
            if data['enabled']:
                sticker_icon = " 🖼" if data['sticker_id'] else ""
                stats_text += f"• `{trigger}` → {data['text'][:20]}...{sticker_icon}\n"
    
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
        "🤖 **Как работает бот:**\n"
        "1. Когда кто-то пишет слово-триггер (например, 'привет')\n"
        "2. Бот автоматически отвечает настроенным текстом\n"
        "3. И отправляет настроенный стикер (если задан)\n"
        "4. После ответа собеседника бот отправляет follow-up сообщение\n\n"
        "⚙️ **Настройка:**\n"
        "• ✏️ **Триггеры и ответы** - добавьте слова и настройте ответы\n"
        "• 🖼 **Стикеры** - прикрепите стикер к каждому триггеру\n"
        "• ⏱ **Задержка** - настройте время ожидания follow-up (10-300 сек)\n\n"
        "💡 **Пример:**\n"
        "1. Добавьте триггер 'привет'\n"
        "2. Настройте ответ 'Приветик! 😊'\n"
        "3. Прикрепите веселый стикер\n"
        "4. Готово! Теперь на 'привет' бот ответит текстом и стикером"
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
    
    if not trigger:
        await message.answer("❌ Триггер не может быть пустым!")
        return
    
    if trigger in storage.data['greetings']:
        await message.answer(
            f"⚠️ Триггер '{trigger}' уже существует!",
            reply_markup=get_greetings_menu()
        )
        await state.clear()
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
        f"Теперь настройте текст ответа и стикер.",
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
        f"✅ Текст ответа для '{trigger}' обновлен!\n"
        f"Теперь: `{message.text}`",
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
        await message.answer("❌ Пожалуйста, отправьте стикер (не файл)!")
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
        if 10 <= delay <= 300:  # От 10 секунд до 5 минут (300 сек)
            storage.data['follow_up']['delay_seconds'] = delay
            storage.save_data()
            
            await state.clear()
            minutes = delay // 60
            seconds = delay % 60
            time_str = f"{minutes} мин {seconds} сек" if minutes > 0 else f"{delay} сек"
            
            await message.answer(
                f"✅ Задержка изменена на {time_str}!",
                reply_markup=get_followup_menu()
            )
        else:
            await message.answer(
                "❌ Введите число от 10 до 300 секунд (5 минут)!",
                reply_markup=get_back_button("menu_followup")
            )
    except ValueError:
        await message.answer(
            "❌ Введите число от 10 до 300 секунд!",
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
    
    # Игнорируем сообщения от самого бота
    if message.from_user.id == bot.id:
        return
    
    user_text = message.text.lower()
    chat_id = message.chat.id
    
    # Проверяем все триггеры
    for trigger, data in storage.data['greetings'].items():
        if data['enabled'] and trigger in user_text:
            # Имитируем набор текста (печатает...)
            await bot.send_chat_action(
                chat_id=chat_id,
                action="typing"
            )
            await asyncio.sleep(1)  # Небольшая задержка для реалистичности
            
            # Отправляем текстовый ответ
            await message.answer(data['text'])
            
            # Отправляем стикер, если он есть
            if data['sticker_id']:
                await asyncio.sleep(0.5)  # Небольшая пауза
                await message.answer_sticker(data['sticker_id'])
            
            # Сохраняем информацию о диалоге для follow-up
            storage.data['active_chats'][chat_id] = {
                'last_trigger': trigger,
                'timestamp': asyncio.get_event_loop().time(),
                'user_id': message.from_user.id
            }
            storage.save_data()
            
            # Запускаем follow-up, если включено
            if storage.data['follow_up']['enabled']:
                asyncio.create_task(schedule_followup(chat_id, message.message_id))
            
            break

async def schedule_followup(chat_id: int, reply_to_msg_id: int):
    """Планирование отложенного ответа"""
    delay = storage.data['follow_up']['delay_seconds']
    text = storage.data['follow_up']['text']
    
    # Ждем указанную задержку
    await asyncio.sleep(delay)
    
    try:
        # Имитируем чтение сообщения (две галочки)
        await bot.send_chat_action(chat_id=chat_id, action="typing")
        await asyncio.sleep(2)  # Имитация набора текста
        
        # Отправляем follow-up сообщение
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_to_message_id=reply_to_msg_id
        )
        
        # Удаляем чат из активных
        if chat_id in storage.data['active_chats']:
            del storage.data['active_chats'][chat_id]
            storage.save_data()
            
    except Exception as e:
        logger.error(f"Ошибка при отправке follow-up: {e}")

# ==================== ЗАПУСК БОТА ====================
async def main():
    print("🤖 Бот запускается...")
    print(f"• Триггеров: {len(storage.data['greetings'])}")
    print(f"• Автоответы: {'ВКЛ' if storage.data['auto_reply_enabled'] else 'ВЫКЛ'}")
    print(f"• Follow-up: {'ВКЛ' if storage.data['follow_up']['enabled'] else 'ВЫКЛ'}")
    print(f"• Задержка: {storage.data['follow_up']['delay_seconds']} сек")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
