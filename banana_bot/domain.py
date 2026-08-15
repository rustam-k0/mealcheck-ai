from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field, model_validator


class DraftStatus(str, Enum):
    awaiting_confirmation = "awaiting_confirmation"
    confirmed = "confirmed"
    calculated = "calculated"


class FoodItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1)
    amount: float = Field(gt=0)
    unit: str = Field(pattern=r"^(g|ml|piece|portion)$")
    preparation: str | None = None
    visible_evidence: str | None = None
    confidence: float = Field(ge=0, le=1)


class RecognitionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[FoodItem]
    missing_details: list[str]
    clarifying_questions: list[str] = Field(max_length=2)
    overall_confidence: float = Field(ge=0, le=1)
    warnings: list[str]


class MealDraft(BaseModel):
    user_id: int
    source: str = Field(pattern=r"^(photo|text|voice)$")
    image_file_id: str | None = None
    detected_items: list[FoodItem]
    portions: list[str] = Field(default_factory=list)
    preparation_notes: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    status: DraftStatus = DraftStatus.awaiting_confirmation
    selected_model: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    missing_details: list[str] = Field(default_factory=list)
    clarifying_questions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class NutritionItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    confirmed_amount_g: float = Field(ge=0)
    kcal: float = Field(ge=0)
    protein_g: float = Field(ge=0)
    fat_g: float = Field(ge=0)
    carbs_g: float = Field(ge=0)
    confidence: float = Field(ge=0, le=1)


class NutritionTotal(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kcal: float = Field(ge=0)
    protein_g: float = Field(ge=0)
    fat_g: float = Field(ge=0)
    carbs_g: float = Field(ge=0)


class NutritionEstimate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[NutritionItem]
    total: NutritionTotal
    estimated_error_percent: float = Field(ge=0, le=100)
    uncertainty_reasons: list[str]


class DiaryEntry(BaseModel):
    id: int | None = None
    user_id: int
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    meal_type: str | None = None
    source: str
    confirmed_items: list[FoodItem]
    total_kcal: float
    protein_g: float
    fat_g: float
    carbs_g: float
    uncertainty: str
    model: str


class TextResult(BaseModel):
    text: str
    provider: str
    model: str
