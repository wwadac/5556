"""Callback-кнопки"""
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, FSInputFile
from aiogram.enums import ChatMemberStatus
from config import config
from database import db
from keyboards import (
    get_main_keyboard, get_dialogs_keyboard, get_dialog_actions_keyboard,
    get_payment_keyboard, get_channel_keyboard, get_back_keyboard
)
from utils import format_dt, time_left, build_chat_export
import os

router = Router()


@router.callback_query(F.data == "check_channel")
async def check_channel(callback: CallbackQuery, bot: Bot):
    try:
        member = await bot.get_chat_member(config.REQUIRED_CHANNEL_ID, callback.from_user.id)
        if member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.KICKED]:
            await callback.answer("❌ Вы не подписаны!", show_alert=True)
            return
        await callback.message.edit_text(
            "✅ Подписка подтверждена!",
            reply_markup=get_back_keyboard()
        )
        await callback.answer()
    except Exception:
        await callback.answer("Ошибка проверки", show_alert=True)


@router.callback_query(F.data == "my_dialogs")
async def my_dialogs(callback: CallbackQuery):
    dialogs = await db.get_dialogs(callback.from_user.id)
    if not dialogs:
        await callback.message.edit_text(
            "📭 <b>Переписок пока нет.</b>\n\nКак только кто-то напишет вам — диалог появится здесь.",
            reply_markup=get_back_keyboard(),
            parse_mode="HTML"
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        f"📨 <b>Мои переписки</b> ({len(dialogs)})",
        reply_markup=get_dialogs_keyboard(dialogs),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("dialog:"))
async def dialog_detail(callback: CallbackQuery):
    chat_id = int(callback.data.split(":")[1])
    dialog = await db.get_dialog(callback.from_user.id, chat_id)
    if not dialog:
        await callback.answer("Диалог не найден", show_alert=True)
        return

    stats = await db.get_chat_stats(callback.from_user.id, chat_id)
    name = dialog.get("peer_name") or dialog.get("peer_username") or "Unknown"
    username = f"@{dialog['peer_username']}" if dialog.get("peer_username") else ""

    text = (
        f"💬 <b>{name}</b> {username}\n"
        f"🆔 <code>{dialog['peer_id']}</code>\n\n"
        f"📊 <b>Статистика чата:</b>\n"
        f"• Всего сообщений: <b>{stats['total']}</b>\n"
        f"• Удалено: <b>{stats['deleted']}</b>\n"
        f"• Отредактировано: <b>{stats['edited']}</b>\n\n"
        f"🕐 Последнее: {format_dt(dialog.get('last_message_at'))}"
    )

    await callback.message.edit_text(
        text,
        reply_markup=get_dialog_actions_keyboard(chat_id),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("download:"))
async def download_chat(callback: CallbackQuery):
    chat_id = int(callback.data.split(":")[1])
    dialog = await db.get_dialog(callback.from_user.id, chat_id)
    if not dialog:
        await callback.answer("Диалог не найден", show_alert=True)
        return

    messages = await db.get_chat_messages(callback.from_user.id, chat_id)
    if not messages:
        await callback.answer("Сообщений нет", show_alert=True)
        return

    name = dialog.get("peer_name") or dialog.get("peer_username") or f"chat_{chat_id}"
    safe_name = "".join(c for c in name if c.isalnum() or c in " _-").strip() or "chat"

    content = build_chat_export(messages, name)
    filename = f"/tmp/chat_{safe_name}_{chat_id}.txt"

    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)

    await callback.message.answer_document(
        document=FSInputFile(filename),
        caption=f"📥 <b>Экспорт чата:</b> {name}",
        parse_mode="HTML"
    )

    os.remove(filename)
    await callback.answer("✅ Чат экспортирован!")


@router.callback_query(F.data == "subscription")
async def show_subscription(callback: CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    is_sub = await db.is_subscribed(callback.from_user.id)

    if is_sub:
        if user.get("trial_until") and time_left(user["trial_until"]) != "Истекла":
            text = f"🎁 <b>Триал активен!</b>\n\nОсталось: {time_left(user['trial_until'])}"
        else:
            text = (
                f"✅ <b>Подписка активна!</b>\n\n"
                f"До: {format_dt(user.get('subscribed_until'))}\n"
                f"Осталось: {time_left(user.get('subscribed_until'))}"
            )
        await callback.message.edit_text(text, reply_markup=get_back_keyboard(), parse_mode="HTML")
    else:
        code = user.get("payment_code", "0000") if user else "0000"
        text = (
            f"💳 <b>Оплата подписки</b>\n\n"
            f"Стоимость: <b>150₽</b>\n"
            f"Период: <b>90 дней</b>\n\n"
            f"1. Переведите <b>150₽</b> на карту Сбер:\n"
            f"   <code>{config.ADMIN_SBER_CARD}</code>\n"
            f"2. В комментарии укажите код: <b>{code}</b>\n"
            f"3. Отправьте скриншот боту\n\n"
            f"⚠️ Без кода платёж не засчитается!"
        )
        await callback.message.edit_text(
            text, reply_markup=get_payment_keyboard(code), parse_mode="HTML"
        )
    await callback.answer()


@router.callback_query(F.data == "new_code")
async def new_code(callback: CallbackQuery):
    code = await db.create_payment(callback.from_user.id)
    text = (
        f"💳 <b>Оплата подписки</b>\n\n"
        f"Стоимость: <b>150₽</b>\n"
        f"Период: <b>90 дней</b>\n\n"
        f"1. Переведите <b>150₽</b> на карту Сбер:\n"
        f"   <code>{config.ADMIN_SBER_CARD}</code>\n"
        f"2. В комментарии укажите код: <b>{code}</b>\n"
        f"3. Отправьте скриншот боту\n\n"
        f"⚠️ Без кода платёж не засчитается!"
    )
    await callback.message.edit_text(text, reply_markup=get_payment_keyboard(code), parse_mode="HTML")
    await callback.answer("🔄 Новый код!")


@router.callback_query(F.data.startswith("screenshot:"))
async def request_screenshot(callback: CallbackQuery):
    code = callback.data.split(":")[1]
    await callback.message.answer(
        f"📤 <b>Отправьте скриншот перевода</b>\n\nКод: <code>{code}</code>",
        parse_mode="HTML"
    )
    await callback.answer()
