import json
import tempfile
import unittest

from banana_bot.config import ConfigError, load_config
from banana_bot.diary import SQLiteDiaryRepository
from banana_bot.domain import DraftStatus, MealDraft, NutritionEstimate
from banana_bot.services.ai import FoodAnalysisService, InvalidModelResponse
from banana_bot.services.safety import safety_reply

RECOGNITION={"items":[{"name":"Rice","amount":120,"unit":"g","preparation":None,"visible_evidence":"visible","confidence":.8}],"missing_details":[],"clarifying_questions":[],"overall_confidence":.8,"warnings":[]}
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
    async def understand_audio(self,model,audio):
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
    async def test_correction_replaces_draft_and_needs_confirmation(self):
        changed={**RECOGNITION,"items":[{**RECOGNITION["items"][0],"amount":90}]}
        _,_,service=self.make([json.dumps(RECOGNITION),json.dumps(changed)])
        draft=await service.recognize_text(1,"rice"); updated=await service.apply_correction(draft,"90 g")
        self.assertEqual(updated.detected_items[0].amount,90); self.assertEqual(updated.status,DraftStatus.awaiting_confirmation)
    async def test_text_and_voice_share_recognize_text_pipeline(self):
        _,_,service=self.make([json.dumps(RECOGNITION),json.dumps(RECOGNITION)])
        text_draft=await service.recognize_text(1,"rice"); voice_draft=await service.recognize_text(1,"rice",source="voice")
        self.assertEqual(text_draft.detected_items,voice_draft.detected_items); self.assertEqual(voice_draft.source,"voice")
    async def test_audio_uses_multimodal_model_without_transcription_endpoint(self):
        _,adapter,service=self.make([])
        result=await service.transcribe(b"ogg")
        self.assertEqual(result.text,"rice 120 g")
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
        base=MealDraft(user_id=1,source="text",detected_items=RECOGNITION["items"],confidence=.8,status=DraftStatus.confirmed,selected_model="vision")
        service.save_to_diary(base,estimate); service.save_to_diary(base.model_copy(update={"user_id":2}),estimate)
        self.assertEqual(len(service.diary.today(1)),1); self.assertEqual(len(service.diary.today(2)),1)
    def test_risky_medical_request_is_safe(self): self.assertIn("врач",safety_reply("назначь лечебную диету","RU"))

if __name__=="__main__": unittest.main()
