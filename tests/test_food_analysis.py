import json
import tempfile
import unittest
from unittest.mock import AsyncMock

from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage

from banana_bot.config import ConfigError, load_config
from banana_bot.diary import SQLiteDiaryRepository
from banana_bot.domain import DraftStatus, MealDraft, NutritionEstimate
from banana_bot.services.ai import FoodAnalysisService, InvalidModelResponse
from banana_bot.services.safety import safety_reply
from banana_bot.services.prompts import CALCULATION_SYSTEM_PROMPT, RECOGNITION_SYSTEM_PROMPT
from banana_bot.routers.text import show_draft, show_estimate
from banana_bot.states import BotStates

RECOGNITION={"items":[{"name":"Rice","amount":120,"unit":"g","preparation":None,"visible_evidence":"visible","confidence":.8}]}
NUTRITION={"items":[{"name":"Rice","confirmed_amount_g":120,"kcal":156,"protein_g":3,"fat_g":.4,"carbs_g":34,"confidence":.8}],"total":{"kcal":156,"protein_g":3,"fat_g":.4,"carbs_g":34},"estimated_error_percent":20,"uncertainty_reasons":["weight"]}

class FakeAdapter:
    def __init__(self, responses): self.responses=list(responses); self.calls=[]
    async def complete(self,model,system,user,**kwargs):
        self.calls.append((model,system,user,kwargs))
        from banana_bot.domain import TextResult
        return TextResult(text=self.responses.pop(0),provider="fake",model=model)
    async def transcribe(self,model,audio):
        from banana_bot.domain import TextResult
        return TextResult(text="rice 120 g",provider="fake",model=model)
    async def understand_audio(self,model,audio,**kwargs):
        self.audio_kwargs=kwargs
        from banana_bot.domain import TextResult
        return TextResult(text="rice 120 g",provider="fake",model=model)

class FoodTests(unittest.IsolatedAsyncioTestCase):
    def make(self,responses,extra=None):
        env={"TELEGRAM_BOT_TOKEN":"t","AI_API_KEY":"k","AI_BASE_URL":"https://gateway/v1","AI_VISION_MODEL":"vision","AI_TEXT_MODEL":"vision","AI_TRANSCRIPTION_MODEL":"vision","AI_MODEL_CATALOG":"vision|text+image+audio,text-only|text",**(extra or {})}
        config=load_config(env,validate=True); adapter=FakeAdapter(responses); tmp=tempfile.NamedTemporaryFile(suffix=".sqlite",delete=False)
        return config,adapter,FoodAnalysisService(config,adapter,SQLiteDiaryRepository(tmp.name))
    async def test_photo_draft_has_no_nutrition_and_confirmation_calculates(self):
        _,adapter,service=self.make([json.dumps(RECOGNITION),json.dumps(NUTRITION)])
        draft=await service.recognize_photo(1,b"photo","file")
        self.assertEqual(draft.status,DraftStatus.awaiting_confirmation); self.assertNotIn("kcal",draft.model_dump_json())
        with self.assertRaises(ValueError): await service.calculate_confirmed_meal(draft)
        estimate=await service.calculate_confirmed_meal(draft.model_copy(update={"status":DraftStatus.confirmed}))
        self.assertEqual(estimate.total.kcal,156); self.assertEqual(len(adapter.calls),2)
        self.assertIn('"name": "Rice"',adapter.calls[-1][2])
        self.assertNotIn("photo",adapter.calls[-1][3])
    async def test_nutrition_total_is_recalculated_from_all_items(self):
        nutrition={**NUTRITION,"total":{"kcal":1,"protein_g":1,"fat_g":1,"carbs_g":1}}
        _,_,service=self.make([json.dumps(nutrition)])
        draft=MealDraft(user_id=1,source="text",detected_items=RECOGNITION["items"],status=DraftStatus.confirmed,selected_model="vision")
        estimate=await service.calculate_confirmed_meal(draft)
        self.assertEqual(estimate.total.model_dump(),{"kcal":156.0,"protein_g":3.0,"fat_g":.4,"carbs_g":34.0})
    async def test_calculation_falls_back_to_multimodal_model_after_invalid_text_response(self):
        _,adapter,service=self.make(["bad","still bad",json.dumps(NUTRITION)],{"AI_TEXT_MODEL":"text-only"})
        draft=MealDraft(user_id=1,source="photo",detected_items=RECOGNITION["items"],status=DraftStatus.confirmed,selected_model="vision")
        estimate=await service.calculate_confirmed_meal(draft)
        self.assertEqual(estimate.total.kcal,156)
        self.assertEqual([call[0] for call in adapter.calls],["text-only","text-only","vision"])
    async def test_calculation_retries_without_strict_schema_when_only_model_fails(self):
        _,adapter,service=self.make(["bad","still bad",json.dumps(NUTRITION)])
        draft=MealDraft(user_id=1,source="photo",detected_items=RECOGNITION["items"],status=DraftStatus.confirmed,selected_model="vision")
        estimate=await service.calculate_confirmed_meal(draft)
        self.assertEqual(estimate.total.kcal,156)
        self.assertIsNone(adapter.calls[-1][3]["response_schema"])
    async def test_recognition_contract_has_no_clarifying_questions(self):
        _,adapter,service=self.make([json.dumps(RECOGNITION)])
        draft=await service.recognize_photo(1,b"photo","file")
        self.assertNotIn("clarifying_questions",draft.model_dump())
        response_schema=adapter.calls[0][3]["response_schema"]
        self.assertNotIn("clarifying_questions",response_schema["properties"])
    def test_unknown_yogurt_properties_use_assumptions_without_questions(self):
        prompt=RECOGNITION_SYSTEM_PROMPT.lower()
        self.assertIn("йогурт средней жирности",prompt)
        self.assertIn("не задавай вопросов",prompt)
        self.assertIn("всегда продолжай расчёт",CALCULATION_SYSTEM_PROMPT.lower())
    def test_unknown_mass_must_be_estimated(self):
        self.assertIn("если точная масса неизвестна, оцени",RECOGNITION_SYSTEM_PROMPT.lower())
    async def test_correction_replaces_draft_and_needs_confirmation(self):
        changed={**RECOGNITION,"items":[{**RECOGNITION["items"][0],"amount":90}]}
        _,adapter,service=self.make([json.dumps(RECOGNITION),json.dumps(changed)])
        draft=await service.recognize_text(1,"rice"); updated=await service.apply_correction(draft,"90 g")
        self.assertEqual(updated.detected_items[0].amount,90); self.assertEqual(updated.status,DraftStatus.awaiting_confirmation)
        self.assertEqual(updated.interaction_id,draft.interaction_id)
        correction_prompt=adapter.calls[-1][2]
        self.assertNotIn("user_id",correction_prompt)
        self.assertNotIn(draft.interaction_id,correction_prompt)
    async def test_text_and_voice_share_recognize_text_pipeline(self):
        _,_,service=self.make([json.dumps(RECOGNITION),json.dumps(RECOGNITION)])
        text_draft=await service.recognize_text(1,"rice"); voice_draft=await service.recognize_text(1,"rice",source="voice")
        self.assertEqual(text_draft.detected_items,voice_draft.detected_items); self.assertEqual(voice_draft.source,"voice")
    async def test_audio_uses_multimodal_model_without_transcription_endpoint(self):
        _,adapter,service=self.make([])
        result=await service.transcribe(b"ogg","RU")
        self.assertEqual(result.text,"rice 120 g")
        self.assertEqual(adapter.audio_kwargs,{"language":"RU","context":None})
    async def test_invalid_json_gets_one_repair_then_safe_error(self):
        _,adapter,service=self.make(["bad","still bad"])
        with self.assertRaises(InvalidModelResponse): await service.recognize_text(1,"rice")
        self.assertEqual(len(adapter.calls),2)
        self.assertFalse(InvalidModelResponse().safety_related)
    async def test_catalog_and_image_capability_are_enforced(self):
        config,_,service=self.make([])
        with self.assertRaises(ConfigError): config.validate_model("unknown")
        with self.assertRaisesRegex(ConfigError,"image"): await service.recognize_photo(1,b"x","f","text-only")
    async def test_diary_isolated_by_user(self):
        _,_,service=self.make([]); estimate=NutritionEstimate.model_validate(NUTRITION)
        base=MealDraft(user_id=1,source="text",detected_items=RECOGNITION["items"],status=DraftStatus.confirmed,selected_model="vision")
        service.save_to_diary(base,estimate); service.save_to_diary(base.model_copy(update={"user_id":2}),estimate)
        self.assertEqual(len(service.diary.today(1)),1); self.assertEqual(len(service.diary.today(2)),1)
    def test_risky_medical_request_is_safe(self): self.assertIn("врач",safety_reply("назначь лечебную диету","RU"))
    def test_ordinary_nutrition_request_is_not_blocked_by_safety(self):
        self.assertIsNone(safety_reply("натуральный йогурт примерно одна миска","RU"))

    async def test_draft_and_estimate_survive_confirmation_state_transition(self):
        storage=MemoryStorage(); state=FSMContext(storage=storage,key=StorageKey(bot_id=1,chat_id=1,user_id=1))
        message=AsyncMock()
        draft=MealDraft(user_id=1,source="photo",detected_items=RECOGNITION["items"],selected_model="vision")
        await show_draft(message,state,draft,"RU")
        self.assertEqual(await state.get_state(),BotStates.awaiting_food_confirmation.state)
        stored=MealDraft.model_validate_json((await state.get_data())["meal_draft"])
        confirmed=stored.model_copy(update={"status":DraftStatus.confirmed})
        estimate=NutritionEstimate.model_validate(NUTRITION)
        await show_estimate(message,state,confirmed,estimate,"RU")
        data=await state.get_data()
        self.assertEqual(await state.get_state(),BotStates.awaiting_diary_confirmation.state)
        self.assertEqual(MealDraft.model_validate_json(data["meal_draft"]).status,DraftStatus.confirmed)
        self.assertEqual(NutritionEstimate.model_validate_json(data["nutrition_estimate"]).total.kcal,156)

    async def test_correction_keeps_interaction_and_can_be_confirmed(self):
        changed={**RECOGNITION,"items":[{**RECOGNITION["items"][0],"amount":90}]}
        _,_,service=self.make([json.dumps(changed),json.dumps(NUTRITION)])
        original=MealDraft(user_id=1,source="photo",detected_items=RECOGNITION["items"],selected_model="vision")
        corrected=await service.apply_correction(original,"90 g")
        self.assertEqual(corrected.interaction_id,original.interaction_id)
        estimate=await service.calculate_confirmed_meal(corrected.model_copy(update={"status":DraftStatus.confirmed}))
        self.assertEqual(estimate.total.kcal,156)

if __name__=="__main__": unittest.main()
