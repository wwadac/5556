# main.py
import os
import asyncio
from datetime import datetime, timedelta
from pyrogram import Client, filters, idle
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode
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
            bot_token=self.config.get('bot_token', '8231456588:AAGNtU0IvMnpFBSGFOTzhIWUiUeplaSNhCU'),
            parse_mode=ParseMode.HTML
        )
        
        # Регистрация обработчиков
        self.setup_handlers()
    
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
    
    def setup_handlers(self):
        """Настройка обработчиков"""
        
        @self.bot.on_message(filters.command("start"))
        async def start_command(client: Client, message: Message):
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔐 Авторизация", callback_data="auth_menu"),
                 InlineKeyboardButton("🔍 Парсинг", callback_data="parse_menu")],
                [InlineKeyboardButton("⚙️ Настройки", callback_data="settings_menu")]
            ])
            
            await message.reply_text(
                "👋 <b>Привет! Я бот для парсинга Telegram чатов</b>\n\n"
                "📋 <b>Доступные команды:</b>\n"
                "/auth - 🔐 Авторизовать аккаунт для парсинга\n"
                "/proxy - 🔧 Настроить прокси\n"
                "/parse - 🔍 Начать парсинг чата\n"
                "/my - 📊 Мои аккаунты\n"
                "/help - ❓ Помощь\n\n"
                "⚡ <b>Быстрый старт:</b>\n"
                "1. Используйте /auth для добавления аккаунта\n"
                "2. Используйте /parse для парсинга",
                reply_markup=keyboard
            )
        
        @self.bot.on_message(filters.command("auth"))
        async def auth_command(client: Client, message: Message):
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📱 По номеру телефона", callback_data="auth_phone")],
                [InlineKeyboardButton("🔑 По сессии Telethon", callback_data="auth_session")],
                [InlineKeyboardButton("❌ Отмена", callback_data="cancel")]
            ])
            await message.reply_text(
                "<b>🔐 Выберите способ авторизации:</b>",
                reply_markup=keyboard
            )
        
        @self.bot.on_message(filters.command("parse"))
        async def parse_command(client: Client, message: Message):
            user_id = message.from_user.id
            
            if str(user_id) not in self.parser_sessions:
                await message.reply_text(
                    "❌ <b>У вас нет активных сессий!</b>\n"
                    "Сначала используйте /auth для авторизации аккаунта."
                )
                return
            
            await message.reply_text(
                "🔍 <b>Введите ссылку на чат для парсинга:</b>\n\n"
                "<b>Примеры:</b>\n"
                "• @username\n"
                "• https://t.me/username\n"
                "• https://t.me/c/123456789\n\n"
                "<i>Просто отправьте ссылку в ответ на это сообщение</i>"
            )
        
        @self.bot.on_message(filters.command("proxy"))
        async def proxy_command(client: Client, message: Message):
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Добавить прокси", callback_data="add_proxy")],
                [InlineKeyboardButton("📋 Мои прокси", callback_data="list_proxy")],
                [InlineKeyboardButton("⚙️ Настроить SOCKS5", callback_data="setup_socks5")]
            ])
            
            await message.reply_text(
                "<b>🔧 Управление прокси:</b>",
                reply_markup=keyboard
            )
        
        @self.bot.on_message(filters.command("my"))
        async def my_command(client: Client, message: Message):
            user_id = str(message.from_user.id)
            
            if user_id not in self.parser_sessions:
                await message.reply_text("❌ <b>У вас нет активных сессий</b>")
                return
            
            sessions = self.parser_sessions[user_id]
            text = "<b>📊 Ваши активные сессии:</b>\n\n"
            
            for idx, session in enumerate(sessions, 1):
                text += f"<b>{idx}.</b> Аккаунт ID: <code>{session.get('user_id', 'Неизвестно')}</code>\n"
                if session.get('username'):
                    text += f"   👤 @{session['username']}\n"
                text += f"   📅 Добавлен: {session.get('added_date', 'Неизвестно')}\n\n"
            
            await message.reply_text(text)
        
        @self.bot.on_message(filters.command("help"))
        async def help_command(client: Client, message: Message):
            help_text = """
🤖 <b>Telegram Parser Bot - Помощь</b>

🔐 <b>Авторизация:</b>
• Используйте /auth для добавления аккаунта
• Можно добавить несколько аккаунтов

🔧 <b>Прокси:</b>
• /proxy - настройка прокси (SOCKS5/HTTP)
• Поддерживается ротация прокси

🔍 <b>Парсинг:</b>
• /parse - начать парсинг чата
• Бот автоматически отправит файл с юзернеймами

⚙️ <b>Настройки:</b>
• Можно указать период парсинга (дни)
• Настройка лимита сообщений

⚠️ <b>Важно:</b>
• Используйте отдельные прокси для каждого аккаунта
• Не парсите слишком быстро (риск бана)
• Сохраняйте сессии
            """
            await message.reply_text(help_text)
        
        @self.bot.on_message(filters.text & filters.private & ~filters.command(["start", "auth", "parse", "proxy", "my", "help"]))
        async def handle_text(client: Client, message: Message):
            """Обработка текстовых сообщений"""
            user_id = str(message.from_user.id)
            text = message.text.strip()
            
            # Если это похоже на ссылку на чат
            if any(trigger in text for trigger in ['@', 't.me/', 'telegram.me/', 'https://t.me/']):
                if user_id in self.parser_sessions:
                    await self.start_parsing(message, text)
                else:
                    await message.reply_text("❌ <b>Сначала авторизуйте аккаунт через /auth</b>")
        
        # Обработка callback кнопок
        @self.bot.on_callback_query()
        async def handle_callback(client: Client, callback_query):
            data = callback_query.data
            user_id = str(callback_query.from_user.id)
            message = callback_query.message
            
            if data == "auth_menu":
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("📱 По номеру телефона", callback_data="auth_phone")],
                    [InlineKeyboardButton("🔑 По сессии Telethon", callback_data="auth_session")],
                    [InlineKeyboardButton("❌ Отмена", callback_data="cancel")]
                ])
                await message.edit_text(
                    "<b>🔐 Выберите способ авторизации:</b>",
                    reply_markup=keyboard
                )
            
            elif data == "auth_phone":
                await message.edit_text(
                    "📱 <b>Введите номер телефона:</b>\n\n"
                    "<b>Формат:</b> +79123456789\n\n"
                    "<i>Отправьте номер в следующем сообщении</i>"
                )
            
            elif data == "auth_session":
                await message.edit_text(
                    "🔑 <b>Введите сессию Telethon:</b>\n\n"
                    "<i>Отправьте строку сессии в следующем сообщении</i>"
                )
            
            elif data == "parse_menu":
                if user_id not in self.parser_sessions:
                    await callback_query.answer("❌ Сначала авторизуйтесь!", show_alert=True)
                    return
                
                await message.edit_text(
                    "🔍 <b>Введите ссылку на чат для парсинга:</b>\n\n"
                    "<b>Примеры:</b>\n"
                    "• @username\n"
                    "• https://t.me/username\n"
                    "• https://t.me/c/123456789"
                )
            
            elif data == "setup_socks5":
                await message.edit_text(
                    "🔧 <b>Настройка SOCKS5 прокси:</b>\n\n"
                    "Отправьте прокси в формате:\n"
                    "<code>ip:port:username:password</code>\n\n"
                    "<b>Примеры:</b>\n"
                    "• <code>1.1.1.1:1080:user:pass</code>\n"
                    "• <code>2.2.2.2:9050::</code>\n"
                    "• <code>3.3.3.3:4145::</code>\n\n"
                    "<i>Отправьте в следующем сообщении</i>"
                )
            
            elif data == "cancel":
                await message.delete()
            
            await callback_query.answer()
    
    async def start_parsing(self, message: Message, chat_link: str):
        """Начало процесса парсинга"""
        user_id = str(message.from_user.id)
        
        # Отправляем сообщение о начале
        status_msg = await message.reply_text(
            "⏳ <b>Начинаю парсинг...</b>\n"
            f"🔗 Чат: {chat_link}\n"
            "📊 Это может занять некоторое время..."
        )
        
        try:
            # Получаем сессию пользователя
            if user_id not in self.parser_sessions:
                await status_msg.edit_text("❌ <b>Нет активных сессий</b>")
                return
            
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
                    f"✅ <b>Парсинг завершен!</b>\n\n"
                    f"💬 Чат: {chat_title}\n"
                    f"👤 Пользователей: {len(usernames)}\n"
                    f"📁 Файл отправлен!"
                )
            else:
                await status_msg.edit_text("❌ <b>Не удалось получить пользователей</b>")
            
            await parser_client.disconnect()
            
        except Exception as e:
            await status_msg.edit_text(f"❌ <b>Ошибка:</b> {str(e)}")
    
    async def create_parser_client(self, session_data):
        """Создание клиента Telethon для парсинга"""
        # Используем прокси если есть
        proxy = None
        if session_data.get('proxy'):
            proxy = {
                'proxy_type': 'socks5',
                'addr': session_data['proxy']['host'],
                'port': session_data['proxy']['port'],
                'username': session_data['proxy'].get('username', ''),
                'password': session_data['proxy'].get('password', ''),
                'rdns': True
            }
        
        client = TelegramClient(
            StringSession(session_data['session_string']),
            api_id=session_data['api_id'],
            api_hash=session_data['api_hash'],
            proxy=proxy
        )
        
        await client.start()
        return client
    
    async def parse_telethon_chat(self, client, chat_link, days=7, limit=2000):
        """Парсинг чата через Telethon"""
        try:
            chat = await client.get_entity(chat_link)
            chat_title = getattr(chat, 'title', 'Unknown')
            
            # Собираем сообщения за период
            since_date = datetime.now() - timedelta(days=days)
            user_ids = set()
            
            print(f"🔍 Парсим чат: {chat_title}")
            print(f"📅 За последние {days} дней")
            print(f"📊 Лимит: {limit} сообщений")
            
            message_count = 0
            async for message in client.iter_messages(
                chat,
                limit=limit,
                offset_date=since_date
            ):
                message_count += 1
                if message_count % 100 == 0:
                    print(f"   Собрано сообщений: {message_count}")
                
                if message.sender_id:
                    user_ids.add(message.sender_id)
            
            print(f"📊 Всего сообщений: {message_count}")
            print(f"👥 Уникальных отправителей: {len(user_ids)}")
            
            usernames = []
            print("👤 Получаю юзернеймы...")
            
            for i, user_id in enumerate(user_ids):
                try:
                    user = await client.get_entity(user_id)
                    if user.username:
                        usernames.append(user.username)
                    else:
                        usernames.append(f"id_{user_id}")
                    
                    if i % 10 == 0:
                        await asyncio.sleep(0.1)
                        
                except Exception as e:
                    print(f"   Ошибка при получении пользователя {user_id}: {e}")
                    continue
            
            return usernames, chat_title
            
        except Exception as e:
            print(f"❌ Ошибка парсинга: {e}")
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
            f"✅ <b>Парсинг завершен!</b>\n\n"
            f"💬 <b>Чат:</b> {chat_title}\n"
            f"👤 <b>Пользователей:</b> {count}\n"
            f"📅 <b>Дата:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        try:
            await message.reply_document(
                document=filename,
                caption=caption,
                parse_mode=ParseMode.HTML
            )
        finally:
            # Удаляем временный файл
            try:
                os.remove(filename)
            except:
                pass
    
    async def run(self):
        """Запуск бота"""
        print("🤖 Запуск Telegram бота...")
        await self.bot.start()
        print("✅ Бот запущен! Отправьте /start")
        await idle()
        await self.bot.stop()


async def main():
    """Главная функция"""
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
    
    # Проверяем конфиг
    if not os.path.exists('bot_config.json'):
        print("❌ Создайте файл bot_config.json")
        print("""
Пример содержимого:
{
    "api_id": 29385016,
    "api_hash": "3c57df8805ab5de5a23a032ed39b9af9",
    "bot_token": "ВАШ_ТОКЕН_БОТА"
}
""")
        return
    
    bot = TelegramParserBot()
    await bot.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен")
