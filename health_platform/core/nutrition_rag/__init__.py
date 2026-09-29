"""
Clinical Nutrition RAG Module.
"""

from health_platform.core.nutrition_rag.models import (
    DietConditionCategory,
    AgeGroupCategory,
    PubMedCitation,
    DietItemRecommendation,
    MacronutrientTarget,
    ClinicalDietGuideline,
    PersonalizedDietPlan,
    GeneratePersonalizedPlanInput,
    DietRAGQueryInput,
    DietRAGQueryResponse
)
from health_platform.core.nutrition_rag.knowledge_base import CLINICAL_NUTRITION_GUIDELINES
from health_platform.core.nutrition_rag.service import NutritionRAGService

__all__ = [
    "DietConditionCategory",
    "AgeGroupCategory",
    "PubMedCitation",
    "DietItemRecommendation",
    "MacronutrientTarget",
    "ClinicalDietGuideline",
    "PersonalizedDietPlan",
    "GeneratePersonalizedPlanInput",
    "DietRAGQueryInput",
    "DietRAGQueryResponse",
    "CLINICAL_NUTRITION_GUIDELINES",
    "NutritionRAGService"
]
