"""Middleware проверки подписки на канал"""
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message
from aiogram.enums import ChatMemberStatus
from config import config
from keyboards import get_channel_keyboard


class ChannelMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        if event.from_user.id in config.ADMIN_IDS:
            return await handler(event, data)
        if hasattr(event, 'data') and event.data == "check_channel":
            return await handler(event, data)

        bot = data.get("bot")
        if not bot or not config.REQUIRED_CHANNEL_ID:
            return await handler(event, data)

        try:
            member = await bot.get_chat_member(config.REQUIRED_CHANNEL_ID, event.from_user.id)
            if member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.KICKED]:
                await event.answer(
                    "⚠️ <b>Для использования бота подпишитесь на канал!</b>\n\n"
                    "📢 " + config.REQUIRED_CHANNEL_LINK,
                    reply_markup=get_channel_keyboard(),
                    parse_mode="HTML"
                )
                return None
        except Exception:
            pass
        return await handler(event, data)
