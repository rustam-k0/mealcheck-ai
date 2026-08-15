from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from banana_bot.config import ConfigError
from banana_bot.domain import DraftStatus, MealDraft, NutritionEstimate
from banana_bot.formatting import telegram_html
from banana_bot.http import ProviderError
from banana_bot.i18n import button_values, text
from banana_bot.keyboards import confirmation_keyboard, diary_keyboard, main_keyboard
from banana_bot.services.ai import FoodAnalysisService
from banana_bot.services.safety import safety_reply
from banana_bot.states import BotStates
from banana_bot.observability import log_event

def _draft_text(draft:MealDraft,lang:str)->str:
    units={"RU":{"g":"г","ml":"мл","piece":"шт.","portion":"порц."},"EN":{"g":"g","ml":"ml","piece":"pc","portion":"serving"}}
    items="\n".join(f"{i}. {telegram_html(x.name)} — ~{x.amount:g} {units.get(lang,units['EN']).get(x.unit,x.unit)}" for i,x in enumerate(draft.detected_items,1))
    intro=("На фото:" if draft.source=="photo" else "Получилось:") if lang=="RU" else ("In the photo:" if draft.source=="photo" else "Got it:")
    return text(lang,"RECOGNIZED",intro=intro,items=items or "—")

async def show_draft(message:Message,state:FSMContext,draft:MealDraft,lang:str):
    await state.update_data(meal_draft=draft.model_dump_json()); await state.set_state(BotStates.awaiting_food_confirmation)
    await message.answer(_draft_text(draft,lang),reply_markup=confirmation_keyboard(lang,draft.interaction_id))

async def show_estimate(message:Message,state:FSMContext,draft:MealDraft,estimate:NutritionEstimate,lang:str):
    kcal_label="ккал" if lang=="RU" else "kcal"
    rows="\n".join(f"• {telegram_html(x.name)} — {x.kcal:.0f} {kcal_label}" for x in estimate.items)
    total=estimate.total; await state.update_data(meal_draft=draft.model_dump_json(),nutrition_estimate=estimate.model_dump_json()); await state.set_state(BotStates.awaiting_diary_confirmation)
    await message.answer(text(lang,"ESTIMATE",table=rows,kcal=total.kcal,protein=total.protein_g,fat=total.fat_g,carbs=total.carbs_g),reply_markup=diary_keyboard(lang,draft.interaction_id))

def build_text_router(service:FoodAnalysisService)->Router:
    router=Router(name="text")
    excluded=set().union(*(button_values(k) for k in ("BTN_ADD","BTN_TODAY","BTN_EDIT_LAST","BTN_DELETE_LAST","BTN_SETTINGS","BTN_NEW","BTN_LANG","BTN_MODEL")))
    @router.message(BotStates.awaiting_food_correction,F.text)
    @router.message(BotStates.awaiting_food_confirmation,F.text)
    async def correction(message:Message,state:FSMContext):
        data=await state.get_data(); lang=data.get("lang","EN"); status=await message.answer(text(lang,"PROCESSING"))
        try: draft=await service.apply_correction(MealDraft.model_validate_json(data["meal_draft"]),message.text,lang); await status.delete(); await show_draft(message,state,draft,lang)
        except Exception: await status.edit_text(text(lang,"ERR"))
    async def active_draft(callback:CallbackQuery,state:FSMContext)->MealDraft|None:
        data=await state.get_data(); raw=data.get("meal_draft")
        if not raw or callback.data.rsplit(":",1)[-1] != MealDraft.model_validate_json(raw).interaction_id:
            await callback.answer(text(data.get("lang","EN"),"STALE_MEAL"),show_alert=True); return None
        return MealDraft.model_validate_json(raw)
    @router.callback_query(F.data.startswith("meal:correct:"))
    async def correct(callback:CallbackQuery,state:FSMContext):
        data=await state.get_data(); lang=data.get("lang","EN")
        if not await active_draft(callback,state): return
        await callback.answer(); await state.set_state(BotStates.awaiting_food_correction); await callback.message.answer(text(lang,"CORRECTION_PROMPT"))
    @router.callback_query(F.data.startswith("meal:cancel:"))
    async def cancel(callback:CallbackQuery,state:FSMContext):
        data=await state.get_data(); lang=data.get("lang","EN")
        if not await active_draft(callback,state): return
        await callback.answer(); await state.clear(); await state.update_data(lang=lang,selected_model=data.get("selected_model",service.config.ai_vision_model)); await callback.message.answer(text(lang,"NEW_DIALOG"),reply_markup=main_keyboard(lang))
    @router.callback_query(F.data.startswith("meal:confirm:"))
    async def confirm(callback:CallbackQuery,state:FSMContext):
        data=await state.get_data(); lang=data.get("lang","EN")
        current=await active_draft(callback,state)
        if not current: return
        await callback.answer(); status=await callback.message.answer(text(lang,"PROCESSING"))
        try:
            draft=current.model_copy(update={"status":DraftStatus.confirmed}); estimate=await service.calculate_confirmed_meal(draft); await status.delete(); await show_estimate(callback.message,state,draft,estimate,lang)
        except Exception as exc:
            log_event("meal_calculation_failed", error_type=type(exc).__name__, error_code=getattr(exc,"code",None), status=getattr(exc,"status",None))
            await status.edit_text(text(lang,"ERR"))
    @router.callback_query(F.data.startswith("diary:save:") | F.data.startswith("diary:skip:"))
    async def diary_action(callback:CallbackQuery,state:FSMContext):
        data=await state.get_data(); lang=data.get("lang","EN"); await callback.answer()
        raw=data.get("meal_draft")
        if not raw or callback.data.rsplit(":",1)[-1] != MealDraft.model_validate_json(raw).interaction_id:
            await callback.message.answer(text(lang,"STALE_MEAL")); return
        if callback.data.startswith("diary:save:"):
            if data.get("edit_last_pending"): service.diary.delete_last(callback.from_user.id)
            service.save_to_diary(MealDraft.model_validate_json(data["meal_draft"]),NutritionEstimate.model_validate_json(data["nutrition_estimate"])); await callback.message.answer(text(lang,"SAVED"))
        else: await callback.message.answer(text(lang,"NOT_SAVED"))
        model=data.get("selected_model",service.config.ai_vision_model); await state.clear(); await state.update_data(lang=lang,selected_model=model)
    @router.message(F.text,~F.text.in_(excluded))
    async def food_text(message:Message,state:FSMContext):
        data=await state.get_data(); lang=data.get("lang","EN"); safe=safety_reply(message.text,lang)
        if safe: await message.answer(safe); return
        status=await message.answer(text(lang,"PROCESSING"))
        try: draft=await service.recognize_text(message.from_user.id,message.text,service.config.ai_text_model,lang); await status.delete(); await show_draft(message,state,draft,lang)
        except (ProviderError,ConfigError): await status.edit_text(text(lang,"ERR"))
    return router
