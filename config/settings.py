"""Конфигурация бота"""
import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    ADMIN_IDS: list[int] = field(default_factory=list)
    REQUIRED_CHANNEL_ID: int = int(os.getenv("REQUIRED_CHANNEL_ID", "0"))
    REQUIRED_CHANNEL_LINK: str = os.getenv("REQUIRED_CHANNEL_LINK", "")
    ADMIN_SBER_CARD: str = os.getenv("ADMIN_SBER_CARD", "")
    SUBSCRIPTION_PRICE: int = int(os.getenv("SUBSCRIPTION_PRICE", "150"))
    SUBSCRIPTION_DAYS: int = int(os.getenv("SUBSCRIPTION_DAYS", "90"))
    TRIAL_HOURS: int = int(os.getenv("TRIAL_HOURS", "16"))
    DB_PATH: str = os.getenv("DB_PATH", "database/bot.db")

    def __post_init__(self):
        admin_ids_str = os.getenv("ADMIN_IDS", "")
        if admin_ids_str:
            object.__setattr__(self, 'ADMIN_IDS', [int(x.strip()) for x in admin_ids_str.split(",")])


config = Config()
