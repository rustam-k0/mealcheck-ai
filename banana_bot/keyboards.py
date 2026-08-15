from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from banana_bot.i18n import TEXTS

def main_keyboard(lang: str) -> ReplyKeyboardMarkup:
    t=TEXTS[lang]; rows=[[t["BTN_ADD"],t["BTN_TODAY"]],[t["BTN_SETTINGS"]]]
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=x) for x in row] for row in rows],resize_keyboard=True)
def language_keyboard() -> ReplyKeyboardMarkup: return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="English 🇬🇧"),KeyboardButton(text="Русский 🇷🇺")]],resize_keyboard=True,one_time_keyboard=True)
def settings_keyboard(lang: str) -> ReplyKeyboardMarkup:
    t=TEXTS[lang]; return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=t["BTN_LANG"])],[KeyboardButton(text=t["BTN_NEW"])]],resize_keyboard=True)
def model_keyboard(models: tuple[str,...]) -> InlineKeyboardMarkup: return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=x,callback_data=f"model:{i}")] for i,x in enumerate(models)])
def confirmation_keyboard(lang: str) -> InlineKeyboardMarkup:
    labels=("✅ Всё верно","✏️ Исправить","✖️ Отменить") if lang=="RU" else ("✅ Correct","✏️ Correct it","✖️ Cancel")
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=labels[0],callback_data="meal:confirm")],[InlineKeyboardButton(text=labels[1],callback_data="meal:correct"),InlineKeyboardButton(text=labels[2],callback_data="meal:cancel")]])
def diary_keyboard(lang: str) -> InlineKeyboardMarkup:
    yes,no=(("💾 Сохранить","Не сохранять") if lang=="RU" else ("💾 Save","Don't save")); return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=yes,callback_data="diary:save"),InlineKeyboardButton(text=no,callback_data="diary:skip")]])
def yes_no_keyboard(prefix: str,lang: str) -> InlineKeyboardMarkup:
    yes,no=(("Да","Нет") if lang=="RU" else ("Yes","No")); return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=yes,callback_data=f"{prefix}:yes"),InlineKeyboardButton(text=no,callback_data=f"{prefix}:no")]])
def diary_manage_keyboard(lang: str) -> InlineKeyboardMarkup:
    edit,delete=(("✏️ Исправить последнюю","🗑 Удалить последнюю") if lang=="RU" else ("✏️ Edit last","🗑 Delete last"))
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=edit,callback_data="manage:edit"),InlineKeyboardButton(text=delete,callback_data="manage:delete")]])
