"""Админ-панель"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from config import config
from database import db
from keyboards import get_admin_keyboard, get_verify_keyboard
from utils import format_dt
from datetime import datetime, timedelta

router = Router()


@router.message(F.photo)
async def handle_screenshot(message: Message):
    user = await db.get_user(message.from_user.id)
    if not user:
        return

    code = user.get("payment_code", "")
    payment = await db.get_payment_by_code(code)
    if not payment or payment["status"] not in ["pending", "waiting_verify"]:
        code = await db.create_payment(message.from_user.id)
        payment = await db.get_payment_by_code(code)

    if payment:
        await db.add_screenshot(payment["id"], message.photo[-1].file_id)

        for admin_id in config.ADMIN_IDS:
            try:
                await message.bot.send_photo(
                    chat_id=admin_id,
                    photo=message.photo[-1].file_id,
                    caption=(
                        "💳 <b>Новый платёж!</b>\n\n"
                        f"👤 {message.from_user.full_name}\n"
                        f"🆔 <code>{message.from_user.id}</code>\n"
                        f"🔢 Код: <code>{code}</code>\n"
                        f"💰 {config.SUBSCRIPTION_PRICE}₽"
                    ),
                    reply_markup=get_verify_keyboard(payment["id"], message.from_user.id),
                    parse_mode="HTML"
                )
            except Exception:
                pass

        await message.answer(
            "📤 <b>Скриншот получен!</b>\n\nПлатёж отправлен на проверку админу.",
            parse_mode="HTML"
        )


@router.callback_query(F.data == "admin_panel")
async def admin_panel(callback: CallbackQuery):
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    await callback.message.edit_text(
        "🔐 <b>Админ-панель</b>",
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    stats = await db.get_stats()
    users = await db.get_all_users()
    new_24h = sum(
        1 for u in users
        if u.get("joined_at") and datetime.fromisoformat(u["joined_at"]) > datetime.now() - timedelta(hours=24)
    )

    text = (
        "📊 <b>Статистика</b>\n\n"
        f"👥 Всего: <b>{stats['total']}</b>\n"
        f"✅ Активных: <b>{stats['active']}</b>\n"
        f"📅 Новых за 24ч: <b>{new_24h}</b>"
    )

    await callback.message.edit_text(text, reply_markup=get_admin_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_users")
async def admin_users(callback: CallbackQuery):
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    users = await db.get_all_users()
    text = f"👥 <b>Пользователей: {len(users)}</b>\n\n"
    for u in users[:30]:
        name = u.get("first_name") or u.get("username") or "Unknown"
        sub = "✅" if await db.is_subscribed(u["user_id"]) else "❌"
        text += f"{sub} {name} — <code>{u['user_id']}</code>\n"

    await callback.message.edit_text(text, reply_markup=get_admin_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_verify")
async def admin_verify(callback: CallbackQuery):
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    await callback.message.edit_text(
        "✅ Платежи приходят автоматически.\nИспользуйте кнопки под скриншотами.",
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("verify_pay:"))
async def verify_pay(callback: CallbackQuery):
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    parts = callback.data.split(":")
    payment_id = int(parts[1])
    user_id = int(parts[2])

    await db.verify_payment(payment_id)
    await db.activate_subscription(user_id)

    try:
        await callback.bot.send_message(
            user_id,
            "✅ <b>Платёж подтверждён!</b>\n\nПодписка активирована на 90 дней. 🎉",
            parse_mode="HTML"
        )
    except Exception:
        pass

    await callback.message.edit_caption(
        caption=callback.message.caption + "\n\n✅ <b>ПОДТВЕРЖДЕНО</b>",
        parse_mode="HTML"
    )
    await callback.answer("✅ Подтверждено!")


@router.callback_query(F.data.startswith("reject_pay:"))
async def reject_pay(callback: CallbackQuery):
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    parts = callback.data.split(":")
    payment_id = int(parts[1])
    user_id = int(parts[2])

    try:
        await callback.bot.send_message(
            user_id,
            "❌ <b>Платёж отклонён.</b>\n\nПроверьте правильность перевода.",
            parse_mode="HTML"
        )
    except Exception:
        pass

    await callback.message.edit_caption(
        caption=callback.message.caption + "\n\n❌ <b>ОТКЛОНЕНО</b>",
        parse_mode="HTML"
    )
    await callback.answer("❌ Отклонено")
