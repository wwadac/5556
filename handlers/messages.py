"""Сохранение сообщений — Business Mode + Forward Fallback"""
import logging
from aiogram import Router, F, Bot
from aiogram.types import Message
from database import db

router = Router()
logger = logging.getLogger(__name__)

_business_owners = {}


def get_media_info(message: Message):
    if message.photo:
        return "photo", message.photo[-1].file_id
    if message.video:
        return "video", message.video.file_id
    if message.audio:
        return "audio", message.audio.file_id
    if message.voice:
        return "voice", message.voice.file_id
    if message.video_note:
        return "video_note", message.video_note.file_id
    if message.document:
        return "document", message.document.file_id
    if message.sticker:
        return "sticker", message.sticker.file_id
    if message.animation:
        return "animation", message.animation.file_id
    return None, None


async def resolve_owner_id(bot: Bot, message: Message) -> int:
    """Определяет владельца (для Business Mode)"""
    bc_id = message.business_connection_id
    if bc_id:
        if bc_id not in _business_owners:
            try:
                bc = await bot.get_business_connection(bc_id)
                _business_owners[bc_id] = bc.user.id
                logger.info(f"Business connection: {bc_id} -> user {bc.user.id}")
            except Exception as e:
                logger.warning(f"Failed to get business connection: {e}")
                return message.from_user.id
        return _business_owners[bc_id]
    return message.from_user.id


async def save_any_message(message: Message, bot: Bot):
    """Сохраняет любое сообщение"""
    owner_id = await resolve_owner_id(bot, message)

    # Если это пересланное сообщение (fallback режим)
    if message.forward_from or message.forward_sender_name or message.forward_date:
        # Определяем "чат" как оригинального отправителя
        if message.forward_from:
            peer_id = message.forward_from.id
            peer_name = message.forward_from.full_name or "Unknown"
            peer_username = message.forward_from.username or ""
        else:
            peer_id = message.chat.id  # fallback
            peer_name = message.forward_sender_name or "Unknown"
            peer_username = ""

        chat_id = peer_id  # Группируем по ID собеседника

        # Сохраняем диалог
        await db.add_or_update_dialog(
            owner_id=owner_id,
            chat_id=chat_id,
            peer_id=peer_id,
            peer_name=peer_name,
            peer_username=peer_username
        )

        media_type, media_file_id = get_media_info(message)
        text = message.text or message.caption

        await db.save_message(
            owner_id=owner_id,
            chat_id=chat_id,
            message_id=message.message_id,
            from_user_id=peer_id,
            from_user_name=peer_name,
            text=text,
            media_type=media_type,
            media_file_id=media_file_id,
            caption=message.caption,
            is_outgoing=False
        )
        logger.info(f"[FORWARD] Saved from {peer_name} for owner {owner_id}")
        return

    # Обычное сообщение (Business Mode или ЛС с ботом)
    chat_id = message.chat.id
    peer_id = chat_id
    peer_name = message.chat.first_name or message.chat.title or "Unknown"
    peer_username = message.chat.username or ""

    from_user_id = message.from_user.id
    from_user_name = message.from_user.full_name or "Unknown"
    is_outgoing = (from_user_id == owner_id)

    # Если собеседник пишет (не owner), обновляем peer_name
    if not is_outgoing:
        peer_name = message.from_user.full_name or peer_name
        peer_username = message.from_user.username or peer_username

    media_type, media_file_id = get_media_info(message)
    text = message.text or message.caption

    await db.add_or_update_dialog(
        owner_id=owner_id,
        chat_id=chat_id,
        peer_id=peer_id,
        peer_name=peer_name,
        peer_username=peer_username
    )

    await db.save_message(
        owner_id=owner_id,
        chat_id=chat_id,
        message_id=message.message_id,
        from_user_id=from_user_id,
        from_user_name=from_user_name,
        text=text,
        media_type=media_type,
        media_file_id=media_file_id,
        caption=message.caption,
        is_outgoing=is_outgoing
    )
    logger.info(f"[MSG] Saved from {from_user_name} in chat {chat_id} for owner {owner_id}")


@router.message()
async def handle_any(message: Message, bot: Bot):
    """Ловит ВСЕ сообщения (кроме тех, что перехвачены выше)"""
    try:
        await save_any_message(message, bot)
    except Exception as e:
        logger.error(f"Error saving message: {e}")
