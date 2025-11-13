import os
import logging
import asyncio
from telethon import TelegramClient, events
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурация
API_ID = int(os.getenv('API_ID', '29385016'))
API_HASH = os.getenv('API_HASH', '3c57df8805ab5de5a23a032ed39b9af9')
BOT_TOKEN = os.getenv('BOT_TOKEN', '8324933170:AAFatQ1T42ZJ70oeWS2UJkcXFeiwUFCIXAk')
MY_ID = int(os.getenv('MY_ID', '8000395560'))
SESSION_NAME = 'user_session'

# Глобальные переменные
client = None
channels_data = {
    'sources': {},
    'destinations': {},
    'mapping': {}
}

async def initialize_telethon():
    """Инициализация Telethon клиента"""
    global client
    
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.start()
    
    # Проверяем авторизацию
    if not await client.is_user_authorized():
        # Если нет сессии, запрашиваем номер телефона
        phone = input("Введите номер телефона: ")
        await client.send_code_request(phone)
        code = input("Введите код: ")
        await client.sign_in(phone, code)
    
    logger.info("Telethon клиент авторизован")
    return client

def create_main_keyboard():
    """Главное меню"""
    keyboard = [
        [InlineKeyboardButton("📥 Добавить источник", callback_data="add_source")],
        [InlineKeyboardButton("📤 Добавить получателя", callback_data="add_dest")],
        [InlineKeyboardButton("🔗 Связать каналы", callback_data="set_mapping")],
        [InlineKeyboardButton("📋 Мои каналы", callback_data="list_channels")],
        [InlineKeyboardButton("🔄 Переслать сообщения", callback_data="forward_messages")],
        [InlineKeyboardButton("🗑️ Удалить канал", callback_data="remove_channel")]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_channels_keyboard(channels_dict, prefix):
    """Клавиатура с каналами"""
    keyboard = []
    for channel_id, name in channels_dict.items():
        keyboard.append([InlineKeyboardButton(
            f"{name}", 
            callback_data=f"{prefix}_{channel_id}"
        )])
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    if update.effective_user.id != MY_ID:
        await update.message.reply_text("❌ Доступ запрещен")
        return
    
    welcome_text = """
🤖 *Бот для пересылки сообщений между каналами*

*Работает через ваш аккаунт Telegram*
✅ Пересылает новые сообщения в реальном времени
✅ Пересылает медиа, фото, документы
✅ Простая настройка через меню

Выберите действие ниже 👇
    """
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=create_main_keyboard(),
        parse_mode='Markdown'
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопок"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "main_menu":
        await show_main_menu(query)
    
    elif data == "add_source":
        await query.edit_message_text(
            "📥 *Добавление канала-источника*\n\n"
            "Перешлите сюда любое сообщение из канала, который хотите отслеживать.",
            parse_mode='Markdown'
        )
        context.user_data['waiting'] = 'source'
    
    elif data == "add_dest":
        await query.edit_message_text(
            "📤 *Добавление канала-получателя*\n\n"
            "Перешлите сюда любое сообщение из канала, куда нужно пересылать.",
            parse_mode='Markdown'
        )
        context.user_data['waiting'] = 'destination'
    
    elif data == "set_mapping":
        if not channels_data['sources']:
            await query.edit_message_text(
                "❌ Сначала добавьте каналы-источники!",
                reply_markup=create_main_keyboard()
            )
            return
        
        await query.edit_message_text(
            "🔗 *Выберите канал-источник:*",
            reply_markup=create_channels_keyboard(channels_data['sources'], "map_source"),
            parse_mode='Markdown'
        )
    
    elif data == "list_channels":
        await show_channels_list(query)
    
    elif data == "forward_messages":
        if not channels_data['sources']:
            await query.edit_message_text(
                "❌ Сначала добавьте каналы!",
                reply_markup=create_main_keyboard()
            )
            return
        
        await query.edit_message_text(
            "🔄 *Выберите канал-источник:*",
            reply_markup=create_channels_keyboard(channels_data['sources'], "forward_source"),
            parse_mode='Markdown'
        )
    
    elif data == "remove_channel":
        await show_remove_menu(query)
    
    elif data.startswith("map_source_"):
        channel_id = int(data.split("_")[2])
        context.user_data['mapping_source'] = channel_id
        
        if not channels_data['destinations']:
            await query.edit_message_text(
                "❌ Сначала добавьте каналы-получатели!",
                reply_markup=create_main_keyboard()
            )
            return
        
        await query.edit_message_text(
            f"🔗 Источник: {channels_data['sources'][channel_id]}\n\n"
            "Выберите канал-получатель:",
            reply_markup=create_channels_keyboard(channels_data['destinations'], "map_dest"),
            parse_mode='Markdown'
        )
    
    elif data.startswith("map_dest_"):
        dest_id = int(data.split("_")[2])
        source_id = context.user_data.get('mapping_source')
        
        if source_id:
            channels_data['mapping'][source_id] = dest_id
            
            # Перезагружаем обработчики событий
            await setup_event_handlers()
            
            await query.edit_message_text(
                f"✅ *Связь установлена!*\n\n"
                f"📥 {channels_data['sources'][source_id]}\n⬇️\n"
                f"📤 {channels_data['destinations'][dest_id]}\n\n"
                f"Теперь новые сообщения будут пересылаться автоматически!",
                reply_markup=create_main_keyboard(),
                parse_mode='Markdown'
            )
    
    elif data.startswith("forward_source_"):
        channel_id = int(data.split("_")[2])
        context.user_data['forward_source'] = channel_id
        
        await query.edit_message_text(
            f"🔄 Пересылка из: {channels_data['sources'][channel_id]}\n\n"
            "Введите количество сообщений для пересылки:",
            parse_mode='Markdown'
        )
        context.user_data['waiting'] = 'forward_count'
    
    elif data == "remove_source":
        if not channels_data['sources']:
            await query.edit_message_text(
                "❌ Нет каналов для удаления!",
                reply_markup=create_main_keyboard()
            )
            return
        
        await query.edit_message_text(
            "🗑️ *Удаление канала-источника:*",
            reply_markup=create_channels_keyboard(channels_data['sources'], "delete_source"),
            parse_mode='Markdown'
        )
    
    elif data == "remove_dest":
        if not channels_data['destinations']:
            await query.edit_message_text(
                "❌ Нет каналов для удаления!",
                reply_markup=create_main_keyboard()
            )
            return
        
        await query.edit_message_text(
            "🗑️ *Удаление канала-получателя:*",
            reply_markup=create_channels_keyboard(channels_data['destinations'], "delete_dest"),
            parse_mode='Markdown'
        )
    
    elif data.startswith("delete_source_"):
        channel_id = int(data.split("_")[2])
        name = channels_data['sources'].pop(channel_id, "Неизвестный")
        
        # Удаляем связанные маппинги
        if channel_id in channels_data['mapping']:
            del channels_data['mapping'][channel_id]
        
        # Перезагружаем обработчики
        await setup_event_handlers()
        
        await query.edit_message_text(
            f"✅ Канал-источник '{name}' удален!",
            reply_markup=create_main_keyboard()
        )
    
    elif data.startswith("delete_dest_"):
        channel_id = int(data.split("_")[2])
        name = channels_data['destinations'].pop(channel_id, "Неизвестный")
        
        # Удаляем связанные маппинги
        channels_data['mapping'] = {k: v for k, v in channels_data['mapping'].items() if v != channel_id}
        
        await query.edit_message_text(
            f"✅ Канал-получатель '{name}' удален!",
            reply_markup=create_main_keyboard()
        )

async def show_main_menu(query):
    """Показать главное меню"""
    await query.edit_message_text(
        "🤖 *Главное меню*\n\nВыберите действие:",
        reply_markup=create_main_keyboard(),
        parse_mode='Markdown'
    )

async def show_channels_list(query):
    """Показать список каналов"""
    if not channels_data['sources'] and not channels_data['destinations']:
        text = "📭 *Каналы не добавлены*"
    else:
        text = "📋 *Ваши каналы*\n\n"
        
        if channels_data['sources']:
            text += "📥 *Источники:*\n"
            for channel_id, name in channels_data['sources'].items():
                text += f"• {name} (`{channel_id}`)\n"
        
        if channels_data['destinations']:
            text += "\n📤 *Получатели:*\n"
            for channel_id, name in channels_data['destinations'].items():
                text += f"• {name} (`{channel_id}`)\n"
        
        if channels_data['mapping']:
            text += "\n🔗 *Активные связи:*\n"
            for source_id, dest_id in channels_data['mapping'].items():
                source_name = channels_data['sources'].get(source_id, "?")
                dest_name = channels_data['destinations'].get(dest_id, "?")
                text += f"• {source_name} → {dest_name}\n"
    
    await query.edit_message_text(
        text,
        reply_markup=create_main_keyboard(),
        parse_mode='Markdown'
    )

async def show_remove_menu(query):
    """Показать меню удаления"""
    await query.edit_message_text(
        "🗑️ *Удаление каналов*\n\nВыберите тип канала:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📥 Источники", callback_data="remove_source")],
            [InlineKeyboardButton("📤 Получатели", callback_data="remove_dest")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")]
        ]),
        parse_mode='Markdown'
    )

async def handle_forwarded_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик пересланных сообщений для добавления каналов"""
    if update.effective_user.id != MY_ID:
        return
    
    if not update.message.forward_from_chat:
        return
    
    waiting_for = context.user_data.get('waiting')
    channel_id = update.message.forward_from_chat.id
    channel_name = update.message.forward_from_chat.title
    
    try:
        # Получаем информацию о канале через Telethon
        entity = await client.get_entity(channel_id)
        
        if waiting_for == 'source':
            channels_data['sources'][channel_id] = channel_name
            await update.message.reply_text(
                f"✅ *Канал-источник добавлен!*\n\n"
                f"📥 {channel_name}\n"
                f"🆔 `{channel_id}`\n\n"
                f"Теперь добавьте канал-получатель и свяжите их.",
                reply_markup=create_main_keyboard(),
                parse_mode='Markdown'
            )
        
        elif waiting_for == 'destination':
            channels_data['destinations'][channel_id] = channel_name
            await update.message.reply_text(
                f"✅ *Канал-получатель добавлен!*\n\n"
                f"📤 {channel_name}\n"
                f"🆔 `{channel_id}`",
                reply_markup=create_main_keyboard(),
                parse_mode='Markdown'
            )
        
        context.user_data.pop('waiting', None)
        
    except Exception as e:
        await update.message.reply_text(
            f"❌ Ошибка: {str(e)}\n\nУбедитесь, что бот добавлен в канал и имеет права на чтение.",
            reply_markup=create_main_keyboard()
        )

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    if update.effective_user.id != MY_ID:
        return
    
    waiting_for = context.user_data.get('waiting')
    
    if waiting_for == 'forward_count':
        try:
            count = int(update.message.text)
            source_id = context.user_data.get('forward_source')
            
            if source_id and source_id in channels_data['mapping']:
                dest_id = channels_data['mapping'][source_id]
                
                # Пересылаем сообщения через Telethon
                await forward_last_messages(source_id, dest_id, count)
                
                await update.message.reply_text(
                    f"✅ Успешно переслано {count} сообщений!\n\n"
                    f"Из: {channels_data['sources'][source_id]}\n"
                    f"В: {channels_data['destinations'][dest_id]}",
                    reply_markup=create_main_keyboard()
                )
            else:
                await update.message.reply_text(
                    "❌ Сначала свяжите каналы!",
                    reply_markup=create_main_keyboard()
                )
            
            context.user_data.pop('waiting', None)
            context.user_data.pop('forward_source', None)
            
        except ValueError:
            await update.message.reply_text("❌ Введите число!")
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка: {str(e)}")

async def setup_event_handlers():
    """Настройка обработчиков событий для отслеживания новых сообщений"""
    # Удаляем старые обработчики
    client.remove_event_handlers()
    
    # Добавляем обработчики для каждого канала-источника
    source_channels = list(channels_data['sources'].keys())
    if source_channels:
        @client.on(events.NewMessage(chats=source_channels))
        async def handler(event):
            await handle_new_message(event)

async def handle_new_message(event):
    """Обработчик новых сообщений в каналах-источниках"""
    try:
        source_channel_id = event.chat_id
        
        if source_channel_id in channels_data['mapping']:
            dest_channel_id = channels_data['mapping'][source_channel_id]
            
            # Пересылаем сообщение
            await client.forward_messages(dest_channel_id, event.message)
            
            logger.info(f"📨 Переслано сообщение из {channels_data['sources'][source_channel_id]} в {channels_data['destinations'][dest_channel_id]}")
            
    except Exception as e:
        logger.error(f"❌ Ошибка пересылки: {e}")

async def forward_last_messages(source_id, dest_id, count):
    """Переслать последние сообщения"""
    try:
        # Получаем последние сообщения
        messages = await client.get_messages(source_id, limit=count)
        
        # Пересылаем в обратном порядке (от старых к новым)
        for message in reversed(messages):
            try:
                await client.forward_messages(dest_id, message)
                await asyncio.sleep(1)  # Задержка между сообщениями
            except Exception as e:
                logger.error(f"Ошибка при пересылке сообщения: {e}")
        
        logger.info(f"✅ Переслано {len(messages)} сообщений из {source_id} в {dest_id}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при получении сообщений: {e}")
        raise

async def main():
    """Основная функция"""
    # Инициализируем Telethon
    await initialize_telethon()
    
    # Настраиваем обработчики событий
    await setup_event_handlers()
    
    # Создаем бота
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(
        filters.FORWARDED & filters.Chat(chat_id=MY_ID),
        handle_forwarded_message
    ))
    application.add_handler(MessageHandler(
        filters.TEXT & filters.Chat(chat_id=MY_ID),
        handle_text_message
    ))
    
    # Запускаем бота
    logger.info("🤖 Бот запущен и готов к работе!")
    await application.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
