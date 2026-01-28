
import asyncio
import aiosqlite
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatAction
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

DB = "settings.db"
OWNER_USER_ID = 8593061718    # OPTIONAL: можно заранее указать ваш user_id, иначе бот запомнит при первой связке.

# --- DB helpers
async def init_db():
    async with aiosqlite.connect(DB) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS chat_settings(
                chat_id INTEGER PRIMARY KEY,
                greeting_text TEXT DEFAULT 'приветик',
                sticker_file_id TEXT,
                followup_text TEXT DEFAULT 'Спасибо за ответ! Чем могу помочь?',
                delay_seconds INTEGER DEFAULT 20,
                enabled INTEGER DEFAULT 1
            )
        """)
        await db.commit()

async def get_settings(chat_id):
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT greeting_text, sticker_file_id, followup_text, delay_seconds, enabled FROM chat_settings WHERE chat_id = ?", (chat_id,))
        row = await cur.fetchone()
        if not row:
            await db.execute("INSERT INTO chat_settings(chat_id) VALUES(?)", (chat_id,))
            await db.commit()
            return {'greeting_text':'приветик','sticker_file_id':None,'followup_text':'Спасибо за ответ! Чем могу помочь?','delay_seconds':20,'enabled':1}
        return {'greeting_text':row[0], 'sticker_file_id':row[1], 'followup_text':row[2], 'delay_seconds':row[3], 'enabled':row[4]}

async def set_field(chat_id, field, value):
    async with aiosqlite.connect(DB) as db:
        await db.execute(f"UPDATE chat_settings SET {field} = ? WHERE chat_id = ?", (value, chat_id))
        await db.commit()

# --- Handlers
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_chat.send_message("Привет! Я бот для автоматических ответов в Business Mode. Используйте /settings для настройки.")

async def settings_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    s = await get_settings(chat_id)
    kb = [
        [InlineKeyboardButton("Изменить привет", callback_data="set_greeting")],
        [InlineKeyboardButton("Установить стикер (отправьте стикер после нажатия)", callback_data="set_sticker")],
        [InlineKeyboardButton("Изменить follow-up текст", callback_data="set_followup")],
        [InlineKeyboardButton("Задать задержку (сек)", callback_data="set_delay")],
        [InlineKeyboardButton("Вкл/Выкл автоответ", callback_data="toggle_enabled")]
    ]
    txt = f"Текущие настройки:\nПривет: {s['greeting_text']}\nСтикер: {'есть' if s['sticker_file_id'] else 'не задан'}\nFollow-up: {s['followup_text']}\nЗадержка (сек): {s['delay_seconds']}\nВключено: {bool(s['enabled'])}"
    await update.effective_chat.send_message(txt, reply_markup=InlineKeyboardMarkup(kb))

async def callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    cd = q.data
    chat_id = q.message.chat_id
    if cd == "set_greeting":
        await q.message.reply_text("Отправьте мне новый привет (обычный текст).")
        context.user_data['awaiting'] = ('greeting', chat_id)
    elif cd == "set_sticker":
        await q.message.reply_text("Отправьте сюда нужный стикер (как сообщение боту).")
        context.user_data['awaiting'] = ('sticker', chat_id)
    elif cd == "set_followup":
        await q.message.reply_text("Отправьте текст для follow-up (после ответа собеседника).")
        context.user_data['awaiting'] = ('followup', chat_id)
    elif cd == "set_delay":
        await q.message.reply_text("Отправьте задержку в секундах (например 20).")
        context.user_data['awaiting'] = ('delay', chat_id)
    elif cd == "toggle_enabled":
        s = await get_settings(chat_id)
        new = 0 if s['enabled'] else 1
        await set_field(chat_id, 'enabled', new)
        await q.message.reply_text(f"Автоответ {'включён' if new else 'выключен'}.")

async def text_or_sticker_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # This handler processes messages sent to the bot (for setting config items)
    if 'awaiting' not in context.user_data:
        return
    kind, target_chat = context.user_data.pop('awaiting')
    if kind == 'greeting' and update.message.text:
        await set_field(target_chat, 'greeting_text', update.message.text)
        await update.message.reply_text("Привет сохранён.")
    elif kind == 'followup' and update.message.text:
        await set_field(target_chat, 'followup_text', update.message.text)
        await update.message.reply_text("Follow-up текст сохранён.")
    elif kind == 'delay' and update.message.text and update.message.text.isdigit():
        await set_field(target_chat, 'delay_seconds', int(update.message.text))
        await update.message.reply_text("Задержка сохранена.")
    elif kind == 'sticker' and update.message.sticker:
        fid = update.message.sticker.file_id
        await set_field(target_chat, 'sticker_file_id', fid)
        await update.message.reply_text("Стикер сохранён.")
    else:
        await update.message.reply_text("Неправильный формат сообщения. Попробуйте ещё раз.")

# --- Business message handler: main logic
async def business_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Реакция на любые business_message (включая исходящие от владельца и входящие от клиента).
    Логика:
      - если исходящее от владельца и текст в триггерах -> сразу отправляем greeting_text + sticker
      - если входящее от клиента (ответ) -> запускаем sendChatAction (typing) -> ждём delay -> отправляем followup_text
    """
    # update.business_message — объект Message (Bot API >= 7.x)
    bm = update.business_message  # python-telegram-bot предоставляет это поле в Update
    if not bm:
        return
    chat_id = bm.chat.id
    s = await get_settings(chat_id)
    if not s['enabled']:
        return

    # Try to extract business_connection_id from message or update
    business_connection_id = getattr(bm, 'business_connection_id', None) or getattr(update, 'business_connection', None)
    # Some libraries include connection info in update.business_connection or message.business_connection_id

    text = (bm.text or "").lower() if bm.text else ""
    # Simple triggers:
    triggers = ["привет", "приветик"]
    # Determine direction: if message is outgoing from business owner -> bm.from_user may be the owner; there is also bm.outgoing optional flag in library
    outgoing = getattr(bm, 'is_outgoing', False) or getattr(bm, 'outgoing', False) or (bm.from_user and getattr(bm.from_user, 'is_bot', False) == False and bm.from_user.id == OWNER_USER_ID)
    # NOTE: Depending on lib fields, adjust detection; best practice — set OWNER_USER_ID or read connection update to discover it.

    # CASE A: Вы (владелец) написали "привет" -> отправляем нужный текст + стикер
    if text in triggers and outgoing:
        # send text first:
        try:
            await context.bot.send_message(chat_id=chat_id,
                                           text=s['greeting_text'],
                                           api_kwargs={'business_connection_id': business_connection_id} if business_connection_id else None)
        except Exception as e:
            # fallback without api_kwargs (may be required in some setups)
            await context.bot.send_message(chat_id=chat_id, text=s['greeting_text'])
        # send sticker if set
        if s['sticker_file_id']:
            try:
                await context.bot.send_sticker(chat_id=chat_id, sticker=s['sticker_file_id'],
                                               api_kwargs={'business_connection_id': business_connection_id} if business_connection_id else None)
            except Exception:
                pass
        return

    # CASE B: клиент ответил -> показать 'typing', ждать delay, отправить followup
    # We decide it's an incoming message if not outgoing
    if not outgoing:
        # show typing
        try:
            await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING,
                                               api_kwargs={'business_connection_id': business_connection_id} if business_connection_id else None)
        except Exception:
            pass
        # wait configured delay (in seconds)
        delay = s['delay_seconds'] or 20
        await asyncio.sleep(delay)
        # send follow-up
        try:
            await context.bot.send_message(chat_id=chat_id, text=s['followup_text'],
                                           api_kwargs={'business_connection_id': business_connection_id} if business_connection_id else None)
        except Exception:
            await context.bot.send_message(chat_id=chat_id, text=s['followup_text'])

# --- Main
async def main():
    import os
    TOKEN = os.environ.get("8556723456:AAFw-r-WKOC4A1kNw9ovHBdVF0Cd08Fbk7E")
    if not TOKEN:
        print("Set BOT_TOKEN env var")
        return
    await init_db()
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("settings", settings_cmd))
    app.add_handler(CallbackQueryHandler(callback_query))
    # messages sent to bot (for setting sticker/text/etc)
    app.add_handler(MessageHandler(filters.ALL & filters.ChatType.PRIVATE, text_or_sticker_handler))
    # Business updates handler: register a generic handler and inspect update.business_message
    app.add_handler(MessageHandler(filters.ALL, business_message_handler))

    # polling (ok for testing). For production use webhook.
    print("Bot started (polling)")
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
