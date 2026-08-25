"""Middleware проверки подписки"""
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message
from database import db
from keyboards import get_payment_keyboard


class SubscriptionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        if event.text and event.text.startswith(("/start", "/help")):
            return await handler(event, data)
        if hasattr(event, 'data') and event.data and event.data.startswith(("subscription", "screenshot", "new_code", "check_channel", "back_main")):
            return await handler(event, data)

        user = await db.get_user(event.from_user.id)
        if not user:
            return await handler(event, data)

        is_sub = await db.is_subscribed(event.from_user.id)
        if not is_sub:
            code = user.get("payment_code", "0000")
            await event.answer(
                "⏰ <b>Бесплатный период закончился!</b>\n\n"
                "Для дальнейшего использования оплатите подписку.\n\n"
                "💳 <b>Стоимость:</b> 150₽ на 90 дней",
                reply_markup=get_payment_keyboard(code),
                parse_mode="HTML"
            )
            return None
        return await handler(event, data)
