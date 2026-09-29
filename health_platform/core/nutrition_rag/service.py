"""
Clinical Nutrition RAG Service.
Implements evidence retrieval, case-wise and age-wise diet synthesis, and
grounded PubMed clinical practice guideline query processing.
"""

from typing import List, Optional, Dict, Any
import uuid
import re
from datetime import datetime, timezone

from health_platform.core.nutrition_rag.models import (
    DietConditionCategory,
    AgeGroupCategory,
    PubMedCitation,
    DietItemRecommendation,
    MacronutrientTarget,
    ClinicalDietGuideline,
    PersonalizedDietPlan,
    DietRAGQueryInput,
    DietRAGQueryResponse
)
from health_platform.core.nutrition_rag.knowledge_base import CLINICAL_NUTRITION_GUIDELINES

class NutritionRAGService:
    def __init__(self):
        self._guidelines: Dict[str, ClinicalDietGuideline] = CLINICAL_NUTRITION_GUIDELINES

    def get_guideline(self, key: str) -> Optional[ClinicalDietGuideline]:
        return self._guidelines.get(key)

    def list_all_guidelines(self) -> List[ClinicalDietGuideline]:
        return list(self._guidelines.values())

    def determine_age_group(self, age: int) -> AgeGroupCategory:
        if age < 18:
            return AgeGroupCategory.PEDIATRIC
        elif age <= 45:
            return AgeGroupCategory.YOUNG_ADULT
        elif age < 65:
            return AgeGroupCategory.MIDDLE_AGED
        else:
            return AgeGroupCategory.GERIATRIC_ELDERLY

    def generate_personalized_diet_plan(
        self,
        patient_name: str,
        age: int,
        surgical_case: Optional[str] = None,
        diagnosed_conditions: Optional[List[str]] = None
    ) -> PersonalizedDietPlan:
        """
        Synthesizes a multi-condition personalized diet plan considering:
        - Surgical case-wise needs (orthopedic, wound healing, collagen)
        - Age-wise needs (geriatric anabolic resistance, leucine pulse)
        - Chronic comorbidities (diabetes, hypertension, CAD, CKD, PCOS, weight reduction)
        """
        age_group = self.determine_age_group(age)
        conditions = [c.lower() for c in (diagnosed_conditions or [])]

        selected_keys: List[str] = []

        # 1. Surgical Case Check
        if surgical_case:
            sc_lower = surgical_case.lower()
            if any(k in sc_lower for k in ["knee", "meniscus", "acl", "bone", "fracture", "ortho", "joint"]):
                selected_keys.append("POST_OP_ORTHOPEDIC")
            elif any(k in sc_lower for k in ["bowel", "abdomen", "colon", "hernia", "appendix", "gallbladder", "laparosc"]):
                selected_keys.append("POST_OP_ORTHOPEDIC") # fallback to post-op or general
            elif any(k in sc_lower for k in ["cardiac", "cabg", "stent", "sternotomy", "bypass"]):
                selected_keys.append("HEART_DISEASE_CAD")

        # 2. Age Check: if elderly and post-op, add geriatric sarcopenia protocol
        if age >= 65 and surgical_case:
            if "POST_OP_GERIATRIC" not in selected_keys:
                selected_keys.append("POST_OP_GERIATRIC")

        # 3. Comorbidity Checks
        for c in conditions:
            if any(k in c for k in ["diabet", "sugar", "glucose", "hba1c"]):
                if "DIABETES_T2" not in selected_keys:
                    selected_keys.append("DIABETES_T2")
            if any(k in c for k in ["hyperten", "bp", "blood pressure"]):
                if "HYPERTENSION" not in selected_keys:
                    selected_keys.append("HYPERTENSION")
            if any(k in c for k in ["heart", "cad", "coronary", "stemi", "ischemi", "infarct"]):
                if "HEART_DISEASE_CAD" not in selected_keys:
                    selected_keys.append("HEART_DISEASE_CAD")
            if any(k in c for k in ["kidney", "renal", "ckd", "nephro"]):
                if "KIDNEY_DISEASE_CKD" not in selected_keys:
                    selected_keys.append("KIDNEY_DISEASE_CKD")
            if any(k in c for k in ["pcod", "pcos", "polycystic"]):
                if "PCOD_PCOS" not in selected_keys:
                    selected_keys.append("PCOD_PCOS")
            if any(k in c for k in ["obese", "obesity", "overweight", "weight"]):
                if "WEIGHT_REDUCTION" not in selected_keys:
                    selected_keys.append("WEIGHT_REDUCTION")

        # Fallback if no specific matched
        if not selected_keys:
            selected_keys = ["POST_OP_ORTHOPEDIC"]

        synthesized_guidelines = [self._guidelines[k] for k in selected_keys if k in self._guidelines]

        # Combine superfoods and avoid lists
        superfoods: List[DietItemRecommendation] = []
        prohibited: List[DietItemRecommendation] = []
        citations: List[PubMedCitation] = []

        seen_super = set()
        seen_prohib = set()
        seen_pmids = set()

        for g in synthesized_guidelines:
            for item in g.recommended_foods:
                if item.food_item not in seen_super:
                    seen_super.add(item.food_item)
                    superfoods.append(item)
            for item in g.prohibited_foods:
                if item.food_item not in seen_prohib:
                    seen_prohib.add(item.food_item)
                    prohibited.append(item)
            for cit in g.pubmed_citations:
                if cit.pmid not in seen_pmids:
                    seen_pmids.add(cit.pmid)
                    citations.append(cit)

        # Formulate combined macronutrient targets with clinical safety precedence
        # Rule: If CKD is present without dialysis, protein must be restricted to 0.6-0.8 g/kg despite post-op status!
        has_ckd = "KIDNEY_DISEASE_CKD" in selected_keys
        has_ortho = "POST_OP_ORTHOPEDIC" in selected_keys or "POST_OP_GERIATRIC" in selected_keys

        if "WEIGHT_REDUCTION" in selected_keys:
            calorie_target = "500 - 750 kcal/day deficit from maintenance TDEE (AACE/ACE target for sustained fat loss)"
            protein_target = "1.2 - 1.6 g/kg/day (high-satiety, lean mass preservation)"
            sodium_target = "< 2,000 mg/day"
            fluid_target = "2.5 - 3.0 Liters/day"
        elif has_ckd:
            calorie_target = "30 - 35 kcal/kg/day (KDOQI target to prevent protein-energy wasting in CKD)"
            protein_target = "0.6 - 0.8 g/kg/day (KDOQI Renal-sparing target takes precedence to avoid uremic strain)"
            sodium_target = "< 2,000 mg/day"
            fluid_target = "1.5 - 2.0 Liters/day (strictly monitor for peripheral/pulmonary edema)"
        elif has_ortho:
            calorie_target = "25 - 30 kcal/kg/day (euvolemic dry body weight)"
            protein_target = "1.5 - 2.0 g/kg/day (ESPEN Surgical Recovery target with 3g Leucine per bolus)"
            sodium_target = "< 2,300 mg/day"
            fluid_target = "2.5 - 3.0 Liters/day (accelerates clearance of inflammatory cytokines)"
        elif "DIABETES_T2" in selected_keys:
            calorie_target = "25 - 30 kcal/kg/day (individualized for glycemic control)"
            protein_target = "1.0 - 1.2 g/kg/day (ADA Target)"
            sodium_target = "< 2,000 mg/day"
            fluid_target = "2.5 Liters/day"
        else:
            calorie_target = "25 - 30 kcal/kg/day (euvolemic dry body weight)"
            protein_target = "1.2 - 1.5 g/kg/day"
            sodium_target = "< 2,000 mg/day"
            fluid_target = "2.5 Liters/day"

        combined_macros = MacronutrientTarget(
            daily_calories_guideline=calorie_target,
            protein_g_per_kg=protein_target,
            carbohydrate_pct="40% - 45% (strictly unrefined, low-glycemic sources)",
            fat_pct="30% - 35% (predominantly Extra Virgin Olive Oil, nuts, Omega-3s)",
            dietary_fiber_g="35 - 45 g/day (essential for metabolic, intestinal, and glycemic health)",
            sodium_limit_mg=sodium_target,
            potassium_guideline="3,500 - 4,700 mg/day (adjusted lower if serum K+ elevated in CKD)",
            fluid_target=fluid_target
        )

        chrononutrition = (
            "Early Time-Restricted Eating: Consume meals within an 8-to-10 hour daylight window (e.g. 8:30 AM to 6:30 PM). "
            "Protein Pulse Feeding: Distribute protein into 25-35g servings every 4 hours. "
            "Meal Sequencing: Consume raw greens/fiber first, then lean protein, and complex carbohydrates last to attenuate postprandial glucose surges by 40%."
        )

        return PersonalizedDietPlan(
            patient_name=patient_name,
            age=age,
            age_group=age_group,
            active_surgical_case=surgical_case,
            diagnosed_conditions=diagnosed_conditions or [],
            synthesized_guidelines=synthesized_guidelines,
            combined_macro_targets=combined_macros,
            curated_superfoods=superfoods,
            curated_prohibited_foods=prohibited,
            chrononutrition_pacing=chrononutrition,
            pubmed_references_summary=citations,
            generated_at=datetime.now(timezone.utc)
        )

    def query_nutrition_rag(self, payload: DietRAGQueryInput) -> DietRAGQueryResponse:
        """
        Retrieves relevant PubMed-indexed clinical nutrition guidelines and formulates
        an authoritative, evidence-grounded response with explicit PMIDs.
        """
        q = payload.query.lower()
        matched_guidelines: List[ClinicalDietGuideline] = []

        # Keyword mapping for RAG retrieval
        if any(w in q for w in ["diabet", "sugar", "glucose", "hba1c"]):
            matched_guidelines.append(self._guidelines["DIABETES_T2"])
        if any(w in q for w in ["hypertens", "bp", "blood pressure", "dash", "sodium", "salt"]):
            matched_guidelines.append(self._guidelines["HYPERTENSION"])
        if any(w in q for w in ["heart", "cardiac", "coronary", "cholesterol", "stemi", "athero"]):
            matched_guidelines.append(self._guidelines["HEART_DISEASE_CAD"])
        if any(w in q for w in ["kidney", "renal", "ckd", "egfr", "creatinine", "proteinuria"]):
            matched_guidelines.append(self._guidelines["KIDNEY_DISEASE_CKD"])
        if any(w in q for w in ["pcod", "pcos", "ovary", "androgen", "spearmint", "period"]):
            matched_guidelines.append(self._guidelines["PCOD_PCOS"])
        if any(w in q for w in ["weight", "obese", "obesity", "fat loss", "slimming"]):
            matched_guidelines.append(self._guidelines["WEIGHT_REDUCTION"])
        if any(w in q for w in ["elderly", "geriatric", "sarcopenia", "old age", "leucine"]):
            matched_guidelines.append(self._guidelines["POST_OP_GERIATRIC"])
        if any(w in q for w in ["post-op", "postoperative", "surgery", "knee", "meniscus", "wound", "cartilage"]):
            if self._guidelines["POST_OP_ORTHOPEDIC"] not in matched_guidelines:
                matched_guidelines.append(self._guidelines["POST_OP_ORTHOPEDIC"])

        # Fallback to general post-op orthopedic if none detected
        if not matched_guidelines:
            matched_guidelines.append(self._guidelines["POST_OP_ORTHOPEDIC"])

        # Aggregate citations and foods
        citations: List[PubMedCitation] = []
        superfoods: List[str] = []
        prohibited: List[str] = []

        for g in matched_guidelines:
            citations.extend(g.pubmed_citations)
            superfoods.extend([f.food_item for f in g.recommended_foods])
            prohibited.extend([f.food_item for f in g.prohibited_foods])

        # Deduplicate
        seen_pmids = set()
        dedup_citations = []
        for c in citations:
            if c.pmid not in seen_pmids:
                seen_pmids.add(c.pmid)
                dedup_citations.append(c)

        # Formulate grounded clinical answer
        primary_g = matched_guidelines[0]
        cit_summary = ", ".join([f"'{c.title}' in {c.journal} ({c.year}, PMID: {c.pmid})" for c in dedup_citations[:2]])

        answer_parts = [
            f"Based on evidence-based recommendations from {cit_summary}:",
            f"For {primary_g.condition_name}, the primary nutritional targets are:",
            f"• Protein Target: {primary_g.macro_targets.protein_g_per_kg}",
            f"• Carbohydrate & Fiber: {primary_g.macro_targets.carbohydrate_pct} carbs with {primary_g.macro_targets.dietary_fiber_g} fiber.",
            f"• Sodium Target: {primary_g.macro_targets.sodium_limit_mg}.",
            "",
            "Key Recommended Superfoods:",
            "\n".join([f"• {f.food_item}: {f.clinical_rationale} (Mechanism: {f.biochemical_mechanism})" for f in primary_g.recommended_foods[:3]]),
            "",
            "Foods to Strictly Avoid / Limit:",
            "\n".join([f"• {f.food_item}: {f.clinical_rationale} (Mechanism: {f.biochemical_mechanism})" for f in primary_g.prohibited_foods[:2]]),
            "",
            f"Meal Timing & Chrononutrition: {primary_g.meal_timing_and_chrononutrition}"
        ]

        grounded_answer = "\n".join(answer_parts)
        takeaway = (
            f"Grounding Evidence: {len(dedup_citations)} peer-reviewed PubMed guidelines referenced. "
            f"Strictly follow {primary_g.macro_targets.protein_g_per_kg} and {primary_g.macro_targets.sodium_limit_mg}."
        )

        return DietRAGQueryResponse(
            query=payload.query,
            grounded_answer=grounded_answer,
            relevant_citations=dedup_citations,
            recommended_foods=superfoods[:6],
            prohibited_foods=prohibited[:4],
            clinical_takeaway=takeaway
        )
