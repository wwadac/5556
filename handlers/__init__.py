from .start import router as start_router
from .admin import router as admin_router
from .callbacks import router as callbacks_router
from .deleted import router as deleted_router
from .edits import router as edits_router
from .messages import router as messages_router

__all__ = [
    "start_router", "admin_router", "callbacks_router",
    "deleted_router", "edits_router", "messages_router"
]
