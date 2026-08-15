from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from banana_bot.config import AppConfig
from banana_bot.diary import DiaryRepository
from banana_bot.i18n import TEXTS, button_values, text
from banana_bot.keyboards import diary_manage_keyboard, language_keyboard, main_keyboard, model_keyboard, settings_keyboard, yes_no_keyboard
from banana_bot.memory import ConversationMemory
from banana_bot.states import BotStates


def build_common_router(config: AppConfig, memory: ConversationMemory, diary: DiaryRepository) -> Router:
    router=Router(name="common")
    @router.message(CommandStart())
    async def start(message:Message,state:FSMContext):
        lang=(await state.get_data()).get("lang"); await state.clear()
        if not lang: await state.set_state(BotStates.language); await message.answer(TEXTS["EN"]["CHOOSE_LANG"],reply_markup=language_keyboard()); return
        await state.update_data(lang=lang,selected_model=config.ai_vision_model); await message.answer(text(lang,"WELCOME"),reply_markup=main_keyboard(lang))
    @router.message(F.text.in_(button_values("BTN_LANG")))
    async def choose(message:Message,state:FSMContext): await state.set_state(BotStates.language); await message.answer(TEXTS["EN"]["CHOOSE_LANG"],reply_markup=language_keyboard())
    @router.message(BotStates.language,F.text.in_({"English 🇬🇧","Русский 🇷🇺"}))
    async def lang_selected(message:Message,state:FSMContext):
        lang="EN" if message.text.startswith("English") else "RU"; await state.set_state(None); await state.update_data(lang=lang,selected_model=config.ai_vision_model)
        await message.answer(text(lang,"WELCOME"),reply_markup=main_keyboard(lang))
    @router.message(BotStates.language)
    async def bad_lang(message:Message): await message.answer(TEXTS["EN"]["INVALID_LANG"]+" / "+TEXTS["RU"]["INVALID_LANG"],reply_markup=language_keyboard())
    @router.message(F.text.in_(button_values("BTN_NEW")))
    async def reset(message:Message,state:FSMContext):
        data=await state.get_data(); memory.clear(message.from_user.id); await state.clear(); await state.update_data(lang=data.get("lang","EN"),selected_model=data.get("selected_model",config.ai_vision_model))
        await message.answer(text(data.get("lang","EN"),"NEW_DIALOG"),reply_markup=main_keyboard(data.get("lang","EN")))
    @router.message(F.text.in_(button_values("BTN_ADD")))
    async def add(message:Message,state:FSMContext):
        data=await state.get_data(); lang=data.get("lang","EN"); await state.clear(); await state.update_data(lang=lang,selected_model=config.ai_vision_model)
        await message.answer(text(lang,"ADD_PROMPT"),reply_markup=main_keyboard(lang))
    @router.message(F.text.in_(button_values("BTN_SETTINGS")))
    async def settings(message:Message,state:FSMContext):
        data=await state.get_data(); lang=data.get("lang","EN"); await state.set_state(BotStates.settings); await message.answer(text(lang,"SETTINGS_TEXT"),reply_markup=settings_keyboard(lang))
    @router.message(F.text.in_(button_values("BTN_MODEL")))
    async def models(message:Message,state:FSMContext):
        lang=(await state.get_data()).get("lang","EN"); names=tuple(x.name for x in config.model_catalog); await message.answer(text(lang,"MODEL_PROMPT"),reply_markup=model_keyboard(names))
    @router.callback_query(F.data.startswith("model:"))
    async def model_selected(callback:CallbackQuery,state:FSMContext):
        data=await state.get_data(); lang=data.get("lang","EN")
        try: model=config.model_catalog[int(callback.data.split(":",1)[1])].name
        except (ValueError,IndexError): await callback.answer("Invalid model",show_alert=True); return
        await state.update_data(selected_model=model); await callback.answer(); await callback.message.answer(text(lang,"MODEL_SET",model=model),reply_markup=settings_keyboard(lang))
    @router.message(F.text.in_(button_values("BTN_TODAY")))
    async def today(message:Message,state:FSMContext):
        lang=(await state.get_data()).get("lang","EN"); entries=diary.today(message.from_user.id)
        if not entries: await message.answer(text(lang,"TODAY_EMPTY")); return
        await message.answer(text(lang,"TODAY",count=len(entries),kcal=sum(x.total_kcal for x in entries),protein=sum(x.protein_g for x in entries),fat=sum(x.fat_g for x in entries),carbs=sum(x.carbs_g for x in entries)),reply_markup=diary_manage_keyboard(lang))
    @router.callback_query(F.data.in_({"manage:edit","manage:delete"}))
    async def manage_last(callback:CallbackQuery,state:FSMContext):
        lang=(await state.get_data()).get("lang","EN"); await callback.answer()
        if not diary.last(callback.from_user.id): await callback.message.answer(text(lang,"NO_LAST")); return
        action="edit" if callback.data.endswith("edit") else "delete"
        await state.set_state(BotStates.awaiting_edit_confirmation if action=="edit" else BotStates.awaiting_delete_confirmation)
        await callback.message.answer(text(lang,"CONFIRM_EDIT" if action=="edit" else "CONFIRM_DELETE"),reply_markup=yes_no_keyboard(action,lang))
    @router.message(F.text.in_(button_values("BTN_DELETE_LAST")))
    async def delete_last(message:Message,state:FSMContext):
        lang=(await state.get_data()).get("lang","EN")
        if not diary.last(message.from_user.id): await message.answer(text(lang,"NO_LAST")); return
        await state.set_state(BotStates.awaiting_delete_confirmation); await message.answer(text(lang,"CONFIRM_DELETE"),reply_markup=yes_no_keyboard("delete",lang))
    @router.callback_query(F.data.startswith("delete:"))
    async def delete_confirm(callback:CallbackQuery,state:FSMContext):
        lang=(await state.get_data()).get("lang","EN"); await callback.answer()
        if callback.data.endswith(":yes"): diary.delete_last(callback.from_user.id); await callback.message.answer(text(lang,"DELETED"))
        await state.set_state(None)
    @router.message(F.text.in_(button_values("BTN_EDIT_LAST")))
    async def edit_last(message:Message,state:FSMContext):
        lang=(await state.get_data()).get("lang","EN")
        if not diary.last(message.from_user.id): await message.answer(text(lang,"NO_LAST")); return
        await state.set_state(BotStates.awaiting_edit_confirmation); await message.answer(text(lang,"CONFIRM_EDIT"),reply_markup=yes_no_keyboard("edit",lang))
    @router.callback_query(F.data.startswith("edit:"))
    async def edit_confirm(callback:CallbackQuery,state:FSMContext):
        data=await state.get_data(); lang=data.get("lang","EN"); await callback.answer(); await state.set_state(None)
        if callback.data.endswith(":yes"): await state.update_data(edit_last_pending=True); await callback.message.answer(text(lang,"EDIT_SEND"))
    return router
