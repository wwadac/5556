from telethon import TelegramClient, events
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext
import asyncio
import logging
import pickle
import os

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурация (можно вынести в отдельный файл или environment variables)
API_ID = 29385016  # Замените на ваш api_id
API_HASH = '3c57df8805ab5de5a23a032ed39b9af9'  # Замените на ваш api_hash
BOT_TOKEN = '8324933170:AAFatQ1T42ZJ70oeWS2UJkcXFeiwUFCIXAk'  # Замените на токен бота
MY_ID =   8000395560 # Замените на ваш user_id

# Словари для хранения каналов
source_channels = {}
destination_channels = {}
channel_mapping = {}

# Клиенты
client = TelegramClient('user_session', API_ID, API_HASH)
bot = Bot(token=BOT_TOKEN)

# Файлы для сохранения данных
DATA_FILE = 'channels_data.pkl'

def save_data():
    """Сохранить данные в файл"""
    data = {
        'source_channels': source_channels,
        'destination_channels': destination_channels,
        'channel_mapping': channel_mapping
    }
    with open(DATA_FILE, 'wb') as f:
        pickle.dump(data, f)

def load_data():
    """Загрузить данные из файла"""
    global source_channels, destination_channels, channel_mapping
    try:
        with open(DATA_FILE, 'rb') as f:
            data = pickle.load(f)
            source_channels = data.get('source_channels', {})
            destination_channels = data.get('destination_channels', {})
            channel_mapping = data.get('channel_mapping', {})
    except FileNotFoundError:
        pass

async def send_notification(message):
    """Отправка уведомления владельцу"""
    try:
        await bot.send_message(chat_id=MY_ID, text=message)
    except Exception as e:
        logger.error(f"Ошибка отправки уведомления: {e}")

def create_main_keyboard():
    """Создать основное меню"""
    keyboard = [
        [InlineKeyboardButton("📥 Добавить канал-источник", callback_data="add_source")],
        [InlineKeyboardButton("📤 Добавить канал-получатель", callback_data="add_destination")],
        [InlineKeyboardButton("🔗 Установить соответствие", callback_data="set_mapping")],
        [InlineKeyboardButton("📋 Список каналов", callback_data="list_channels")],
        [InlineKeyboardButton("🔄 Переслать последние сообщения", callback_data="last_messages")],
        [InlineKeyboardButton("❌ Удалить канал", callback_data="remove_channel")]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_channels_keyboard(channels_dict, callback_prefix):
    """Создать клавиатуру с каналами"""
    keyboard = []
    for channel_id, channel_name in channels_dict.items():
        keyboard.append([InlineKeyboardButton(
            f"{channel_name} ({channel_id})", 
            callback_data=f"{callback_prefix}_{channel_id}"
        )])
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")])
    return InlineKeyboardMarkup(keyboard)

async def start_command(update: Update, context: CallbackContext):
    """Команда /start"""
    if update.effective_user.id != MY_ID:
        return
    
    welcome_text = """
🤖 *Бот для пересылки сообщений между каналами*

*Возможности:*
✅ Автоматическая пересылка новых сообщений
✅ Пересылка старых сообщений
✅ Простая настройка через меню
✅ Работа с любыми публичными каналами

Выберите действие в меню ниже:
    """
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=create_main_keyboard(),
        parse_mode='Markdown'
    )

async def button_handler(update: Update, context: CallbackContext):
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "add_source":
        await query.edit_message_text(
            "📥 *Добавление канала-источника*\n\n"
            "Перешлите любое сообщение из канала, который нужно отслеживать:",
            parse_mode='Markdown'
        )
        context.user_data['waiting_for'] = 'source_channel'

    elif data == "add_destination":
        await query.edit_message_text(
            "📤 *Добавление канала-получателя*\n\n"
            "Перешлите любое сообщение из канала, куда нужно пересылать:",
            parse_mode='Markdown'
        )
        context.user_data['waiting_for'] = 'destination_channel'

    elif data == "set_mapping":
        if not source_channels:
            await query.edit_message_text(
                "❌ Сначала добавьте каналы-источники!",
                reply_markup=create_main_keyboard()
            )
            return
        
        await query.edit_message_text(
            "🔗 *Выберите канал-источник:*",
            reply_markup=create_channels_keyboard(source_channels, "select_source"),
            parse_mode='Markdown'
        )

    elif data == "list_channels":
        await show_channels_list(query)

    elif data == "last_messages":
        if not source_channels:
            await query.edit_message_text(
                "❌ Сначала добавьте каналы-источники!",
                reply_markup=create_main_keyboard()
            )
            return
        
        await query.edit_message_text(
            "🔄 *Выберите канал-источник для пересылки:*",
            reply_markup=create_channels_keyboard(source_channels, "last_source"),
            parse_mode='Markdown'
        )

    elif data == "remove_channel":
        await query.edit_message_text(
            "❌ *Удаление канала*\n\nВыберите тип канала для удаления:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📥 Канал-источник", callback_data="remove_source")],
                [InlineKeyboardButton("📤 Канал-получатель", callback_data="remove_destination")],
                [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")]
            ]),
            parse_mode='Markdown'
        )

    elif data == "remove_source":
        if not source_channels:
            await query.edit_message_text(
                "❌ Нет каналов-источников для удаления!",
                reply_markup=create_main_keyboard()
            )
            return
        
        await query.edit_message_text(
            "❌ *Выберите канал-источник для удаления:*",
            reply_markup=create_channels_keyboard(source_channels, "delete_source"),
            parse_mode='Markdown'
        )

    elif data == "remove_destination":
        if not destination_channels:
            await query.edit_message_text(
                "❌ Нет каналов-получателей для удаления!",
                reply_markup=create_main_keyboard()
            )
            return
        
        await query.edit_message_text(
            "❌ *Выберите канал-получатель для удаления:*",
            reply_markup=create_channels_keyboard(destination_channels, "delete_destination"),
            parse_mode='Markdown'
        )

    elif data.startswith("select_source_"):
        channel_id = int(data.split("_")[2])
        context.user_data['selected_source'] = channel_id
        
        await query.edit_message_text(
            f"🔗 *Источник:* {source_channels[channel_id]}\n\n"
            "Теперь выберите канал-получатель:",
            reply_markup=create_channels_keyboard(destination_channels, "select_dest"),
            parse_mode='Markdown'
        )

    elif data.startswith("select_dest_"):
        dest_channel_id = int(data.split("_")[2])
        source_channel_id = context.user_data.get('selected_source')
        
        if source_channel_id:
            channel_mapping[source_channel_id] = dest_channel_id
            save_data()
            
            await query.edit_message_text(
                f"✅ *Соответствие установлено!*\n\n"
                f"📥 *Источник:* {source_channels[source_channel_id]}\n"
                f"📤 *Получатель:* {destination_channels[dest_channel_id]}",
                reply_markup=create_main_keyboard(),
                parse_mode='Markdown'
            )
            
            await send_notification(
                f"🔗 Новое соответствие:\n"
                f"{source_channels[source_channel_id]} → {destination_channels[dest_channel_id]}"
            )

    elif data.startswith("last_source_"):
        channel_id = int(data.split("_")[2])
        context.user_data['last_source'] = channel_id
        
        await query.edit_message_text(
            f"🔄 *Источник:* {source_channels[channel_id]}\n\n"
            "Введите количество сообщений для пересылки:",
            parse_mode='Markdown'
        )
        context.user_data['waiting_for'] = 'last_count'

    elif data.startswith("delete_source_"):
        channel_id = int(data.split("_")[2])
        channel_name = source_channels.pop(channel_id, None)
        
        # Удаляем связанные соответствия
        if channel_id in channel_mapping:
            del channel_mapping[channel_id]
        
        save_data()
        
        await query.edit_message_text(
            f"✅ Канал-источник '{channel_name}' удален!",
            reply_markup=create_main_keyboard()
        )

    elif data.startswith("delete_destination_"):
        channel_id = int(data.split("_")[2])
        channel_name = destination_channels.pop(channel_id, None)
        
        # Удаляем связанные соответствия
        channel_mapping = {k: v for k, v in channel_mapping.items() if v != channel_id}
        
        save_data()
        
        await query.edit_message_text(
            f"✅ Канал-получатель '{channel_name}' удален!",
            reply_markup=create_main_keyboard()
        )

    elif data == "back_to_main":
        await query.edit_message_text(
            "🤖 *Главное меню*\n\nВыберите действие:",
            reply_markup=create_main_keyboard(),
            parse_mode='Markdown'
        )

async def show_channels_list(query):
    """Показать список всех каналов"""
    if not source_channels and not destination_channels:
        text = "❌ *Каналы не добавлены*"
    else:
        text = "📋 *Список каналов*\n\n"
        
        if source_channels:
            text += "📥 *Каналы-источники:*\n"
            for channel_id, name in source_channels.items():
                text += f"• {name} (`{channel_id}`)\n"
            text += "\n"
        
        if destination_channels:
            text += "📤 *Каналы-получатели:*\n"
            for channel_id, name in destination_channels.items():
                text += f"• {name} (`{channel_id}`)\n"
            text += "\n"
        
        if channel_mapping:
            text += "🔗 *Соответствия:*\n"
            for source_id, dest_id in channel_mapping.items():
                text += f"• {source_channels[source_id]} → {destination_channels[dest_id]}\n"
    
    await query.edit_message_text(
        text,
        reply_markup=create_main_keyboard(),
        parse_mode='Markdown'
    )

async def handle_message(update: Update, context: CallbackContext):
    """Обработчик обычных сообщений"""
    if update.effective_user.id != MY_ID:
        return
    
    waiting_for = context.user_data.get('waiting_for')
    
    if waiting_for == 'last_count':
        try:
            count = int(update.message.text)
            source_channel_id = context.user_data.get('last_source')
            
            if source_channel_id and source_channel_id in channel_mapping:
                dest_channel_id = channel_mapping[source_channel_id]
                
                # Пересылаем сообщения
                await forward_last_messages(source_channel_id, dest_channel_id, count)
                
                await update.message.reply_text(
                    f"✅ Переслано {count} сообщений из {source_channels[source_channel_id]}",
                    reply_markup=create_main_keyboard()
                )
            else:
                await update.message.reply_text(
                    "❌ Ошибка: не установлено соответствие для этого канала",
                    reply_markup=create_main_keyboard()
                )
            
            context.user_data.pop('waiting_for', None)
            context.user_data.pop('last_source', None)
            
        except ValueError:
            await update.message.reply_text("❌ Пожалуйста, введите число!")

async def handle_forwarded_message(update: Update, context: CallbackContext):
    """Обработчик пересланных сообщений для добавления каналов"""
    if update.effective_user.id != MY_ID:
        return
    
    if not update.message.forward_from_chat:
        return
    
    waiting_for = context.user_data.get('waiting_for')
    channel_id = update.message.forward_from_chat.id
    channel_name = update.message.forward_from_chat.title
    
    if waiting_for == 'source_channel':
        source_channels[channel_id] = channel_name
        save_data()
        
        await update.message.reply_text(
            f"✅ *Канал-источник добавлен!*\n\n"
            f"📥 *Название:* {channel_name}\n"
            f"🆔 *ID:* `{channel_id}`",
            reply_markup=create_main_keyboard(),
            parse_mode='Markdown'
        )
        
        context.user_data.pop('waiting_for', None)
        
    elif waiting_for == 'destination_channel':
        destination_channels[channel_id] = channel_name
        save_data()
        
        await update.message.reply_text(
            f"✅ *Канал-получатель добавлен!*\n\n"
            f"📤 *Название:* {channel_name}\n"
            f"🆔 *ID:* `{channel_id}`",
            reply_markup=create_main_keyboard(),
            parse_mode='Markdown'
        )
        
        context.user_data.pop('waiting_for', None)

@client.on(events.NewMessage)
async def new_message_handler(event):
    """Обработчик новых сообщений в Telethon"""
    if event.chat_id in channel_mapping:
        destination_channel_id = channel_mapping[event.chat_id]
        
        try:
            # Пересылаем сообщение
            await client.forward_messages(
                destination_channel_id,
                event.message
            )
            
            logger.info(f"📨 Переслано сообщение из {source_channels[event.chat_id]} в {destination_channels[destination_channel_id]}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка пересылки: {e}")
            await send_notification(f"❌ Ошибка пересылки: {e}")

async def forward_last_messages(source_channel_id, dest_channel_id, count):
    """Переслать последние сообщения"""
    try:
        messages = await client.get_messages(source_channel_id, limit=count)
        
        # Пересылаем в обратном порядке (от старых к новым)
        for message in reversed(messages):
            try:
                await client.forward_messages(dest_channel_id, message)
                await asyncio.sleep(0.5)  # Небольшая задержка
            except Exception as e:
                logger.error(f"Ошибка при пересылке сообщения: {e}")
        
        logger.info(f"✅ Переслано {len(messages)} сообщений")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при получении сообщений: {e}")
        await send_notification(f"❌ Ошибка пересылки старых сообщений: {e}")

async def main():
    """Основная функция"""
    # Загружаем сохраненные данные
    load_data()
    
    # Запускаем Telethon клиент
    await client.start()
    
    # Настраиваем бота
    updater = Updater(BOT_TOKEN)
    dp = updater.dispatcher
    
    # Добавляем обработчики
    dp.add_handler(CommandHandler("start", start_command))
    dp.add_handler(CallbackQueryHandler(button_handler))
    dp.add_handler(telegram.ext.MessageHandler(
        telegram.ext.Filters.text & ~telegram.ext.Filters.command, 
        handle_message
    ))
    dp.add_handler(telegram.ext.MessageHandler(
        telegram.ext.Filters.forwarded, 
        handle_forwarded_message
    ))
    
    # Запускаем бота
    updater.start_polling()
    
    await send_notification("🤖 Бот запущен и готов к работе!")
    logger.info("Бот запущен")
    
    # Запускаем клиент
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
