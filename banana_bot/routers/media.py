from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from io import BytesIO
from PIL import Image, ImageOps

from banana_bot.config import ConfigError
from banana_bot.http import ProviderError
from banana_bot.i18n import text
from banana_bot.routers.text import show_draft
from banana_bot.services.ai import FoodAnalysisService
from banana_bot.domain import MealDraft
from banana_bot.states import BotStates

async def _download(bot,file_id:str)->bytes:
    value=await bot.get_file(file_id); stream=await bot.download_file(value.file_path); return stream.read()

def _optimize_photo(content: bytes) -> bytes:
    with Image.open(BytesIO(content)) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
        image.thumbnail((1280, 1280), Image.Resampling.LANCZOS)
        output = BytesIO(); image.save(output, "JPEG", quality=82, optimize=True)
        return output.getvalue()

def build_media_router(service:FoodAnalysisService)->Router:
    router=Router(name="media")
    @router.message(F.photo)
    async def photo(message:Message,state:FSMContext,bot):
        data=await state.get_data(); lang=data.get("lang","EN"); model=service.config.ai_vision_model
        try: service.config.validate_model(model,"image")
        except ConfigError: await message.answer(text(lang,"NO_VISION")); return
        status=await message.answer(text(lang,"PROCESSING"))
        try:
            image=_optimize_photo(await _download(bot,message.photo[-1].file_id)); draft=await service.recognize_photo(message.from_user.id,image,message.photo[-1].file_id,model,lang); await status.delete(); await show_draft(message,state,draft,lang)
        except Exception: await status.edit_text(text(lang,"ERR"))
    @router.message(F.voice)
    async def voice(message:Message,state:FSMContext,bot):
        data=await state.get_data(); lang=data.get("lang","EN")
        if not service.config.ai_transcription_model: await message.answer(text(lang,"NO_TRANSCRIPTION")); return
        status=await message.answer(text(lang,"PROCESSING"))
        try:
            current_state=await state.get_state(); existing=MealDraft.model_validate_json(data["meal_draft"]) if data.get("meal_draft") and current_state in {BotStates.awaiting_food_confirmation.state,BotStates.awaiting_food_correction.state} else None
            context=", ".join(f"{x.name} {x.amount:g} {x.unit}" for x in existing.detected_items) if existing else None
            audio=await _download(bot,message.voice.file_id); transcript=await service.transcribe(audio,lang,context); await status.delete()
            if existing:
                draft=await service.apply_correction(existing,transcript.text,lang); await show_draft(message,state,draft,lang); return
            draft=await service.recognize_text(message.from_user.id,transcript.text,service.config.ai_text_model,lang,source="voice")
            if not draft.detected_items: await message.answer(text(lang,"BAD_VOICE")); return
            await show_draft(message,state,draft,lang)
        except ProviderError as exc: await status.edit_text(text(lang,"NO_TRANSCRIPTION" if exc.code=="transcription_unavailable" else "BAD_VOICE"))
        except Exception: await status.edit_text(text(lang,"BAD_VOICE"))
    @router.message()
    async def unsupported(message:Message,state:FSMContext): await message.answer(text((await state.get_data()).get("lang","EN"),"ADD_PROMPT"))
    return router
