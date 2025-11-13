import asyncio
import random
import pandas as pd
import json
import sqlite3
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, 
    ContextTypes, MessageHandler, filters
)
import logging

# Настройки
BOT_TOKEN = "8324933170:AAFatQ1T42ZJ70oeWS2UJkcXFeiwUFCIXAk"
EXCEL_FILE = "development(500).xlsx"

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class AdminUserBot:
    def __init__(self):
        self.users_data = self.load_users_data()
        self.settings = self.load_settings()
        self.setup_database()
        
    def setup_database(self):
        """Настраивает базу данных для хранения настроек"""
        conn = sqlite3.connect('bot_settings.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        conn.commit()
        conn.close()
        
    def save_setting(self, key, value):
        """Сохраняет настройку в базу данных"""
        conn = sqlite3.connect('bot_settings.db')
        cursor = conn.cursor()
        cursor.execute(
            'INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)',
            (key, value)
        )
        conn.commit()
        conn.close()
        
    def load_setting(self, key, default=None):
        """Загружает настройку из базы данных"""
        conn = sqlite3.connect('bot_settings.db')
        cursor = conn.cursor()
        cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else default
        
    def load_users_data(self):
        """Загружает данные пользователей из Excel файла"""
        try:
            df = pd.read_excel(EXCEL_FILE)
            logger.info(f"Загружено {len(df)} пользователей из Excel")
            return df.to_dict('records')
        except Exception as e:
            logger.error(f"Ошибка загрузки Excel: {e}")
            return []
    
    def load_settings(self):
        """Загружает настройки"""
        return {
            'channel': self.load_setting('channel', ''),
            'interval': int(self.load_setting('interval', '3600')),
            'is_active': self.load_setting('is_active', 'False') == 'True',
            'admin_ids': json.loads(self.load_setting('admin_ids', '[]')),
            'last_sent_index': int(self.load_setting('last_sent_index', '0'))
        }
    
    def save_settings(self):
        """Сохраняет все настройки"""
        for key, value in self.settings.items():
            if key == 'admin_ids':
                self.save_setting(key, json.dumps(value))
            else:
                self.save_setting(key, str(value))
    
    def is_admin(self, user_id):
        """Проверяет, является ли пользователь администратором"""
        return user_id in self.settings['admin_ids']
    
    def add_admin(self, user_id):
        """Добавляет администратора"""
        if user_id not in self.settings['admin_ids']:
            self.settings['admin_ids'].append(user_id)
            self.save_settings()
    
    def remove_admin(self, user_id):
        """Удаляет администратора"""
        if user_id in self.settings['admin_ids']:
            self.settings['admin_ids'].remove(user_id)
            self.save_settings()
    
    def get_random_user(self):
        """Возвращает случайного пользователя из данных"""
        if not self.users_data:
            return None
        return random.choice(self.users_data)
    
    def get_next_user(self):
        """Возвращает следующего пользователя по порядку"""
        if not self.users_data:
            return None
        
        user = self.users_data[self.settings['last_sent_index']]
        self.settings['last_sent_index'] = (self.settings['last_sent_index'] + 1) % len(self.users_data)
        self.save_settings()
        return user
    
    def format_user_message(self, user_data):
        """Форматирует сообщение о пользователе"""
        username = user_data.get('A', 'N/A').split('/')[-1] if user_data.get('A') else 'N/A'
        name = user_data.get('B', 'N/A')
        description = user_data.get('C', 'N/A')
        gender = user_data.get('E', 'N/A')
        
        message = f"👤 **Новый пользователь**\n\n"
        message += f"🔗 **Username:** @{username}\n"
        message += f"📛 **Имя:** {name}\n"
        message += f"📝 **Описание:** {description[:100]}...\n" if len(str(description)) > 100 else f"📝 **Описание:** {description}\n"
        message += f"⚧ **Пол:** {gender}\n"
        message += f"🔗 **Профиль:** {user_data.get('A', 'N/A')}\n\n"
        message += f"#пользователь #{username.replace('_', '')}"
        
        return message

# Создаем экземпляр бота
bot = AdminUserBot()

# ===== КЛАВИАТУРЫ =====
def get_admin_keyboard():
    """Клавиатура админ-панели"""
    keyboard = [
        [InlineKeyboardButton("⚙️ Настройки канала", callback_data="channel_settings")],
        [InlineKeyboardButton("⏰ Настройки времени", callback_data="time_settings")],
        [InlineKeyboardButton("🔧 Управление рассылкой", callback_data="mailing_control")],
        [InlineKeyboardButton("👥 Управление админами", callback_data="admin_management")],
        [InlineKeyboardButton("📊 Статистика", callback_data="statistics")],
        [InlineKeyboardButton("👤 Тестовый пользователь", callback_data="test_user")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_settings_keyboard():
    """Клавиатура настроек"""
    status = "✅ ВКЛ" if bot.settings['is_active'] else "❌ ВЫКЛ"
    keyboard = [
        [InlineKeyboardButton(f"🔄 Авто-отправка: {status}", callback_data="toggle_auto")],
        [InlineKeyboardButton("📝 Изменить канал", callback_data="change_channel")],
        [InlineKeyboardButton("⏱ Изменить интервал", callback_data="change_interval")],
        [InlineKeyboardButton("◀️ Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_time_keyboard():
    """Клавиатура настроек времени"""
    intervals = {
        "15 минут": 900,
        "30 минут": 1800,
        "1 час": 3600,
        "3 часа": 10800,
        "6 часов": 21600,
        "12 часов": 43200,
        "24 часа": 86400
    }
    
    keyboard = []
    for text, seconds in intervals.items():
        keyboard.append([InlineKeyboardButton(text, callback_data=f"interval_{seconds}")])
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="back_to_settings")])
    
    return InlineKeyboardMarkup(keyboard)

def get_admin_management_keyboard():
    """Клавиатура управления админами"""
    keyboard = [
        [InlineKeyboardButton("➕ Добавить админа", callback_data="add_admin")],
        [InlineKeyboardButton("➖ Удалить админа", callback_data="remove_admin")],
        [InlineKeyboardButton("📋 Список админов", callback_data="list_admins")],
        [InlineKeyboardButton("◀️ Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ===== ОБРАБОТЧИКИ КОМАНД =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user_id = update.effective_user.id
    
    if bot.is_admin(user_id):
        await update.message.reply_text(
            "🛠 **Админ-панель управления ботом**\n\n"
            "Выберите действие:",
            reply_markup=get_admin_keyboard()
        )
    else:
        await update.message.reply_text(
            "❌ У вас нет доступа к админ-панели.\n"
            "Обратитесь к администратору."
        )

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для открытия админ-панели"""
    user_id = update.effective_user.id
    
    if bot.is_admin(user_id):
        await update.message.reply_text(
            "🛠 **Админ-панель управления ботом**\n\n"
            "Выберите действие:",
            reply_markup=get_admin_keyboard()
        )
    else:
        await update.message.reply_text("❌ У вас нет доступа к админ-панели.")

# ===== ОБРАБОТЧИКИ CALLBACK =====
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not bot.is_admin(user_id):
        await query.edit_message_text("❌ У вас нет доступа к админ-панели.")
        return
    
    data = query.data
    
    if data == "channel_settings":
        await show_channel_settings(query)
    elif data == "time_settings":
        await show_time_settings(query)
    elif data == "mailing_control":
        await show_mailing_control(query)
    elif data == "admin_management":
        await show_admin_management(query)
    elif data == "statistics":
        await show_statistics(query)
    elif data == "test_user":
        await send_test_user(query)
    elif data == "back_to_main":
        await query.edit_message_text(
            "🛠 **Админ-панель управления ботом**\n\nВыберите действие:",
            reply_markup=get_admin_keyboard()
        )
    elif data == "back_to_settings":
        await show_channel_settings(query)
    elif data.startswith("interval_"):
        await set_interval(query, data)
    elif data == "toggle_auto":
        await toggle_auto_sending(query)
    elif data == "change_channel":
        await query.edit_message_text(
            "📝 Отправьте username канала (например: @my_channel):"
        )
        context.user_data['waiting_for_channel'] = True
    elif data == "change_interval":
        await query.edit_message_text(
            "⏰ Выберите интервал отправки:",
            reply_markup=get_time_keyboard()
        )
    elif data == "add_admin":
        await query.edit_message_text(
            "➕ Отправьте ID пользователя для добавления в админы:"
        )
        context.user_data['waiting_for_admin_add'] = True
    elif data == "remove_admin":
        await query.edit_message_text(
            "➖ Отправьте ID пользователя для удаления из админов:"
        )
        context.user_data['waiting_for_admin_remove'] = True
    elif data == "list_admins":
        await show_admin_list(query)

async def show_channel_settings(query):
    """Показывает настройки канала"""
    channel = bot.settings['channel'] or "Не установлен"
    interval = bot.settings['interval']
    status = "✅ Активна" if bot.settings['is_active'] else "❌ Остановлена"
    
    # Конвертируем интервал в читаемый формат
    if interval < 60:
        interval_text = f"{interval} сек"
    elif interval < 3600:
        interval_text = f"{interval // 60} мин"
    else:
        interval_text = f"{interval // 3600} час"
    
    message = (
        "⚙️ **Настройки рассылки**\n\n"
        f"📢 **Канал:** {channel}\n"
        f"⏰ **Интервал:** {interval_text}\n"
        f"🔄 **Статус:** {status}\n\n"
        "Выберите действие:"
    )
    
    await query.edit_message_text(message, reply_markup=get_settings_keyboard())

async def show_time_settings(query):
    """Показывает настройки времени"""
    await query.edit_message_text(
        "⏰ **Настройки интервала отправки**\n\n"
        "Выберите интервал:",
        reply_markup=get_time_keyboard()
    )

async def show_mailing_control(query):
    """Показывает управление рассылкой"""
    keyboard = [
        [InlineKeyboardButton("▶️ Запустить рассылку", callback_data="start_mailing")],
        [InlineKeyboardButton("⏹ Остановить рассылку", callback_data="stop_mailing")],
        [InlineKeyboardButton("🔁 Отправить сейчас", callback_data="send_now")],
        [InlineKeyboardButton("◀️ Назад", callback_data="back_to_main")]
    ]
    
    await query.edit_message_text(
        "🔧 **Управление рассылкой**\n\n"
        "Запустите или остановите автоматическую отправку:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_admin_management(query):
    """Показывает управление админами"""
    await query.edit_message_text(
        "👥 **Управление администраторами**\n\n"
        "Выберите действие:",
        reply_markup=get_admin_management_keyboard()
    )

async def show_statistics(query):
    """Показывает статистику"""
    total_users = len(bot.users_data)
    sent_users = bot.settings['last_sent_index']
    remaining = total_users - sent_users
    
    message = (
        "📊 **Статистика бота**\n\n"
        f"👥 Всего пользователей: {total_users}\n"
        f"📤 Отправлено: {sent_users}\n"
        f"📋 Осталось: {remaining}\n"
        f"🔄 Прогресс: {sent_users/total_users*100:.1f}%\n\n"
        f"📢 Канал: {bot.settings['channel'] or 'Не установлен'}\n"
        f"⏰ Интервал: {bot.settings['interval']} сек\n"
        f"🔄 Авто-отправка: {'✅ ВКЛ' if bot.settings['is_active'] else '❌ ВЫКЛ'}"
    )
    
    keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="back_to_main")]]
    await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))

async def send_test_user(query):
    """Отправляет тестового пользователя"""
    user_data = bot.get_random_user()
    if user_data:
        message = bot.format_user_message(user_data)
        try:
            await query.message.reply_text(message, parse_mode='Markdown')
            await query.edit_message_text("✅ Тестовый пользователь отправлен!")
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка отправки: {e}")
    else:
        await query.edit_message_text("❌ Нет данных пользователей")

async def set_interval(query, data):
    """Устанавливает интервал отправки"""
    seconds = int(data.split('_')[1])
    bot.settings['interval'] = seconds
    bot.save_settings()
    
    await query.edit_message_text(
        f"✅ Интервал установлен: {seconds} секунд",
        reply_markup=get_settings_keyboard()
    )

async def toggle_auto_sending(query):
    """Включает/выключает авто-отправку"""
    bot.settings['is_active'] = not bot.settings['is_active']
    bot.save_settings()
    
    status = "включена" if bot.settings['is_active'] else "выключена"
    await query.edit_message_text(
        f"✅ Авто-отправка {status}",
        reply_markup=get_settings_keyboard()
    )

async def show_admin_list(query):
    """Показывает список админов"""
    admins = bot.settings['admin_ids']
    if not admins:
        message = "📋 Список администраторов пуст"
    else:
        message = "📋 **Список администраторов:**\n\n" + "\n".join([f"🆔 {admin_id}" for admin_id in admins])
    
    keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="admin_management")]]
    await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))

# ===== ОБРАБОТЧИКИ СООБЩЕНИЙ =====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    user_id = update.effective_user.id
    text = update.message.text
    
    if not bot.is_admin(user_id):
        return
    
    # Обработка изменения канала
    if context.user_data.get('waiting_for_channel'):
        if text.startswith('@'):
            bot.settings['channel'] = text
            bot.save_settings()
            await update.message.reply_text(f"✅ Канал установлен: {text}")
            context.user_data['waiting_for_channel'] = False
        else:
            await update.message.reply_text("❌ Username канала должен начинаться с @")
    
    # Обработка добавления админа
    elif context.user_data.get('waiting_for_admin_add'):
        try:
            new_admin_id = int(text)
            bot.add_admin(new_admin_id)
            await update.message.reply_text(f"✅ Админ добавлен: {new_admin_id}")
            context.user_data['waiting_for_admin_add'] = False
        except ValueError:
            await update.message.reply_text("❌ ID должен быть числом")
    
    # Обработка удаления админа
    elif context.user_data.get('waiting_for_admin_remove'):
        try:
            admin_id = int(text)
            bot.remove_admin(admin_id)
            await update.message.reply_text(f"✅ Админ удален: {admin_id}")
            context.user_data['waiting_for_admin_remove'] = False
        except ValueError:
            await update.message.reply_text("❌ ID должен быть числом")

# ===== АВТОМАТИЧЕСКАЯ ОТПРАВКА =====
async def auto_send_users(context: ContextTypes.DEFAULT_TYPE):
    """Автоматическая отправка пользователей в канал"""
    if not bot.settings['is_active'] or not bot.settings['channel']:
        return
    
    try:
        user_data = bot.get_next_user()
        if user_data:
            message = bot.format_user_message(user_data)
            await context.bot.send_message(
                chat_id=bot.settings['channel'],
                text=message,
                parse_mode='Markdown'
            )
            logger.info(f"Отправлен пользователь в канал {bot.settings['channel']}")
    except Exception as e:
        logger.error(f"Ошибка авто-отправки: {e}")

# ===== ОСНОВНАЯ ФУНКЦИЯ =====
def main():
    """Запуск бота"""
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Настраиваем job queue для авто-отправки
    job_queue = application.job_queue
    job_queue.run_repeating(
        auto_send_users,
        interval=30,  # Проверка каждые 30 секунд
        first=10
    )
    
    # Добавляем первого админа (замените на ваш ID)
    bot.add_admin(6893832048)  # Ваш Telegram ID
    
    # Запускаем бота
    print("🤖 Бот запущен!")
    application.run_polling()

if __name__ == "__main__":
    main()
