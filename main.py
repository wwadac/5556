# main.py
import os
import asyncio
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from telethon import TelegramClient
from telethon.sessions import StringSession
import json

class TelegramParserBot:
    def __init__(self):
        # Конфигурация
        self.config_file = 'bot_config.json'
        self.parser_sessions = {}  # {user_id: session_data}
        
        # Загрузка конфигурации
        self.config = self.load_config()
        
        # Инициализация бота
        self.bot = Client(
            "parser_bot",
            api_id=self.config.get('api_id', 29385016),
            api_hash=self.config.get('api_hash', '3c57df8805ab5de5a23a032ed39b9af9'),
            bot_token=self.config.get('bot_token', '8231456588:AAGNtU0IvMnpFBSGFOTzhIWUiUeplaSNhCU')  # Получите у @BotFather
        )
    
    def load_config(self):
        """Загрузка конфигурации"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                return json.load(f)
        return {}
    
    def save_config(self):
        """Сохранение конфигурации"""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=4)
    
    async def start_bot(self):
        """Запуск бота"""
        print("🤖 Запуск Telegram бота...")
        
        # Регистрация обработчиков
        @self.bot.on_message(filters.command("start"))
        async def start_command(client: Client, message: Message):
            await message.reply_text(
                "👋 **Привет! Я бот для парсинга Telegram чатов**\n\n"
                "📋 **Доступные команды:**\n"
                "/auth - 🔐 Авторизовать аккаунт для парсинга\n"
                "/proxy - 🔧 Настроить прокси\n"
                "/parse - 🔍 Начать парсинг чата\n"
                "/sessions - 📊 Мои сессии\n"
                "/help - ❓ Помощь\n\n"
                "⚡ **Быстрый старт:**\n"
                "1. Используйте /auth для добавления аккаунта\n"
                "2. Используйте /parse для парсинга",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔐 Авторизация", callback_data="auth"),
                     InlineKeyboardButton("🔍 Парсинг", callback_data="parse")]
                ])
            )
        
        @self.bot.on_message(filters.command("auth"))
        async def auth_command(client: Client, message: Message):
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📱 По номеру телефона", callback_data="auth_phone")],
                [InlineKeyboardButton("🔑 По сессии", callback_data="auth_session")]
            ])
            await message.reply_text(
                "🔐 **Выберите способ авторизации:**",
                reply_markup=keyboard
            )
        
        @self.bot.on_message(filters.command("parse"))
        async def parse_command(client: Client, message: Message):
            user_id = message.from_user.id
            
            if str(user_id) not in self.parser_sessions:
                await message.reply_text(
                    "❌ **У вас нет активных сессий!**\n"
                    "Сначала используйте /auth для авторизации аккаунта."
                )
                return
            
            await message.reply_text(
                "🔍 **Введите ссылку на чат для парсинга:**\n\n"
                "Примеры:\n"
                "• @username\n"
                "• https://t.me/username\n"
                "• https://t.me/c/123456789\n\n"
                "💡 _Просто отправьте ссылку в ответ на это сообщение_"
            )
        
        @self.bot.on_message(filters.command("proxy"))
        async def proxy_command(client: Client, message: Message):
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Добавить прокси", callback_data="add_proxy")],
                [InlineKeyboardButton("📋 Мои прокси", callback_data="list_proxy")],
                [InlineKeyboardButton("🗑️ Удалить прокси", callback_data="remove_proxy")]
            ])
            
            await message.reply_text(
                "🔧 **Управление прокси:**",
                reply_markup=keyboard
            )
        
        @self.bot.on_message(filters.command("sessions"))
        async def sessions_command(client: Client, message: Message):
            user_id = str(message.from_user.id)
            
            if user_id not in self.parser_sessions:
                await message.reply_text("❌ **У вас нет активных сессий**")
                return
            
            sessions = self.parser_sessions[user_id]
            text = "📊 **Ваши активные сессии:**\n\n"
            
            for idx, session in enumerate(sessions, 1):
                text += f"**{idx}.** Аккаунт ID: `{session.get('user_id', 'Неизвестно')}`\n"
                if session.get('username'):
                    text += f"   👤 @{session['username']}\n"
                text += f"   📅 Добавлен: {session.get('added_date', 'Неизвестно')}\n\n"
            
            await message.reply_text(text)
        
        @self.bot.on_message(filters.command("help"))
        async def help_command(client: Client, message: Message):
            help_text = """
            🤖 **Telegram Parser Bot - Помощь**

            🔐 **Авторизация:**
            • Используйте /auth для добавления аккаунта
            • Можно добавить несколько аккаунтов
            
            🔧 **Прокси:**
            • /proxy - настройка прокси (SOCKS5/HTTP)
            • Поддерживается ротация прокси
            
            🔍 **Парсинг:**
            • /parse - начать парсинг чата
            • Бот автоматически отправит файл с юзернеймами
            
            ⚙️ **Настройки:**
            • Можно указать период парсинга (дни)
            • Настройка лимита сообщений
            
            ⚠️ **Важно:**
            • Используйте отдельные прокси для каждого аккаунта
            • Не парсите слишком быстро (риск бана)
            • Сохраняйте сессии
            
            📞 **Поддержка:**
            По вопросам: @ваш_ник
            """
            await message.reply_text(help_text)
        
        # Обработка ссылок на чаты
        @self.bot.on_message(filters.text & filters.private)
        async def handle_chat_link(client: Client, message: Message):
            user_id = str(message.from_user.id)
            
            # Проверяем, это ссылка на чат?
            text = message.text.strip()
            if any(trigger in text for trigger in ['@', 't.me/', 'telegram.me/']):
                # Это похоже на ссылку на чат
                if user_id in self.parser_sessions:
                    await self.start_parsing(message, text)
        
        # Обработка inline кнопок
        @self.bot.on_callback_query()
        async def handle_callback(client: Client, callback_query):
            data = callback_query.data
            user_id = str(callback_query.from_user.id)
            
            if data == "auth":
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("📱 По номеру телефона", callback_data="auth_phone")],
                    [InlineKeyboardButton("🔑 По сессии", callback_data="auth_session")]
                ])
                await callback_query.message.edit_text(
                    "🔐 **Выберите способ авторизации:**",
                    reply_markup=keyboard
                )
            
            elif data == "auth_phone":
                await callback_query.message.edit_text(
                    "📱 **Введите номер телефона:**\n\n"
                    "Формат: +79123456789\n\n"
                    "💡 _Отправьте номер в ответ на это сообщение_"
                )
                # Здесь нужно сохранить состояние для ожидания номера
            
            elif data == "parse":
                if user_id not in self.parser_sessions:
                    await callback_query.answer("❌ Сначала авторизуйтесь!", show_alert=True)
                    return
                
                await callback_query.message.edit_text(
                    "🔍 **Введите ссылку на чат для парсинга:**\n\n"
                    "Примеры:\n"
                    "• @username\n"
                    "• https://t.me/username\n"
                    "• https://t.me/c/123456789"
                )
            
            elif data == "add_proxy":
                await callback_query.message.edit_text(
                    "🔧 **Добавление прокси:**\n\n"
                    "Отправьте прокси в формате:\n"
                    "`тип:адрес:порт:логин:пароль`\n\n"
                    "Примеры:\n"
                    "`socks5:1.1.1.1:1080:user:pass`\n"
                    "`http:2.2.2.2:8080::`\n"
                    "`socks5:3.3.3.3:9050::`\n\n"
                    "💡 _Отправьте в ответ на это сообщение_"
                )
            
            await callback_query.answer()
        
        # Запуск бота
        print("✅ Бот запущен! Отправьте /start")
        await self.bot.start()
        await self.bot.idle()
    
    async def start_parsing(self, message: Message, chat_link: str):
        """Начало процесса парсинга"""
        user_id = str(message.from_user.id)
        
        # Отправляем сообщение о начале
        status_msg = await message.reply_text(
            "⏳ **Начинаю парсинг...**\n"
            f"🔗 Чат: {chat_link}\n"
            "📊 Это может занять некоторое время..."
        )
        
        try:
            # Получаем сессию пользователя
            session_data = self.parser_sessions[user_id][0]  # Берём первую сессию
            
            # Создаем клиента для парсинга
            parser_client = await self.create_parser_client(session_data)
            
            # Парсим чат
            usernames, chat_title = await self.parse_telethon_chat(parser_client, chat_link)
            
            if usernames:
                # Сохраняем результаты
                filename = self.save_results_to_file(usernames, chat_title, user_id)
                
                # Отправляем файл
                await self.send_results_file(message, filename, chat_title, len(usernames))
                
                # Обновляем статус
                await status_msg.edit_text(
                    f"✅ **Парсинг завершен!**\n\n"
                    f"💬 Чат: {chat_title}\n"
                    f"👤 Пользователей: {len(usernames)}\n"
                    f"📁 Файл отправлен!"
                )
            else:
                await status_msg.edit_text("❌ **Не удалось получить пользователей**")
            
            await parser_client.disconnect()
            
        except Exception as e:
            await status_msg.edit_text(f"❌ **Ошибка:** {str(e)}")
    
    async def create_parser_client(self, session_data):
        """Создание клиента Telethon для парсинга"""
        # Здесь создаем клиент с сессией и прокси
        # Это упрощенная версия, нужно доработать
        
        client = TelegramClient(
            StringSession(session_data['session_string']),
            api_id=session_data['api_id'],
            api_hash=session_data['api_hash']
        )
        
        await client.start()
        return client
    
    async def parse_telethon_chat(self, client, chat_link, days=7, limit=2000):
        """Парсинг чата через Telethon"""
        try:
            chat = await client.get_entity(chat_link)
            chat_title = getattr(chat, 'title', 'Unknown')
            
            # Здесь логика парсинга как в предыдущем коде
            # Упрощенная версия:
            
            from datetime import timedelta
            since_date = datetime.now() - timedelta(days=days)
            user_ids = set()
            
            async for message in client.iter_messages(
                chat,
                limit=limit,
                offset_date=since_date
            ):
                if message.sender_id:
                    user_ids.add(message.sender_id)
            
            usernames = []
            for user_id in user_ids:
                try:
                    user = await client.get_entity(user_id)
                    if user.username:
                        usernames.append(user.username)
                    else:
                        usernames.append(f"id_{user_id}")
                except:
                    continue
            
            return usernames, chat_title
            
        except Exception as e:
            print(f"Ошибка парсинга: {e}")
            return [], "Unknown"
    
    def save_results_to_file(self, usernames, chat_title, user_id):
        """Сохранение результатов в файл"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"users_{user_id}_{timestamp}.txt"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"# Парсинг: {chat_title}\n")
            f.write(f"# Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# Пользователей: {len(usernames)}\n")
            f.write("#" * 50 + "\n\n")
            
            for username in usernames:
                f.write(f"{'@' + username if not username.startswith('id_') else username}\n")
        
        return filename
    
    async def send_results_file(self, message: Message, filename: str, chat_title: str, count: int):
        """Отправка файла с результатами"""
        caption = (
            f"✅ **Парсинг завершен!**\n\n"
            f"💬 **Чат:** {chat_title}\n"
            f"👤 **Пользователей:** {count}\n"
            f"📅 **Дата:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        await message.reply_document(
            document=filename,
            caption=caption
        )
        
        # Удаляем временный файл
        try:
            os.remove(filename)
        except:
            pass

# Файл с настройками
# bot_config.json - создайте его вручную с таким содержимым:
"""
{
    "api_id": 29385016,
    "api_hash": "3c57df8805ab5de5a23a032ed39b9af9",
    "bot_token": "ВАШ_ТОКЕН_БОТА_ОТ_BOTFATHER"
}
"""

async def main():
    """Главная функция"""
    bot = TelegramParserBot()
    await bot.start_bot()

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════╗
║    🤖 TELEGRAM PARSER BOT           ║
║                                      ║
║    🔐 Авторизация аккаунтов         ║
║    🔧 Поддержка прокси (SOCKS5)     ║
║    🔍 Парсинг чатов                 ║
║    📤 Авто-отправка файлов          ║
╚══════════════════════════════════════╝
    """)
    
    # Запуск бота
    asyncio.run(main())
