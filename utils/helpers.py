"""Вспомогательные функции"""
from datetime import datetime


def format_dt(dt) -> str:
    if dt is None:
        return "—"
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except ValueError:
            return dt
    return dt.strftime("%d.%m.%Y %H:%M:%S")


def time_left(dt) -> str:
    if dt is None:
        return "Не активна"
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except ValueError:
            return "Ошибка"
    diff = dt - datetime.now()
    if diff.total_seconds() <= 0:
        return "Истекла"
    days = diff.days
    hours = diff.seconds // 3600
    mins = (diff.seconds % 3600) // 60
    parts = []
    if days > 0:
        parts.append(f"{days}д")
    if hours > 0:
        parts.append(f"{hours}ч")
    if mins > 0 and days == 0:
        parts.append(f"{mins}м")
    return " ".join(parts) if parts else "<1м"


def build_chat_export(messages: list, peer_name: str) -> str:
    """Собирает txt файл с историей чата"""
    lines = [
        f"📁 Экспорт переписки: {peer_name}",
        "=" * 50,
        ""
    ]
    for msg in messages:
        dt = format_dt(msg.get("created_at"))
        name = msg.get("from_user_name") or "Unknown"
        text = msg.get("text") or msg.get("caption") or ""
        media = msg.get("media_type")
        deleted = " [УДАЛЕНО]" if msg.get("is_deleted") else ""
        edited = " [РЕДАКТИРОВАНО]" if msg.get("edited_at") else ""
        prefix = f"[{dt}] {name}:"
        if media:
            text = f"[{media.upper()}] {text}"
        lines.append(f"{prefix}{deleted}{edited}")
        if text:
            lines.append(text)
        lines.append("")
    return "\n".join(lines)
