"""Обработка удаления сообщений"""
from aiogram import Router, F
from aiogram.types import Message

router = Router()


@router.message(F.content_type.in_(["delete_chat_photo", "group_chat_created"]))
async def dummy(message: Message):
    pass
