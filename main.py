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
from datetime import datetime
import os

# ==================== НАСТРОЙКА ====================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен бота (получи у @BotFather)
BOT_TOKEN = "8556723456:AAFeT0XjYIF9yEYNJnyKH6VWniFLllb6nq4"

# ID владельца (ваш ID в Telegram)
OWNER_ID = 8593061718  # Замените на ваш ID

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ==================== ХРАНЕНИЕ ДАННЫХ ====================
class BusinessBotStorage:
    def __init__(self):
        self.data_file = 'business_bot_data.json'
        self.load_data()
    
    def load_data(self):
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
        else:
            self.data = {
                'owner_id': OWNER_ID,
                'auto_reply_enabled': True,
                'away_messages': {
                    'default': {
                        'text': 'Привет! Сейчас я занят(а), но скоро отвечу 😊\n\nОтправьте /help для быстрой помощи.',
                        'enabled': True
                    },
                    'work': {
                        'text': 'Я на работе, отвечу в перерыве.',
                        'enabled': False
                    },
                    'sleep': {
                        'text': 'Сплю 💤 Отвечу утром!',
                        'enabled': False
                    }
                },
                'quick_replies': {
                    '1': 'Спасибо за сообщение! Отвечу в ближайшее время.',
                    '2': 'Получил(а) ваше сообщение!',
                    '3': 'Скоро свяжусь с вами!'
                },
                'working_hours': {
                    'enabled': False,
                    'start': '09:00',
                    'end': '18:00',
                    'offline_message': 'Рабочий день закончился. Отвечу завтра!'
                },
                'blacklist': [],
                'message_history': {},
                'settings': {
                    'reply_delay': 5,  # Задержка ответа в секундах
                    'signature': '\n\n🤖 Автоответчик',
                    'notify_owner': True  # Уведомлять владельца о новых сообщениях
                }
            }
            self.save_data()
    
    def save_data(self):
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

storage = BusinessBotStorage()

# ==================== СОСТОЯНИЯ FSM ====================
class BusinessBotForm(StatesGroup):
    waiting_away_message = State()
    waiting_quick_reply = State()
    waiting_working_hours = State()

# ==================== ИНЛАЙН-КЛАВИАТУРЫ ====================
def get_business_main_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    status = "✅" if storage.data['auto_reply_enabled'] else "❌"
    
    builder.row(
        InlineKeyboardButton(text=f"🤖 Автоответы: {status}", callback_data="toggle_business_mode")
    )
    builder.row(
        InlineKeyboardButton(text="💬 Сообщения нерабочие", callback_data="menu_away_messages"),
        InlineKeyboardButton(text="⚡ Быстрые ответы", callback_data="menu_quick_replies")
    )
    builder.row(
        InlineKeyboardButton(text="🕐 Рабочие часы", callback_data="menu_working_hours"),
        InlineKeyboardButton(text="⚙️ Настройки", callback_data="menu_settings")
    )
    builder.row(
        InlineKeyboardButton(text="📊 Статистика", callback_data="business_stats"),
        InlineKeyboardButton(text="📋 История", callback_data="message_history")
    )
    
    return builder.as_markup()

def get_away_messages_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    for key, msg in storage.data['away_messages'].items():
        status = "✅" if msg['enabled'] else "❌"
        builder.row(
            InlineKeyboardButton(
                text=f"{status} {key}: {msg['text'][:20]}...",
                callback_data=f"edit_away:{key}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(text="➕ Добавить", callback_data="add_away_message"),
        InlineKeyboardButton(text="« Назад", callback_data="main_menu")
    )
    
    return builder.as_markup()

def get_quick_replies_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    for key, reply in storage.data['quick_replies'].items():
        builder.row(
            InlineKeyboardButton(
                text=f"⚡ {key}: {reply[:30]}...",
                callback_data=f"send_quick:{key}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(text="✏️ Редактировать", callback_data="edit_quick_replies"),
        InlineKeyboardButton(text="« Назад", callback_data="main_menu")
    )
    
    return builder.as_markup()

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================
def save_message_history(user_id: int, message_text: str):
    """Сохранение истории сообщений"""
    if message_text is None:
        return
    
    if str(user_id) not in storage.data['message_history']:
        storage.data['message_history'][str(user_id)] = []
    
    history_entry = {
        'timestamp': datetime.now().isoformat(),
        'message': message_text[:500],  # Ограничиваем длину
        'user_id': user_id
    }
    
    storage.data['message_history'][str(user_id)].append(history_entry)
    
    # Ограничиваем историю последними 50 сообщениями
    if len(storage.data['message_history'][str(user_id)]) > 50:
        storage.data['message_history'][str(user_id)] = storage.data['message_history'][str(user_id)][-50:]
    
    storage.save_data()

def get_active_away_message() -> str:
    """Получение активного сообщения нерабочие"""
    for key, msg in storage.data['away_messages'].items():
        if msg['enabled']:
            return msg['text']
    
    # Если ничего не найдено, возвращаем дефолтное
    return storage.data['away_messages']['default']['text']

def is_within_working_hours() -> bool:
    """Проверка, находятся ли текущее время в рабочих часах"""
    hours = storage.data['working_hours']
    
    if not hours['enabled']:
        return True  # Если часы не настроены, всегда считаем рабочими
    
    try:
        current_time = datetime.now().time()
        start = datetime.strptime(hours['start'], '%H:%M').time()
        end = datetime.strptime(hours['end'], '%H:%M').time()
        
        return start <= current_time <= end
    except Exception as e:
        logger.error(f"Ошибка проверки рабочего времени: {e}")
        return True

async def notify_owner_about_message(message: Message):
    """Уведомление владельца о новом сообщении"""
    owner_id = storage.data['owner_id']
    
    user_info = f"👤 {message.from_user.full_name} (@{message.from_user.username or 'нет'})"
    message_preview = f"💬 {message.text[:100]}{'...' if len(message.text) > 100 else ''}" if message.text else "[Без текста]"
    
    notification = (
        f"📨 **Новое сообщение**\n\n"
        f"{user_info}\n"
        f"{message_preview}\n\n"
        f"ID: `{message.from_user.id}`\n"
        f"Чат: `{message.chat.id}`"
    )
    
    try:
        await bot.send_message(
            chat_id=owner_id,
            text=notification,
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Не удалось уведомить владельца: {e}")

async def handle_client_message(message: Message):
    """Обработка сообщений от клиентов (тех, кто пишет владельцу)"""
    
    # Проверяем, включен ли автоответ
    if not storage.data['auto_reply_enabled']:
        # Если автоответ выключен, уведомляем владельца
        if storage.data['settings']['notify_owner']:
            await notify_owner_about_message(message)
        return
    
    # Проверяем рабочие часы
    if not is_within_working_hours():
        offline_msg = storage.data['working_hours']['offline_message']
        if offline_msg:
            await message.answer(offline_msg)
        return
    
    # Небольшая задержка для реалистичности
    await asyncio.sleep(storage.data['settings']['reply_delay'])
    
    # Отправляем автоответ
    away_message = get_active_away_message()
    signature = storage.data['settings']['signature']
    
    full_message = away_message + signature
    
    await message.answer(full_message)
    
    # Уведомляем владельца
    if storage.data['settings']['notify_owner']:
        await notify_owner_about_message(message)

# ==================== ОБРАБОТЧИКИ КОМАНД ====================
@dp.message(Command("start"))
async def cmd_business_start(message: Message):
    """Стартовая команда для владельца"""
    if message.from_user.id == storage.data['owner_id']:
        await message.answer(
            "🤖 **Business Bot Mode - Панель управления**\n\n"
            "Этот бот будет отвечать на личные сообщения, которые приходят ВАМ, "
            "когда вы заняты или не в сети.\n\n"
            "⚡ **Функции:**\n"
            "• Автоответы в ваше отсутствие\n"
            "• Быстрые ответы одним кликом\n"
            "• Настройка рабочих часов\n"
            "• История сообщений\n\n"
            "**Как подключить к аккаунту:**\n"
            "1. Telegram → Настройки → Business → Business Bot\n"
            "2. Выберите этого бота (@вашбот)\n"
            "3. Настройте режим работы\n\n"
            "**Управление:**",
            reply_markup=get_business_main_menu(),
            parse_mode="Markdown"
        )
    else:
        # Если пишет не владелец - это клиент
        save_message_history(message.from_user.id, message.text)
        await handle_client_message(message)

@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Помощь для клиентов"""
    save_message_history(message.from_user.id, message.text)
    
    help_text = (
        "👋 Привет! Это автоответчик.\n\n"
        "Владелец сейчас не онлайн, но скоро ответит.\n\n"
        "📌 **Что можно сделать:**\n"
        "• Оставьте сообщение - вам ответят позже\n"
        "• Напишите срочный вопрос (я передам)\n"
        "• Узнайте контакты: /contacts\n"
        "• Часы работы: /hours\n\n"
        "Ваше сообщение сохранено!"
    )
    await message.answer(help_text)
    
    # Уведомляем владельца
    if storage.data['settings']['notify_owner']:
        await notify_owner_about_message(message)

@dp.message(Command("contacts"))
async def cmd_contacts(message: Message):
    """Контакты"""
    save_message_history(message.from_user.id, message.text)
    
    contacts = (
        "📞 **Контакты:**\n\n"
        "• Email: email@example.com\n"
        "• Телефон: +7 (XXX) XXX-XX-XX\n"
        "• Сайт: example.com\n\n"
        "Скоро с вами свяжутся!"
    )
    await message.answer(contacts)

@dp.message(Command("hours"))
async def cmd_hours(message: Message):
    """Часы работы"""
    save_message_history(message.from_user.id, message.text)
    
    hours = storage.data['working_hours']
    
    if hours['enabled']:
        text = f"🕐 **Часы работы:**\n\n{hours['start']} - {hours['end']}\n\n"
        if hours['offline_message']:
            text += f"_Вне рабочих часов:_ {hours['offline_message']}"
    else:
        text = "⏰ Часы работы не настроены"
    
    await message.answer(text)

# ==================== ОСНОВНОЙ ОБРАБОТЧИК СООБЩЕНИЙ ====================
@dp.message()
async def universal_message_handler(message: Message):
    """Обработчик ВСЕХ сообщений"""
    
    user_id = message.from_user.id
    
    # Сохраняем историю
    save_message_history(user_id, message.text)
    
    # Если сообщение от владельца
    if user_id == storage.data['owner_id']:
        await handle_owner_message(message)
    else:
        # Если сообщение от клиента (кто-то пишет владельцу)
        await handle_client_message(message)

async def handle_owner_message(message: Message):
    """Обработка сообщений от владельца"""
    text = message.text or ""
    
    # Команды управления через текст (альтернатива inline-кнопкам)
    if text.lower() == 'статус':
        status = "включен" if storage.data['auto_reply_enabled'] else "выключен"
        await message.answer(f"🤖 Business Bot Mode: {status}")
    
    elif text.lower() == 'оффлайн':
        # Быстрое включение автоответчика
        storage.data['auto_reply_enabled'] = True
        storage.save_data()
        await message.answer("✅ Автоответчик включен. Бот будет отвечать за вас.")
    
    elif text.lower() == 'онлайн':
        # Быстрое выключение
        storage.data['auto_reply_enabled'] = False
        storage.save_data()
        await message.answer("❌ Автоответчик выключен. Вы отвечаете сами.")
    
    elif text.lower() == 'меню':
        # Показать главное меню
        await message.answer(
            "🤖 **Business Bot Mode - Панель управления**",
            reply_markup=get_business_main_menu(),
            parse_mode="Markdown"
        )

# ==================== ОБРАБОТЧИКИ INLINE-КНОПОК ====================
@dp.callback_query(F.data == "toggle_business_mode")
async def toggle_business_mode(callback: CallbackQuery):
    """Включение/выключение Business Bot Mode"""
    storage.data['auto_reply_enabled'] = not storage.data['auto_reply_enabled']
    storage.save_data()
    
    status = "ВКЛЮЧЕН" if storage.data['auto_reply_enabled'] else "ВЫКЛЮЧЕН"
    await callback.message.edit_text(
        f"🤖 **Business Bot Mode: {status}**\n\n"
        f"Теперь бот будет {'отвечать на сообщения вместо вас' if storage.data['auto_reply_enabled'] else 'только уведомлять вас о новых сообщениях'}.",
        reply_markup=get_business_main_menu(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data == "menu_away_messages")
async def menu_away_messages(callback: CallbackQuery):
    """Меню сообщений нерабочие"""
    await callback.message.edit_text(
        "💬 **Сообщения нерабочие**\n\n"
        "Эти сообщения будут отправляться, когда вы не в сети.\n"
        "✅ - активно, ❌ - неактивно\n",
        reply_markup=get_away_messages_menu(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data == "menu_quick_replies")
async def menu_quick_replies(callback: CallbackQuery):
    """Меню быстрых ответов"""
    await callback.message.edit_text(
        "⚡ **Быстрые ответы**\n\n"
        "Нажмите на ответ, чтобы отправить его клиенту:\n",
        reply_markup=get_quick_replies_menu(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data == "main_menu")
async def main_menu_handler(callback: CallbackQuery):
    """Главное меню"""
    await callback.message.edit_text(
        "🤖 **Business Bot Mode - Панель управления**",
        reply_markup=get_business_main_menu(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("send_quick:"))
async def send_quick_reply(callback: CallbackQuery):
    """Отправка быстрого ответа"""
    reply_key = callback.data.split(":")[1]
    reply_text = storage.data['quick_replies'].get(reply_key)
    
    if reply_text:
        # Здесь должна быть логика отправки клиенту
        # Пока просто покажем пример
        await callback.answer(f"Быстрый ответ: {reply_text[:30]}...", show_alert=True)
    else:
        await callback.answer("❌ Ответ не найден", show_alert=True)

# ==================== ЗАПУСК БОТА ====================
async def main():
    print("🤖 Business Bot запускается...")
    print(f"• Владелец: {storage.data['owner_id']}")
    print(f"• Автоответы: {'ВКЛ' if storage.data['auto_reply_enabled'] else 'ВЫКЛ'}")
    print(f"• Сообщений в истории: {sum(len(v) for v in storage.data['message_history'].values())}")
    print("\n📌 Инструкция по подключению:")
    print("1. Откройте Telegram → Настройки → Business → Business Bot")
    print("2. Выберите этого бота")
    print("3. Настройте в этом меню сообщения")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
