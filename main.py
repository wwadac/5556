import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, File
import pandas as pd
import io
import os

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен бота (замени на свой)
API_TOKEN = '8324933170:AAFatQ1T42ZJ70oeWS2UJkcXFeiwUFCIXAk'

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Хранилище для данных (в памяти)
user_data = {}

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "📊 Бот для работы с Excel базой пользователей\n\n"
        "Отправь мне Excel файл (.xlsx) со столбцом 'username' или 'user_id'\n"
        "Затем используй команду /mention_all для упоминания всех пользователей\n"
        "Команда /clear - очистить базу"
    )

@dp.message(Command("clear"))
async def cmd_clear(message: Message):
    user_data[message.chat.id] = []
    await message.answer("✅ База данных очищена")

@dp.message(Command("mention_all"))
async def cmd_mention_all(message: Message):
    chat_id = message.chat.id
    
    if chat_id not in user_data or not user_data[chat_id]:
        await message.answer("❌ База данных пуста. Сначала отправь Excel файл")
        return
    
    users = user_data[chat_id]
    mentions = []
    
    for user in users:
        if 'username' in user and user['username']:
            # Если есть username, создаем ссылку
            username = user['username'].lstrip('@')
            mentions.append(f"@{username}")
        elif 'user_id' in user and user['user_id']:
            # Если есть user_id, упоминаем по ID
            mentions.append(f"<a href='tg://user?id={user['user_id']}'>👤</a>")
        elif 'name' in user and user['name']:
            # Если есть только имя
            mentions.append(f"👤 {user['name']}")
    
    if mentions:
        text = "📢 Упоминания из базы данных:\n\n" + "\n".join(mentions)
        await message.answer(text, parse_mode='HTML')
    else:
        await message.answer("❌ Не найдено данных для упоминания")

@dp.message(F.document)
async def handle_excel_file(message: Message):
    # Проверяем, что файл Excel
    if not (message.document.file_name.endswith('.xlsx') or 
            message.document.file_name.endswith('.xls')):
        await message.answer("❌ Пожалуйста, отправьте файл в формате Excel (.xlsx или .xls)")
        return
    
    try:
        # Скачиваем файл
        file = await bot.get_file(message.document.file_id)
        file_path = file.file_path
        
        # Скачиваем содержимое файла
        file_content = await bot.download_file(file_path)
        
        # Читаем Excel файл
        excel_data = pd.read_excel(file_content)
        
        # Преобразуем в список словарей
        users = excel_data.to_dict('records')
        
        # Сохраняем в память
        user_data[message.chat.id] = users
        
        # Формируем отчет
        total_users = len(users)
        columns = list(excel_data.columns)
        
        response = (
            f"✅ Файл успешно загружен!\n"
            f"📊 Загружено записей: {total_users}\n"
            f"📋 Колонки: {', '.join(columns)}\n\n"
            f"Теперь используй команду /mention_all для упоминания пользователей"
        )
        
        await message.answer(response)
        
    except Exception as e:
        logger.error(f"Error processing Excel file: {e}")
        await message.answer("❌ Ошибка при обработке файла. Убедитесь, что это корректный Excel файл")

@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    chat_id = message.chat.id
    
    if chat_id not in user_data or not user_data[chat_id]:
        await message.answer("📊 База данных пуста")
        return
    
    users = user_data[chat_id]
    total = len(users)
    
    # Статистика по колонкам
    columns = {}
    for user in users:
        for key, value in user.items():
            if pd.notna(value):  # Проверяем, что значение не NaN
                if key not in columns:
                    columns[key] = 0
                columns[key] += 1
    
    stats_text = f"📊 Статистика базы данных:\n\nВсего записей: {total}\n\n"
    
    for column, count in columns.items():
        stats_text += f"{column}: {count} записей\n"
    
    await message.answer(stats_text)

@dp.message(Command("help"))
async def cmd_help(message: Message):
    help_text = """
🤖 Помощь по боту:

📥 Загрузка данных:
- Просто отправь Excel файл (.xlsx) с данными пользователей
- Обязательная колонка: 'username' или 'user_id'
- Дополнительно можно добавить: 'name', 'id', etc.

📊 Команды:
/start - начать работу
/mention_all - упомянуть всех пользователей из базы
/stats - статистика базы данных
/clear - очистить базу
/help - эта справка

💡 Пример Excel файла:
username       | name
@user1        | Иван
@user2        | Мария
123456789     | Петр (как user_id)
"""
    await message.answer(help_text)

async def main():
    logger.info("Starting bot...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
