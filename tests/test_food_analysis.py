import json
import tempfile
import unittest

from banana_bot.config import ConfigError, load_config
from banana_bot.diary import SQLiteDiaryRepository
from banana_bot.domain import DraftStatus, MealDraft, NutritionEstimate
from banana_bot.services.ai import FoodAnalysisService, InvalidModelResponse
from banana_bot.services.safety import safety_reply

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

if __name__=="__main__": unittest.main()
