from aiogram.fsm.state import State, StatesGroup

class RegistrationFSM(StatesGroup):
    waiting_captcha = State()
    entering_minecraft_nick = State()

class TaskFSM(StatesGroup):
    waiting_screenshot = State()

class WithdrawFSM(StatesGroup):
    changing_nick = State()

class SupportFSM(StatesGroup):
    chatting = State()

class AdminFSM(StatesGroup):
    replying_support = State()