"""Старт и профиль"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from config import config
from database import db
from keyboards import get_main_keyboard, get_back_keyboard
from utils import format_dt, time_left

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    user = message.from_user
    await db.add_user(user.id, user.username or "", user.first_name or "", user.last_name or "")
    is_new = not await db.get_user(user.id)

    if is_new:
        await message.answer(
            """👋 <b>Бот подключён!</b>

Теперь я сохраняю все ваши переписки автоматически.
Бесплатный период: <b>16 часов</b>.

📨 <b>Мои переписки</b> — список всех диалогов
📊 <b>Мой профиль</b> — статистика
💾 Чаты можно скачать даже если их удалили!""",
            parse_mode="HTML"
        )

    is_admin = user.id in config.ADMIN_IDS
    await message.answer(
        "🏠 <b>Главное меню</b>",
        reply_markup=get_main_keyboard(is_admin),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "my_profile")
async def my_profile(callback: CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    if not user:
        await callback.answer("Ошибка", show_alert=True)
        return

    total_dialogs = await db.get_total_dialogs(callback.from_user.id)
    total_messages = await db.get_total_messages(callback.from_user.id)
    is_sub = await db.is_subscribed(callback.from_user.id)

    if is_sub:
        if user.get("trial_until") and time_left(user["trial_until"]) != "Истекла":
            sub_text = f"🎁 Триал: {time_left(user['trial_until'])}"
        else:
            sub_text = f"✅ Подписка до: {format_dt(user.get('subscribed_until'))}"
    else:
        sub_text = "❌ Подписка неактивна"

    text = f"""📊 <b>Ваш профиль</b>

👤 {user.get('first_name') or user.get('username')}
🆔 <code>{user['user_id']}</code>

💬 <b>Чатов:</b> {total_dialogs}
📝 <b>Сообщений:</b> {total_messages}

{sub_text}"""

    await callback.message.edit_text(text, reply_markup=get_back_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "back_main")
async def back_main(callback: CallbackQuery):
    is_admin = callback.from_user.id in config.ADMIN_IDS
    await callback.message.edit_text(
        "🏠 <b>Главное меню</b>",
        reply_markup=get_main_keyboard(is_admin),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "help")
async def show_help(callback: CallbackQuery):
    text = """❓ <b>Помощь</b>

<b>Как это работает?</b>
Бот подключён к вашему аккаунту через Business Mode. Все сообщения из ваших ЛС сохраняются автоматически.

<b>Мои переписки</b> — список всех диалогов
<b>Скачать чат</b> — экспорт в txt файл
<b>Даже удалённые чаты</b> остаются в боте!

⏰ Бесплатный период: 16 часов
💳 Подписка: 150₽ / 90 дней"""

    await callback.message.edit_text(text, reply_markup=get_back_keyboard(), parse_mode="HTML")
    await callback.answer()
