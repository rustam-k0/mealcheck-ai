from __future__ import annotations

TEXTS = {
 "EN": {
  "BTN_ADD":"➕ Add meal", "BTN_TODAY":"📅 Today", "BTN_EDIT_LAST":"✏️ Edit last entry", "BTN_DELETE_LAST":"🗑 Delete last entry",
  "BTN_SETTINGS":"⚙️ Settings", "BTN_NEW":"🆕 New analysis", "BTN_LANG":"🌐 Language / Язык", "BTN_MODEL":"🤖 Model",
  "WELCOME":"Hey! Send me a meal photo, text, or voice 👋",
  "CHOOSE_LANG":"Choose language / Выбери язык", "LANG_SET":"English it is 🇬🇧", "INVALID_LANG":"Choose a language below 👇",
  "ADD_PROMPT":"Send a photo, text, or voice 👇", "NEW_DIALOG":"Ready for a new meal ✨",
  "SETTINGS_TEXT":"What do you want to change?", "MODEL_PROMPT":"Choose a model:", "MODEL_SET":"Done: {model}",
  "RECOGNIZED":"{intro}\n{items}",
  "CORRECTION_PROMPT":"What should I change?", "PROCESSING":"⏳ One sec…", "TRANSCRIBED":"🎙 {value}",
  "NO_VISION":"I can’t read this photo. Try another one.",
  "NO_TRANSCRIPTION":"Voice isn’t available right now. Type it instead 🙌",
  "BAD_VOICE":"Didn’t catch that. Try again or type it.", "ERR":"Something went wrong. Try again 🙌",
  "STALE_MEAL":"This one is already closed. Use the latest meal.",
  "ESTIMATE":"{table}\n\n<b>{kcal:.0f} kcal</b> · P {protein:.1f} · F {fat:.1f} · C {carbs:.1f} g",
  "SAVED":"Saved ✅", "NOT_SAVED":"Okay, not saved", "TODAY_EMPTY":"Nothing logged today yet.",
  "TODAY":"Today: {count} · {kcal:.0f} kcal\nP {protein:.1f} · F {fat:.1f} · C {carbs:.1f} g",
  "NO_LAST":"Nothing to edit yet.", "CONFIRM_DELETE":"Delete the last meal?", "DELETED":"Deleted 🗑",
  "ADMIN_DENIED":"This action isn’t available.",
  "CONFIRM_EDIT":"Edit the last meal?", "EDIT_SEND":"Send the updated meal.",
 },
 "RU": {
  "BTN_ADD":"➕ Добавить прием пищи", "BTN_TODAY":"📅 Сегодня", "BTN_EDIT_LAST":"✏️ Исправить последнюю", "BTN_DELETE_LAST":"🗑 Удалить последнюю",
  "BTN_SETTINGS":"⚙️ Настройки", "BTN_NEW":"🆕 Новый анализ", "BTN_LANG":"🌐 Language / Язык", "BTN_MODEL":"🤖 Модель",
  "WELCOME":"Привет! Кидай фото еды, текст или голосовое 👋",
  "CHOOSE_LANG":"Choose language / Выбери язык", "LANG_SET":"Погнали на русском 🇷🇺", "INVALID_LANG":"Выбери язык кнопкой ниже 👇",
  "ADD_PROMPT":"Кидай фото, текст или голосовое 👇", "NEW_DIALOG":"Готов к новому приёму пищи ✨",
  "SETTINGS_TEXT":"Что хочешь поменять?", "MODEL_PROMPT":"Выбери модель:", "MODEL_SET":"Готово: {model}",
  "RECOGNIZED":"{intro}\n{items}",
  "CORRECTION_PROMPT":"Что поменять?", "PROCESSING":"⏳ Секунду…", "TRANSCRIBED":"🎙 {value}",
  "NO_VISION":"Не получилось прочитать фото. Попробуй другое.",
  "NO_TRANSCRIPTION":"Голосовые пока не работают. Напиши текстом 🙌",
  "BAD_VOICE":"Не расслышал. Повтори или напиши текстом.", "ERR":"Что-то пошло не так. Попробуй ещё раз 🙌",
  "STALE_MEAL":"Этот приём уже закрыт. Используй последнее сообщение.",
  "ESTIMATE":"{table}\n\n<b>{kcal:.0f} ккал</b> · Б {protein:.1f} · Ж {fat:.1f} · У {carbs:.1f} г",
  "SAVED":"Сохранил ✅", "NOT_SAVED":"Окей, не сохраняю", "TODAY_EMPTY":"Сегодня пока пусто.",
  "TODAY":"Сегодня: {count} · {kcal:.0f} ккал\nБ {protein:.1f} · Ж {fat:.1f} · У {carbs:.1f} г",
  "NO_LAST":"Пока нечего менять.", "CONFIRM_DELETE":"Удалить последний приём?", "DELETED":"Удалил 🗑",
  "ADMIN_DENIED":"Это действие недоступно.",
  "CONFIRM_EDIT":"Изменить последний приём?", "EDIT_SEND":"Пришли обновлённый состав.",
 }
}

def text(lang: str, key: str, **values: object) -> str: return TEXTS[lang if lang in TEXTS else "EN"][key].format(**values)
def button_values(key: str) -> set[str]: return {x[key] for x in TEXTS.values()}
