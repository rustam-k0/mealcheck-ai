from __future__ import annotations

import json
from pydantic import BaseModel, ValidationError

from banana_bot.adapters.unified import UnifiedAIAdapter
from banana_bot.config import AppConfig, ConfigError
from banana_bot.diary import DiaryRepository
from banana_bot.domain import DiaryEntry, DraftStatus, MealDraft, NutritionEstimate, NutritionTotal, RecognitionResult, TextResult
from banana_bot.http import ProviderError
from banana_bot.services.prompts import CALCULATION_SYSTEM_PROMPT, NUTRITION_SCHEMA, RECOGNITION_SCHEMA, RECOGNITION_SYSTEM_PROMPT


class InvalidModelResponse(ProviderError):
    def __init__(self): super().__init__(502, "The AI gateway returned invalid structured data", "invalid_json")


class FoodAnalysisService:
    def __init__(self, config: AppConfig, adapter: UnifiedAIAdapter, diary: DiaryRepository, transcription_adapter: UnifiedAIAdapter | None = None):
        self.config, self.adapter, self.diary = config, adapter, diary
        self.transcription_adapter = transcription_adapter or adapter

    def _model(self, selected: str | None, capability: str) -> str:
        name = selected or (self.config.ai_vision_model if capability == "image" else self.config.ai_text_model)
        self.config.validate_model(name, capability)
        return name

    async def _structured(self, model: str, system: str, prompt: str, schema: str, target: type[BaseModel], image: bytes | None = None, *, strict_output: bool = True):
        request = f"{prompt}\nRequired JSON schema: {schema}"
        response_schema = target.model_json_schema() if strict_output else None
        result = await self.adapter.complete(model, system, request, image=image, max_tokens=self.config.max_output_tokens, response_schema=response_schema)
        for attempt in range(2):
            try:
                return target.model_validate_json(result.text)
            except (ValidationError, ValueError, json.JSONDecodeError):
                if attempt:
                    raise InvalidModelResponse()
                result = await self.adapter.complete(model, "Repair JSON. Return only valid JSON matching the schema; do not add facts.", f"Schema: {schema}\nInvalid response: {result.text}", max_tokens=self.config.max_output_tokens, response_schema=response_schema)
        raise InvalidModelResponse()

    async def recognize_photo(self, user_id: int, image: bytes, image_file_id: str, selected_model: str | None = None, lang: str = "RU") -> MealDraft:
        model = self._model(selected_model, "image")
        result: RecognitionResult = await self._structured(model, RECOGNITION_SYSTEM_PROMPT, f"Фото еды. Язык: {lang}.", RECOGNITION_SCHEMA, RecognitionResult, image)
        return self._draft(user_id, "photo", model, result, image_file_id)

    async def recognize_text(self, user_id: int, value: str, selected_model: str | None = None, lang: str = "RU", source: str = "text") -> MealDraft:
        model = self._model(selected_model, "text")
        result: RecognitionResult = await self._structured(model, RECOGNITION_SYSTEM_PROMPT, f"Язык: {lang}. Еда: {value}", RECOGNITION_SCHEMA, RecognitionResult)
        return self._draft(user_id, source, model, result)

    @staticmethod
    def _draft(user_id: int, source: str, model: str, result: RecognitionResult, image_file_id: str | None = None, interaction_id: str | None = None) -> MealDraft:
        identity = {"interaction_id": interaction_id} if interaction_id else {}
        return MealDraft(**identity, user_id=user_id, source=source, image_file_id=image_file_id,
            detected_items=result.items, selected_model=model)

    async def apply_correction(self, draft: MealDraft, correction: str, lang: str = "RU") -> MealDraft:
        model = self._model(self.config.ai_text_model, "text")
        items = json.dumps([item.model_dump() for item in draft.detected_items], ensure_ascii=False)
        prompt = f"Верни полный обновлённый список. Неизменённые позиции сохрани. Язык: {lang}. Сейчас: {items}. Правка: {correction}"
        result: RecognitionResult = await self._structured(model, RECOGNITION_SYSTEM_PROMPT, prompt, RECOGNITION_SCHEMA, RecognitionResult)
        return self._draft(draft.user_id, draft.source, model, result, draft.image_file_id, draft.interaction_id)

    async def calculate_confirmed_meal(self, draft: MealDraft) -> NutritionEstimate:
        if draft.status != DraftStatus.confirmed:
            raise ValueError("Nutrition can only be calculated for a confirmed meal draft")
        model = self._model(self.config.ai_text_model, "text")
        prompt = "Confirmed items (do not change): " + json.dumps([x.model_dump() for x in draft.detected_items], ensure_ascii=False)
        fallback = self.config.ai_vision_model
        if fallback != model:
            self.config.validate_model(fallback, "text")
        attempts = [(model, True)]
        if fallback != model:
            attempts.append((fallback, True))
        # Some compatible gateways intermittently reject strict JSON Schema
        # while still supporting ordinary JSON output for the same model.
        attempts.append((fallback, False))
        for index, (attempt_model, strict_output) in enumerate(attempts):
            try:
                estimate: NutritionEstimate = await self._structured(
                    attempt_model, CALCULATION_SYSTEM_PROMPT, prompt, NUTRITION_SCHEMA,
                    NutritionEstimate, strict_output=strict_output,
                )
                break
            except ProviderError:
                if index == len(attempts) - 1:
                    raise
        # The item estimates come from the model; make the displayed total deterministic.
        total = NutritionTotal(
            kcal=sum(item.kcal for item in estimate.items),
            protein_g=sum(item.protein_g for item in estimate.items),
            fat_g=sum(item.fat_g for item in estimate.items),
            carbs_g=sum(item.carbs_g for item in estimate.items),
        )
        return estimate.model_copy(update={"total": total})

    def save_to_diary(self, draft: MealDraft, estimate: NutritionEstimate) -> DiaryEntry:
        if draft.status not in {DraftStatus.confirmed, DraftStatus.calculated}:
            raise ValueError("Only a confirmed meal can be saved")
        total = estimate.total
        return self.diary.add(DiaryEntry(user_id=draft.user_id, source=draft.source, confirmed_items=draft.detected_items,
            total_kcal=total.kcal, protein_g=total.protein_g, fat_g=total.fat_g, carbs_g=total.carbs_g,
            uncertainty="; ".join(estimate.uncertainty_reasons), model=draft.selected_model))

    async def transcribe(self, audio: bytes, lang: str = "RU", context: str | None = None) -> TextResult:
        if not self.config.ai_transcription_model:
            raise ProviderError(501, "Audio transcription is not configured", "transcription_unavailable")
        model = self._model(self.config.ai_transcription_model, "audio")
        return await self.transcription_adapter.understand_audio(model, audio, language=lang, context=context)
