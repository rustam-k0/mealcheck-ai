from __future__ import annotations

TEXTS = {
 "EN": {
  "BTN_ADD":"➕ Add meal", "BTN_TODAY":"📅 Today", "BTN_EDIT_LAST":"✏️ Edit last entry", "BTN_DELETE_LAST":"🗑 Delete last entry",
  "BTN_SETTINGS":"⚙️ Settings", "BTN_NEW":"🆕 New analysis", "BTN_LANG":"🌐 Language / Язык", "BTN_MODEL":"🤖 Model",
  "WELCOME":"Hi! I’m BiteMate 🍽\n\nSend a food photo or describe your meal in text or voice. I’ll confirm the items first, then estimate calories and macros.",
  "CHOOSE_LANG":"Choose your language / Выберите язык:", "LANG_SET":"English selected 🇬🇧", "INVALID_LANG":"Please choose a language below.",
  "ADD_PROMPT":"Send a food photo, text description, or voice message.", "NEW_DIALOG":"The unconfirmed analysis was cleared. Your diary is unchanged.",
  "SETTINGS_TEXT":"Settings. Choose the interface language. BiteMate selects the best model automatically.", "MODEL_PROMPT":"Choose an allowed model:", "MODEL_SET":"Model selected: {model}",
  "RECOGNIZED":"I see:\n{items}\n\nIs this correct? You can send a correction, for example: “rice 120 g, no sauce”.{questions}",
  "CORRECTION_PROMPT":"Send the corrected items or portions in one message.", "PROCESSING":"⏳ Analyzing…", "TRANSCRIBED":"🎙 I heard: {value}",
  "NO_VISION":"The selected model cannot analyze images. Choose a multimodal model in Settings → Model.",
  "NO_TRANSCRIPTION":"Voice transcription is not configured. Please describe the meal in text; photos and text still work.",
  "BAD_VOICE":"I couldn’t confidently recognize a food description. Please repeat it or type it.", "ERR":"I couldn’t analyze this safely. Please try again.",
  "ESTIMATE":"Approximate nutrition estimate:\n{table}\n\nTotal: {kcal:.0f} kcal · P {protein:.1f} g · F {fat:.1f} g · C {carbs:.1f} g\nExpected error: ±{error:.0f}%\nUncertainty: {reasons}",
  "SAVED":"Saved to your diary.", "NOT_SAVED":"Not saved.", "TODAY_EMPTY":"There are no meals in today’s diary.",
  "TODAY":"Today: {count} meal(s) · {kcal:.0f} kcal · P {protein:.1f} g · F {fat:.1f} g · C {carbs:.1f} g",
  "NO_LAST":"There is no diary entry to change.", "CONFIRM_DELETE":"Delete the last diary entry?", "DELETED":"The last entry was deleted.",
  "ADMIN_DENIED":"This command is available to administrators only.",
  "CONFIRM_EDIT":"Edit the last entry? After confirmation, send its corrected composition.", "EDIT_SEND":"Send the corrected composition. The old entry will be kept until a new result is confirmed.",
 },
 "RU": {
  "BTN_ADD":"➕ Добавить прием пищи", "BTN_TODAY":"📅 Сегодня", "BTN_EDIT_LAST":"✏️ Исправить последнюю", "BTN_DELETE_LAST":"🗑 Удалить последнюю",
  "BTN_SETTINGS":"⚙️ Настройки", "BTN_NEW":"🆕 Новый анализ", "BTN_LANG":"🌐 Language / Язык", "BTN_MODEL":"🤖 Модель",
  "WELCOME":"Привет! Я BiteMate 🍽\n\nПришлите фото еды или опишите приём пищи текстом или голосом. Сначала я подтвержу состав, затем оценю калории и БЖУ.",
  "CHOOSE_LANG":"Choose your language / Выберите язык:", "LANG_SET":"Выбран русский язык 🇷🇺", "INVALID_LANG":"Выберите язык кнопкой ниже.",
  "ADD_PROMPT":"Пришлите фото еды, текстовое описание или голосовое сообщение.", "NEW_DIALOG":"Неподтвержденный анализ сброшен. Дневник не изменен.",
  "SETTINGS_TEXT":"Настройки. Выберите язык интерфейса. BiteMate сам подберёт модель под задачу.", "MODEL_PROMPT":"Выберите разрешенную модель:", "MODEL_SET":"Выбрана модель: {model}",
  "RECOGNIZED":"Я вижу:\n{items}\n\nВсё верно? Можно написать исправление, например: «рис 120 г, соуса не было».{questions}",
  "CORRECTION_PROMPT":"Одним сообщением напишите исправленный состав или порции.", "PROCESSING":"⏳ Анализирую…", "TRANSCRIBED":"🎙 Я услышал: {value}",
  "NO_VISION":"Выбранная модель не поддерживает изображения. Выберите мультимодальную модель в «Настройки» → «Модель».",
  "NO_TRANSCRIPTION":"Транскрибация голоса не настроена. Опишите еду текстом; фото и текст продолжают работать.",
  "BAD_VOICE":"Не удалось уверенно распознать описание еды. Повторите или напишите текстом.", "ERR":"Не удалось безопасно выполнить анализ. Попробуйте ещё раз.",
  "ESTIMATE":"Ориентировочная оценка пищевой ценности:\n{table}\n\nИтого: {kcal:.0f} ккал · Б {protein:.1f} г · Ж {fat:.1f} г · У {carbs:.1f} г\nОжидаемая погрешность: ±{error:.0f}%\nНеопределенность: {reasons}",
  "SAVED":"Запись сохранена в дневник.", "NOT_SAVED":"Запись не сохранена.", "TODAY_EMPTY":"Сегодня в дневнике пока нет приемов пищи.",
  "TODAY":"Сегодня: {count} прием(а) · {kcal:.0f} ккал · Б {protein:.1f} г · Ж {fat:.1f} г · У {carbs:.1f} г",
  "NO_LAST":"В дневнике нет записи для изменения.", "CONFIRM_DELETE":"Удалить последнюю запись дневника?", "DELETED":"Последняя запись удалена.",
  "ADMIN_DENIED":"Команда доступна только администраторам.",
  "CONFIRM_EDIT":"Исправить последнюю запись? После подтверждения отправьте новый состав.", "EDIT_SEND":"Отправьте исправленный состав. Старая запись сохранится, пока новый результат не подтвержден.",
 }
}

LEGACY_BUTTONS = {}
def text(lang: str, key: str, **values: object) -> str: return TEXTS[lang if lang in TEXTS else "EN"][key].format(**values)
def button_values(key: str) -> set[str]: return {x[key] for x in TEXTS.values()}
