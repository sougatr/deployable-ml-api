"""
Clinical Nutrition RAG & Personalized Diet Domain Models.
Supports case-wise and age-wise post-operative nutrition, as well as disease-specific
Medical Nutrition Therapy (Diabetes, Hypertension, Heart Disease, CKD, PCOD, Weight Loss)
grounded directly in peer-reviewed PubMed indexed clinical practice guidelines.
"""

from typing import List, Optional, Dict, Any
from enum import Enum
import uuid
from datetime import datetime, timezone
from pydantic import BaseModel, Field

class DietConditionCategory(str, Enum):
    POST_OP_ORTHOPEDIC = "POST_OP_ORTHOPEDIC"
    POST_OP_ABDOMINAL = "POST_OP_ABDOMINAL"
    POST_OP_CARDIAC = "POST_OP_CARDIAC"
    DIABETES_T2 = "DIABETES_T2"
    HYPERTENSION = "HYPERTENSION"
    HEART_DISEASE_CAD = "HEART_DISEASE_CAD"
    KIDNEY_DISEASE_CKD = "KIDNEY_DISEASE_CKD"
    PCOD_PCOS = "PCOD_PCOS"
    WEIGHT_REDUCTION = "WEIGHT_REDUCTION"

class AgeGroupCategory(str, Enum):
    PEDIATRIC = "PEDIATRIC"             # < 18
    YOUNG_ADULT = "YOUNG_ADULT"         # 18 - 45
    MIDDLE_AGED = "MIDDLE_AGED"         # 46 - 64
    GERIATRIC_ELDERLY = "GERIATRIC"     # >= 65

class PubMedCitation(BaseModel):
    pmid: str
    title: str
    authors: str
    journal: str
    year: int
    evidence_level: str # e.g. "Level 1A: International ESPEN Guideline", "ADA Consensus", "KDOQI Guideline"
    doi: Optional[str] = None
    url: str

class DietItemRecommendation(BaseModel):
    food_item: str
    category: str # "Superfood / Prioritize" or "Limit / Strictly Avoid"
    clinical_rationale: str
    biochemical_mechanism: str

class MacronutrientTarget(BaseModel):
    daily_calories_guideline: str
    protein_g_per_kg: str
    carbohydrate_pct: str
    fat_pct: str
    dietary_fiber_g: str
    sodium_limit_mg: str
    potassium_guideline: str
    fluid_target: str

class ClinicalDietGuideline(BaseModel):
    guideline_id: str
    condition: DietConditionCategory
    condition_name: str
    age_applicability: str
    surgical_case_type: Optional[str] = None
    clinical_summary: str
    pubmed_citations: List[PubMedCitation] = Field(default_factory=list)
    macro_targets: MacronutrientTarget
    recommended_foods: List[DietItemRecommendation] = Field(default_factory=list)
    prohibited_foods: List[DietItemRecommendation] = Field(default_factory=list)
    meal_timing_and_chrononutrition: str
    rag_knowledge_chunk: str

class PersonalizedDietPlan(BaseModel):
    patient_name: str
    age: int
    age_group: AgeGroupCategory
    active_surgical_case: Optional[str] = None
    diagnosed_conditions: List[str] = Field(default_factory=list)
    synthesized_guidelines: List[ClinicalDietGuideline] = Field(default_factory=list)
    combined_macro_targets: MacronutrientTarget
    curated_superfoods: List[DietItemRecommendation] = Field(default_factory=list)
    curated_prohibited_foods: List[DietItemRecommendation] = Field(default_factory=list)
    chrononutrition_pacing: str
    pubmed_references_summary: List[PubMedCitation] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class DietRAGQueryInput(BaseModel):
    mpi_id: Optional[uuid.UUID] = None
    query: str
    age: Optional[int] = None
    condition_filter: Optional[str] = None

class DietRAGQueryResponse(BaseModel):
    query: str
    grounded_answer: str
    relevant_citations: List[PubMedCitation] = Field(default_factory=list)
    recommended_foods: List[str] = Field(default_factory=list)
    prohibited_foods: List[str] = Field(default_factory=list)
    clinical_takeaway: str
    disclaimer: str = (
        "PubMed Evidence Disclaimer: These nutritional recommendations are derived from peer-reviewed "
        "clinical guidelines (ESPEN, ADA, ACC/AHA, KDOQI, AACE). Always discuss personalized dietary changes "
        "with your clinical dietitian or physician."
    )

class GeneratePersonalizedPlanInput(BaseModel):
    patient_name: str
    age: int
    surgical_case: Optional[str] = None
    diagnosed_conditions: List[str] = Field(default_factory=list)

