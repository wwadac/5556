import asyncio
import random
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import telebot
from telebot import types
from telebot.types import BusinessMessagesDeleted, BusinessConnection
from telebot.async_telebot import AsyncTeleBot
from telebot.asyncio_storage import StateMemoryStorage

# Конфигурация
BOT_TOKEN = "8556723456:AAFw-r-WKOC4A1kNw9ovHBdVF0Cd08Fbk7E"  # Замени на токен бота
OWNER_ID = 8593061718  # Твой ID в Telegram
CONFIG_FILE = "business_bot_config.json"

# Инициализация бота с асинхронным режимом
storage = StateMemoryStorage()
bot = AsyncTeleBot(BOT_TOKEN, state_storage=storage)

# Структуры данных
MESSAGES = {}
user_configs: Dict[int, Dict] = {}
business_connections: Dict[str, BusinessConnection] = {}

# Загрузка конфигурации
def load_config():
    global user_configs
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Конвертируем ключи из строк в int
                user_configs = {int(k): v for k, v in data.items()}
                print(f"Загружено {len(user_configs)} конфигураций")
        except Exception as e:
            print(f"Ошибка загрузки конфигурации: {e}")
            user_configs = {}
    else:
        user_configs = {}

# Сохранение конфигурации
def save_config():
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(user_configs, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Ошибка сохранения конфигурации: {e}")

# Инициализация конфигурации пользователя
def init_user_config(user_id: int):
    if user_id not in user_configs:
        user_configs[user_id] = {
            "auto_responses": {
                "привет": {"text": "Привет! 👋", "sticker_id": None},
                "приветик": {"text": "Приветик! 😊", "sticker_id": None},
                "здравствуйте": {"text": "Здравствуйте! 🤝", "sticker_id": None}
            },
            "follow_up_messages": {
                "default": {"text": "Как ваши дела?", "delay": 30}
            },
            "settings": {
                "typing_delay": 2,
                "read_delay": 3,
                "min_follow_up_delay": 20,
                "max_follow_up_delay": 60,
                "enabled": True
            },
            "current_action": None,
            "business_connection_id": None
        }
        save_config()
    return user_configs[user_id]

# Вспомогательные функции
def chat_name(chat):
    return chat.title or f"{chat.first_name or ''} {chat.last_name or ''}".strip()

def base_record(msg):
    return {
        "from_user": msg.from_user.first_name,
        "from_user_id": msg.from_user.id,
        "type": msg.content_type,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }

# Создание главного меню
def create_main_menu():
    keyboard = types.InlineKeyboardMarkup()
    
    # Первый ряд
    keyboard.row(
        types.InlineKeyboardButton("📝 Настроить автоответы", callback_data="setup_auto"),
        types.InlineKeyboardButton("⏰ Настроить отложенные", callback_data="setup_followup")
    )
    
    # Второй ряд
    keyboard.row(
        types.InlineKeyboardButton("⚙️ Настройки бота", callback_data="bot_settings"),
        types.InlineKeyboardButton("📊 Статус", callback_data="status")
    )
    
    # Третий ряд
    keyboard.row(
        types.InlineKeyboardButton("🔌 Подключения", callback_data="connections"),
        types.InlineKeyboardButton("❓ Помощь", callback_data="help")
    )
    
    # Четвертый ряд
    keyboard.row(
        types.InlineKeyboardButton("🔄 Вкл/Выкл бота", callback_data="toggle_bot"),
        types.InlineKeyboardButton("🗑️ Очистить настройки", callback_data="clear_config")
    )
    
    return keyboard

# Создание меню автоответов
def create_auto_responses_menu(user_id):
    config = init_user_config(user_id)
    keyboard = types.InlineKeyboardMarkup()
    
    for trigger, response in config["auto_responses"].items():
        sticker_info = "➕ стикер" if response["sticker_id"] else "❌ без стикера"
        btn_text = f"✏️ '{trigger}' → '{response['text'][:10]}...' {sticker_info}"
        keyboard.row(types.InlineKeyboardButton(
            btn_text, 
            callback_data=f"edit_auto_{trigger}"
        ))
    
    keyboard.row(
        types.InlineKeyboardButton("➕ Добавить автоответ", callback_data="add_auto"),
        types.InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")
    )
    
    return keyboard

# Создание меню настроек
def create_settings_menu(user_id):
    config = init_user_config(user_id)
    settings = config["settings"]
    
    keyboard = types.InlineKeyboardMarkup()
    
    keyboard.row(
        types.InlineKeyboardButton(f"⌨️ Задержка печати: {settings['typing_delay']}с", 
                                 callback_data="set_typing_delay"),
        types.InlineKeyboardButton(f"👁️ Задержка чтения: {settings['read_delay']}с", 
                                 callback_data="set_read_delay")
    )
    
    keyboard.row(
        types.InlineKeyboardButton(f"⏱️ Мин. пауза: {settings['min_follow_up_delay']}с", 
                                 callback_data="set_min_delay"),
        types.InlineKeyboardButton(f"⏱️ Макс. пауза: {settings['max_follow_up_delay']}с", 
                                 callback_data="set_max_delay")
    )
    
    status = "✅ ВКЛ" if settings["enabled"] else "❌ ВЫКЛ"
    keyboard.row(
        types.InlineKeyboardButton(f"Статус бота: {status}", callback_data="toggle_bot"),
        types.InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")
    )
    
    return keyboard

# Обработчики бизнес-сообщений
@bot.business_message_handler(content_types=["text"])
async def on_business_message(msg: types.Message):
    try:
        user_id = msg.from_user.id
        config = init_user_config(user_id)
        
        # Проверяем, включен ли бот
        if not config["settings"]["enabled"]:
            return
        
        # Ищем триггер в сообщении
        text_lower = msg.text.lower().strip()
        
        for trigger, response in config["auto_responses"].items():
            if trigger in text_lower:
                # Удаляем оригинальное сообщение
                try:
                    await bot.delete_message(msg.chat.id, msg.message_id)
                except:
                    pass
                
                # Имитируем "печатает"
                await bot.send_chat_action(msg.chat.id, "typing")
                await asyncio.sleep(config["settings"]["typing_delay"])
                
                # Отправляем текст
                await bot.send_message(
                    msg.chat.id,
                    response["text"],
                    reply_to_message_id=msg.message_id - 1 if msg.message_id > 1 else None
                )
                
                # Отправляем стикер если есть
                if response["sticker_id"]:
                    await bot.send_sticker(msg.chat.id, response["sticker_id"])
                
                # Имитируем "прочитано" через задержку
                await asyncio.sleep(config["settings"]["read_delay"])
                # В реальном API бота нет метода "прочитано", но можно использовать действия
                await bot.send_chat_action(msg.chat.id, "choose_sticker")
                
                # Сохраняем информацию о чате для follow-up
                config["last_chat_id"] = msg.chat.id
                config["last_user_id"] = msg.from_user.id
                save_config()
                
                break
                
    except Exception as e:
        print(f"Ошибка в on_business_message: {e}")

# Обработчик ответов пользователя
@bot.edited_business_message_handler(content_types=["text"])
@bot.business_message_handler(func=lambda m: m.reply_to_message is not None)
async def on_user_reply(msg: types.Message):
    try:
        user_id = msg.from_user.id
        config = init_user_config(user_id)
        
        # Проверяем, включен ли бот
        if not config["settings"]["enabled"]:
            return
        
        # Если это ответ на наше сообщение
        if hasattr(msg.reply_to_message, 'from_user') and msg.reply_to_message.from_user.id == msg.bot.id:
            # Генерируем случайную задержку
            min_delay = config["settings"]["min_follow_up_delay"]
            max_delay = config["settings"]["max_follow_up_delay"]
            delay = random.randint(min_delay, max_delay)
            
            # Ждем
            await asyncio.sleep(delay)
            
            # Имитируем "печатает"
            await bot.send_chat_action(msg.chat.id, "typing")
            await asyncio.sleep(config["settings"]["typing_delay"])
            
            # Отправляем follow-up сообщение
            follow_up = config["follow_up_messages"].get("default", 
                {"text": "Как ваши дела?", "delay": 30})
            
            await bot.send_message(
                msg.chat.id,
                follow_up["text"],
                reply_to_message_id=msg.message_id
            )
            
            # Имитируем "прочитано"
            await asyncio.sleep(config["settings"]["read_delay"])
            await bot.send_chat_action(msg.chat.id, "choose_sticker")
            
    except Exception as e:
        print(f"Ошибка в on_user_reply: {e}")

# Обработчик callback-запросов
@bot.callback_query_handler(func=lambda call: True)
async def handle_callback(call: types.CallbackQuery):
    user_id = call.from_user.id
    config = init_user_config(user_id)
    
    try:
        if call.data == "main_menu":
            await bot.edit_message_text(
                "🏠 *Главное меню бизнес-бота*\n\nВыберите действие:",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=create_main_menu(),
                parse_mode="Markdown"
            )
        
        elif call.data == "setup_auto":
            await bot.edit_message_text(
                "📝 *Настройка автоответов*\n\nВыберите триггер для редактирования:",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=create_auto_responses_menu(user_id),
                parse_mode="Markdown"
            )
        
        elif call.data.startswith("edit_auto_"):
            trigger = call.data.replace("edit_auto_", "")
            response = config["auto_responses"].get(trigger, {"text": "", "sticker_id": None})
            
            keyboard = types.InlineKeyboardMarkup()
            keyboard.row(
                types.InlineKeyboardButton("✏️ Изменить текст", callback_data=f"change_text_{trigger}"),
                types.InlineKeyboardButton("🖼️ Изменить стикер", callback_data=f"change_sticker_{trigger}")
            )
            keyboard.row(
                types.InlineKeyboardButton("🗑️ Удалить", callback_data=f"delete_auto_{trigger}"),
                types.InlineKeyboardButton("⬅️ Назад", callback_data="setup_auto")
            )
            
            sticker_info = f"Стикер: {'✅ установлен' if response['sticker_id'] else '❌ не установлен'}"
            await bot.edit_message_text(
                f"✏️ *Редактирование автоответа*\n\n"
                f"Триггер: `{trigger}`\n"
                f"Текст: {response['text']}\n"
                f"{sticker_info}\n\n"
                f"Выберите действие:",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        
        elif call.data.startswith("change_text_"):
            trigger = call.data.replace("change_text_", "")
            config["current_action"] = f"set_text_{trigger}"
            save_config()
            
            await bot.edit_message_text(
                f"✍️ *Введите новый текст для триггера '{trigger}':*",
                call.message.chat.id,
                call.message.message_id,
                parse_mode="Markdown"
            )
        
        elif call.data.startswith("change_sticker_"):
            trigger = call.data.replace("change_sticker_", "")
            config["current_action"] = f"set_sticker_{trigger}"
            save_config()
            
            await bot.edit_message_text(
                f"🖼️ *Отправьте стикер для триггера '{trigger}':*\n\n"
                f"Просто отправьте любой стикер в этот чат.",
                call.message.chat.id,
                call.message.message_id,
                parse_mode="Markdown"
            )
        
        elif call.data == "add_auto":
            config["current_action"] = "add_auto_trigger"
            save_config()
            
            await bot.edit_message_text(
                "➕ *Добавление нового автоответа*\n\n"
                "Введите *триггер* (слово или фразу, на которое бот будет реагировать):\n"
                "Например: `привет` или `здравствуйте`",
                call.message.chat.id,
                call.message.message_id,
                parse_mode="Markdown"
            )
        
        elif call.data == "bot_settings":
            settings = config["settings"]
            status = "✅ ВКЛЮЧЕН" if settings["enabled"] else "❌ ВЫКЛЮЧЕН"
            
            text = (
                f"⚙️ *Настройки бота*\n\n"
                f"• Статус: {status}\n"
                f"• Задержка печати: {settings['typing_delay']} сек\n"
                f"• Задержка чтения: {settings['read_delay']} сек\n"
                f"• Мин. пауза ответа: {settings['min_follow_up_delay']} сек\n"
                f"• Макс. пауза ответа: {settings['max_follow_up_delay']} сек\n\n"
                f"Выберите параметр для изменения:"
            )
            
            await bot.edit_message_text(
                text,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=create_settings_menu(user_id),
                parse_mode="Markdown"
            )
        
        elif call.data == "toggle_bot":
            config["settings"]["enabled"] = not config["settings"]["enabled"]
            save_config()
            
            status = "✅ ВКЛЮЧЕН" if config["settings"]["enabled"] else "❌ ВЫКЛЮЧЕН"
            await bot.answer_callback_query(call.id, f"Бот {status.lower()}")
            await handle_callback(types.CallbackQuery(
                id=call.id,
                from_user=call.from_user,
                data="bot_settings",
                message=call.message
            ))
        
        elif call.data == "status":
            auto_count = len(config["auto_responses"])
            settings = config["settings"]
            connections_count = len([c for c in business_connections.values() if c.user.id == user_id])
            
            text = (
                f"📊 *Статус бизнес-бота*\n\n"
                f"• Автоответов настроено: {auto_count}\n"
                f"• Бизнес-подключений: {connections_count}\n"
                f"• Статус: {'🟢 АКТИВЕН' if settings['enabled'] else '🔴 ВЫКЛЮЧЕН'}\n"
                f"• Задержка печати: {settings['typing_delay']} сек\n"
                f"• Задержка чтения: {settings['read_delay']} сек\n\n"
                f"*Текущие триггеры:*\n"
            )
            
            for trigger, response in config["auto_responses"].items():
                text += f"• `{trigger}` → {response['text'][:20]}...\n"
            
            keyboard = types.InlineKeyboardMarkup()
            keyboard.row(
                types.InlineKeyboardButton("🔄 Обновить", callback_data="status"),
                types.InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")
            )
            
            await bot.edit_message_text(
                text,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        
        elif call.data == "help":
            text = (
                "❓ *Помощь по бизнес-боту*\n\n"
                "🤖 *Как работает бот:*\n"
                "1. Подключите бота через Telegram Business\n"
                "2. Настройте автоответы и задержки\n"
                "3. Когда вы пишете слово-триггер, бот автоматически заменяет его\n"
                "4. После ответа собеседника бот отправляет follow-up сообщение\n\n"
                "⚙️ *Основные функции:*\n"
                "• Автозамена сообщений с триггерами\n"
                "• Автоматические follow-up сообщения\n"
                "• Настраиваемые задержки\n"
                "• Имитация печати и чтения\n"
                "• Управление через инлайн-кнопки\n\n"
                "📱 *Требования:*\n"
                "• Telegram Premium\n"
                "• Telegram Business\n"
                "• Подключение бота через Business Connections"
            )
            
            keyboard = types.InlineKeyboardMarkup()
            keyboard.row(types.InlineKeyboardButton("⬅️ Назад", callback_data="main_menu"))
            
            await bot.edit_message_text(
                text,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        
        elif call.data == "connections":
            user_connections = [c for c in business_connections.values() if c.user.id == user_id]
            
            if user_connections:
                text = "🔌 *Ваши бизнес-подключения:*\n\n"
                for conn in user_connections:
                    text += f"• ID: `{conn.id}`\n"
                    text += f"  Пользователь: {conn.user.first_name}\n"
                    text += f"  Дата: {conn.date}\n\n"
            else:
                text = "🔌 *Бизнес-подключения*\n\nУ вас нет активных бизнес-подключений."
            
            keyboard = types.InlineKeyboardMarkup()
            keyboard.row(types.InlineKeyboardButton("⬅️ Назад", callback_data="main_menu"))
            
            await bot.edit_message_text(
                text,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        
        elif call.data == "clear_config":
            keyboard = types.InlineKeyboardMarkup()
            keyboard.row(
                types.InlineKeyboardButton("✅ Да, очистить", callback_data="confirm_clear"),
                types.InlineKeyboardButton("❌ Нет, отмена", callback_data="main_menu")
            )
            
            await bot.edit_message_text(
                "⚠️ *Внимание!*\n\n"
                "Вы уверены, что хотите очистить ВСЕ настройки бота?\n"
                "Это действие нельзя отменить!",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        
        elif call.data == "confirm_clear":
            user_configs[user_id] = {}
            init_user_config(user_id)  # Создаем новую конфигурацию
            save_config()
            
            await bot.edit_message_text(
                "✅ *Настройки очищены!*\n\n"
                "Все настройки сброшены до значений по умолчанию.",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=create_main_menu(),
                parse_mode="Markdown"
            )
        
        elif call.data in ["set_typing_delay", "set_read_delay", "set_min_delay", "set_max_delay"]:
            param_map = {
                "set_typing_delay": ("typing_delay", "задержки печати"),
                "set_read_delay": ("read_delay", "задержки чтения"),
                "set_min_delay": ("min_follow_up_delay", "минимальной паузы"),
                "set_max_delay": ("max_follow_up_delay", "максимальной паузы")
            }
            
            param, name = param_map[call.data]
            config["current_action"] = f"set_{param}"
            save_config()
            
            await bot.edit_message_text(
                f"⏱️ *Настройка {name}*\n\n"
                f"Введите новое значение в секундах (от 1 до 60):",
                call.message.chat.id,
                call.message.message_id,
                parse_mode="Markdown"
            )
        
        await bot.answer_callback_query(call.id)
        
    except Exception as e:
        print(f"Ошибка в handle_callback: {e}")
        await bot.answer_callback_query(call.id, "⚠️ Произошла ошибка")

# Обработчик текстовых сообщений для настройки
@bot.message_handler(func=lambda m: m.chat.type == "private" and m.content_type == "text")
async def handle_text_message(msg: types.Message):
    user_id = msg.from_user.id
    config = init_user_config(user_id)
    
    if config.get("current_action"):
        action = config["current_action"]
        
        if action.startswith("set_text_"):
            trigger = action.replace("set_text_", "")
            config["auto_responses"][trigger]["text"] = msg.text
            config["current_action"] = None
            save_config()
            
            await bot.send_message(
                msg.chat.id,
                f"✅ Текст для триггера `{trigger}` обновлен!",
                parse_mode="Markdown",
                reply_markup=types.InlineKeyboardMarkup().add(
                    types.InlineKeyboardButton("⬅️ Назад к меню", callback_data="setup_auto")
                )
            )
        
        elif action.startswith("set_sticker_"):
            # Для стикеров нужно использовать отдельный обработчик
            pass
        
        elif action == "add_auto_trigger":
            trigger = msg.text.lower().strip()
            if trigger not in config["auto_responses"]:
                config["auto_responses"][trigger] = {"text": "Привет!", "sticker_id": None}
                config["current_action"] = f"set_text_{trigger}"
                save_config()
                
                await bot.send_message(
                    msg.chat.id,
                    f"✅ Триггер `{trigger}` добавлен!\n\n"
                    f"Теперь введите текст ответа:",
                    parse_mode="Markdown"
                )
            else:
                await bot.send_message(
                    msg.chat.id,
                    f"⚠️ Триггер `{trigger}` уже существует!",
                    parse_mode="Markdown"
                )
        
        elif action.startswith("set_"):
            param_map = {
                "set_typing_delay": "typing_delay",
                "set_read_delay": "read_delay",
                "set_min_follow_up_delay": "min_follow_up_delay",
                "set_max_follow_up_delay": "max_follow_up_delay"
            }
            
            param = param_map.get(action)
            if param:
                try:
                    value = int(msg.text)
                    if 1 <= value <= 60:
                        config["settings"][param] = value
                        config["current_action"] = None
                        save_config()
                        
                        await bot.send_message(
                            msg.chat.id,
                            f"✅ Параметр `{param}` установлен на {value} секунд!",
                            parse_mode="Markdown",
                            reply_markup=types.InlineKeyboardMarkup().add(
                                types.InlineKeyboardButton("⬅️ Назад к настройкам", callback_data="bot_settings")
                            )
                        )
                    else:
                        await bot.send_message(
                            msg.chat.id,
                            "⚠️ Введите число от 1 до 60!"
                        )
                except ValueError:
                    await bot.send_message(
                        msg.chat.id,
                        "⚠️ Введите корректное число!"
                    )
    
    else:
        # Если нет активного действия, показываем главное меню
        await bot.send_message(
            msg.chat.id,
            "🤖 *Добро пожаловать в Business Bot!*\n\n"
            "Этот бот поможет автоматизировать ваши бизнес-переписки в Telegram.\n\n"
            "🔹 *Как начать:*\n"
            "1. Убедитесь, что у вас есть Telegram Premium\n"
            "2. Подключите бота через Telegram Business\n"
            "3. Настройте автоответы ниже\n\n"
            "📱 *Основные возможности:*\n"
            "• Автозамена сообщений по триггерам\n"
            "• Автоматические follow-up сообщения\n"
            "• Настраиваемые задержки\n"
            "• Имитация печати и чтения\n",
            reply_markup=create_main_menu(),
            parse_mode="Markdown"
        )

# Обработчик стикеров для настройки
@bot.message_handler(content_types=["sticker"])
async def handle_sticker(msg: types.Message):
    user_id = msg.from_user.id
    config = init_user_config(user_id)
    
    if config.get("current_action") and config["current_action"].startswith("set_sticker_"):
        trigger = config["current_action"].replace("set_sticker_", "")
        config["auto_responses"][trigger]["sticker_id"] = msg.sticker.file_id
        config["current_action"] = None
        save_config()
        
        await bot.send_message(
            msg.chat.id,
            f"✅ Стикер для триггера `{trigger}` установлен!",
            parse_mode="Markdown",
            reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton("⬅️ Назад к меню", callback_data="setup_auto")
            )
        )

# Обработчик бизнес-подключений
@bot.business_connection_handler()
async def on_business_connection(business_connection: BusinessConnection):
    business_connections[business_connection.id] = business_connection
    user_id = business_connection.user.id
    
    await bot.send_message(
        user_id,
        f"✅ *Новое бизнес-подключение!*\n\n"
        f"Бот подключен к чату с {business_connection.user.first_name}\n"
        f"ID подключения: `{business_connection.id}`\n\n"
        f"Теперь бот будет обрабатывать сообщения в этом чате.",
        parse_mode="Markdown"
    )

# Команда /start
@bot.message_handler(commands=['start'])
async def start_command(msg: types.Message):
    await bot.send_message(
        msg.chat.id,
        "🚀 *Business Bot активирован!*\n\n"
        "Для работы с ботом:\n"
        "1. Перейдите в настройки Telegram Business\n"
        "2. Подключите этого бота\n"
        "3. Настройте автоответы через меню ниже\n\n"
        "📌 *Важно:* Требуется Telegram Premium и Telegram Business!",
        reply_markup=create_main_menu(),
        parse_mode="Markdown"
    )

# Команда /setup
@bot.message_handler(commands=['setup'])
async def setup_command(msg: types.Message):
    await handle_callback(types.CallbackQuery(
        id="setup",
        from_user=msg.from_user,
        data="main_menu",
        message=msg
    ))

# Запуск бота
async def main():
    # Загружаем конфигурацию
    load_config()
    
    print("🤖 Business Bot запущен!")
    print("✨ Особенности:")
    print("• Автозамена сообщений по триггерам")
    print("• Автоматические follow-up ответы")
    print("• Настраиваемые задержки")
    print("• Имитация печати и чтения")
    print("• Управление через инлайн-кнопки")
    print("\nДля подключения:")
    print("1. Установите Telegram Premium")
    print("2. Включите Telegram Business")
    print("3. Подключите этого бота в настройках Business")
    
    await bot.polling(none_stop=True)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
