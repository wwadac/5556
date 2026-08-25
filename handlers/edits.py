"""Обработка редактирования сообщений"""
from aiogram import Router, F
from aiogram.types import Message
from database import db
from utils import format_dt
import logging

router = Router()
logger = logging.getLogger(__name__)

_business_owners = {}


async def resolve_owner_id(bot, message: Message) -> int:
    bc_id = message.business_connection_id
    if bc_id:
        if bc_id not in _business_owners:
            try:
                from aiogram import Bot
                bc = await bot.get_business_connection(bc_id)
                _business_owners[bc_id] = bc.user.id
            except Exception:
                return message.from_user.id
        return _business_owners[bc_id]
    return message.from_user.id


@router.edited_message()
async def handle_edited(message: Message, bot):
    owner_id = await resolve_owner_id(bot, message)
    messages = await db.get_chat_messages(owner_id, message.chat.id)
    old_text = None
    for m in messages:
        if m["message_id"] == message.message_id:
            old_text = m["text"] or m["caption"] or "[медиа]"
            break

    new_text = message.text or message.caption or "[медиа]"
    if old_text and old_text != new_text:
        await db.save_edit(
            message_id=message.message_id,
            chat_id=message.chat.id,
            owner_id=owner_id,
            old_text=old_text,
            new_text=new_text
        )
        logger.info(f"[EDIT] Saved edit for message {message.message_id}")
