"""
Unit & Integration Tests for Personalized Clinical Nutrition RAG,
Case-wise & Age-wise Post-Operative Nutrition, Disease-Specific MNT
(Diabetes, Hypertension, CAD, CKD, PCOS, Weight Loss), and PubMed Grounding.
"""

import unittest
import uuid
from fastapi.testclient import TestClient

from health_platform.api.app import app, identity_service, nutrition_rag_service
from health_platform.core.identity.models import PatientRegistrationRequest
from health_platform.core.nutrition_rag.models import (
    DietConditionCategory,
    AgeGroupCategory,
    DietRAGQueryInput,
    GeneratePersonalizedPlanInput
)

class TestPersonalizedNutritionRAG(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

        # Register a patient for portal testing if not present
        if not hasattr(cls, "mpi_id") or cls.mpi_id is None:
            try:
                res = identity_service.resolve_or_create_patient(
                    PatientRegistrationRequest(
                        first_name="Ananya",
                        last_name="Roy",
                        dob="1996-03-20",
                        gender="FEMALE",
                        primary_phone="+919876500112",
                        postal_code="110001",
                        identifiers=[]
                    )
                )
                cls.mpi_id = res.mpi_id
            except Exception:
                for p in identity_service._patients.values():
                    if p.first_name == "Ananya" and p.last_name == "Roy":
                        cls.mpi_id = p.mpi_id
                        break

    def test_01_all_condition_guidelines_and_pubmed_pmids(self):
        """Verify all conditions are cataloged with peer-reviewed PubMed citations."""
        guidelines = nutrition_rag_service.list_all_guidelines()
        self.assertGreaterEqual(len(guidelines), 8)

        cond_keys = [g.condition.value for g in guidelines]
        self.assertIn(DietConditionCategory.POST_OP_ORTHOPEDIC.value, cond_keys)
        self.assertIn(DietConditionCategory.DIABETES_T2.value, cond_keys)
        self.assertIn(DietConditionCategory.HYPERTENSION.value, cond_keys)
        self.assertIn(DietConditionCategory.HEART_DISEASE_CAD.value, cond_keys)
        self.assertIn(DietConditionCategory.KIDNEY_DISEASE_CKD.value, cond_keys)
        self.assertIn(DietConditionCategory.PCOD_PCOS.value, cond_keys)
        self.assertIn(DietConditionCategory.WEIGHT_REDUCTION.value, cond_keys)

        # Verify exact PubMed PMIDs
        ortho = nutrition_rag_service.get_guideline("POST_OP_ORTHOPEDIC")
        ortho_pmids = [c.pmid for c in ortho.pubmed_citations]
        self.assertIn("34242915", ortho_pmids) # ESPEN Surgery

        dm = nutrition_rag_service.get_guideline("DIABETES_T2")
        dm_pmids = [c.pmid for c in dm.pubmed_citations]
        self.assertIn("31000505", dm_pmids) # ADA Consensus

        htn = nutrition_rag_service.get_guideline("HYPERTENSION")
        htn_pmids = [c.pmid for c in htn.pubmed_citations]
        self.assertIn("29146535", htn_pmids) # ACC/AHA Hypertension
        self.assertIn("11136953", htn_pmids) # DASH-Sodium

        ckd = nutrition_rag_service.get_guideline("KIDNEY_DISEASE_CKD")
        ckd_pmids = [c.pmid for c in ckd.pubmed_citations]
        self.assertIn("32829751", ckd_pmids) # KDOQI 2020

        pcos = nutrition_rag_service.get_guideline("PCOD_PCOS")
        pcos_pmids = [c.pmid for c in pcos.pubmed_citations]
        self.assertIn("37580162", pcos_pmids) # 2023 International PCOS

        obesity = nutrition_rag_service.get_guideline("WEIGHT_REDUCTION")
        obesity_pmids = [c.pmid for c in obesity.pubmed_citations]
        self.assertIn("27219882", obesity_pmids) # AACE Obesity

    def test_02_post_op_orthopedic_case_synthesis(self):
        """Verify orthopedic post-op nutrition provides 1.5-2.0 g/kg protein and collagen cofactors."""
        plan = nutrition_rag_service.generate_personalized_diet_plan(
            patient_name="Ramesh Verma",
            age=52,
            surgical_case="Right Knee Arthroscopy - Medial Meniscus Root Repair",
            diagnosed_conditions=[]
        )
        self.assertEqual(plan.age_group, AgeGroupCategory.MIDDLE_AGED)
        self.assertIn("1.5 - 2.0 g/kg/day", plan.combined_macro_targets.protein_g_per_kg)
        
        superfood_names = [f.food_item for f in plan.curated_superfoods]
        self.assertTrue(any("Collagen" in s or "Bone Broth" in s for s in superfood_names))
        self.assertTrue(any("Salmon" in s or "Mackerel" in s for s in superfood_names))

    def test_03_geriatric_age_wise_sarcopenia_pacing(self):
        """Verify elderly post-op patients (age >= 65) receive leucine pulse feeding protocol."""
        plan = nutrition_rag_service.generate_personalized_diet_plan(
            patient_name="Shanti Devi",
            age=72,
            surgical_case="Total Hip Arthroplasty (Ortho)",
            diagnosed_conditions=[]
        )
        self.assertEqual(plan.age_group, AgeGroupCategory.GERIATRIC_ELDERLY)
        superfood_names = [f.food_item for f in plan.curated_superfoods]
        self.assertTrue(any("Whey" in s or "Leucine" in s for s in superfood_names))
        
        # Verify ESPEN Geriatric PMID 30337166
        pmids = [c.pmid for c in plan.pubmed_references_summary]
        self.assertIn("30337166", pmids)

    def test_04_chronic_kidney_disease_protein_safety_rule(self):
        """Verify that CKD restricts protein (0.6-0.8 g/kg) and bans lethal starfruit even post-op."""
        plan = nutrition_rag_service.generate_personalized_diet_plan(
            patient_name="Vikram Rao",
            age=60,
            surgical_case="Knee Debridement",
            diagnosed_conditions=["Chronic Kidney Disease Stage 4", "Hypertension"]
        )
        # CKD rule must take precedence over high-protein loading to prevent uremic crisis
        self.assertIn("0.6 - 0.8 g/kg/day", plan.combined_macro_targets.protein_g_per_kg)
        
        prohib_names = [p.food_item for p in plan.curated_prohibited_foods]
        self.assertTrue(any("Starfruit" in p for p in prohib_names))

    def test_05_pcod_pcos_anti_androgenic_plan(self):
        """Verify PCOS diet targets hyperinsulinemia with spearmint, inositol, and flaxseeds."""
        plan = nutrition_rag_service.generate_personalized_diet_plan(
            patient_name="Pooja Sharma",
            age=26,
            surgical_case=None,
            diagnosed_conditions=["PCOD with Hirsutism and Irregular Cycles"]
        )
        superfoods = [f.food_item for f in plan.curated_superfoods]
        self.assertTrue(any("Spearmint" in s for s in superfoods))
        self.assertTrue(any("Inositol" in s or "Buckwheat" in s for s in superfoods))
        self.assertTrue(any("Flaxseeds" in s for s in superfoods))

    def test_06_weight_reduction_satiety_pacing(self):
        """Verify weight reduction diet prescribes 500-750 kcal deficit and high satiety foods."""
        plan = nutrition_rag_service.generate_personalized_diet_plan(
            patient_name="Amitabh Das",
            age=38,
            surgical_case=None,
            diagnosed_conditions=["Obesity Class 1 (BMI 31.5)"]
        )
        self.assertIn("500 - 750 kcal/day", plan.combined_macro_targets.daily_calories_guideline)
        superfoods = [f.food_item for f in plan.curated_superfoods]
        self.assertTrue(any("Boiled Potatoes" in s or "Satiety Index" in s for s in superfoods))

    def test_07_nutrition_rag_query_engine(self):
        """Verify querying the Nutrition RAG returns grounded evidence with PubMed citations."""
        res_htn = nutrition_rag_service.query_nutrition_rag(
            DietRAGQueryInput(query="What is the sodium and potassium target for hypertension in the DASH diet?")
        )
        self.assertIn("ACC/AHA", res_htn.grounded_answer)
        self.assertIn("< 1,500 mg/day", res_htn.grounded_answer)
        pmids = [c.pmid for c in res_htn.relevant_citations]
        self.assertIn("29146535", pmids)

        res_pcos = nutrition_rag_service.query_nutrition_rag(
            DietRAGQueryInput(query="What herbs or teas reduce testosterone in PCOD?")
        )
        self.assertIn("Spearmint Tea", res_pcos.grounded_answer)
        self.assertIn("5-alpha-reductase", res_pcos.grounded_answer)

    def test_08_chatbot_ai_companion_nutrition_grounding(self):
        """Verify Patient Portal Chatbot answers condition-specific diet queries with PMIDs."""
        # 1. Diabetes Query
        res_dm = self.client.post("/api/v1/portal/ai-query", json={
            "mpi_id": str(self.mpi_id),
            "question": "What diet should I eat for my diabetes and high sugar?"
        })
        self.assertEqual(res_dm.status_code, 200)
        self.assertIn("ADA Standards of Care", res_dm.json()["answer"])
        self.assertIn("PMID", res_dm.json()["answer"])
        self.assertIn("Fenugreek", res_dm.json()["answer"])

        # 2. Kidney Disease Query
        res_ckd = self.client.post("/api/v1/portal/ai-query", json={
            "mpi_id": str(self.mpi_id),
            "question": "What foods should I avoid with kidney disease CKD?"
        })
        self.assertEqual(res_ckd.status_code, 200)
        self.assertIn("KDOQI", res_ckd.json()["answer"])
        self.assertIn("Starfruit", res_ckd.json()["answer"])

        # 3. PCOD Query
        res_pcos = self.client.post("/api/v1/portal/ai-query", json={
            "mpi_id": str(self.mpi_id),
            "question": "How can diet help my PCOD and irregular periods?"
        })
        self.assertEqual(res_pcos.status_code, 200)
        self.assertIn("Spearmint", res_pcos.json()["answer"])
        self.assertIn("Inositol", res_pcos.json()["answer"])

    def test_09_api_nutrition_endpoints(self):
        """Verify REST API endpoints for guidelines, personalized plans, and RAG queries."""
        # GET /guidelines
        res_list = self.client.get("/api/v1/nutrition/guidelines")
        self.assertEqual(res_list.status_code, 200)
        self.assertGreaterEqual(len(res_list.json()), 8)

        # GET /guidelines/{condition_key}
        res_single = self.client.get("/api/v1/nutrition/guidelines/HYPERTENSION")
        self.assertEqual(res_single.status_code, 200)
        self.assertEqual(res_single.json()["condition"], "HYPERTENSION")

        # POST /personalized-plan
        res_plan = self.client.post("/api/v1/nutrition/personalized-plan", json={
            "patient_name": "Meera Sen",
            "age": 55,
            "surgical_case": "Knee Arthroscopy",
            "diagnosed_conditions": ["Type 2 Diabetes", "Hypertension"]
        })
        self.assertEqual(res_plan.status_code, 200)
        data = res_plan.json()
        self.assertEqual(data["patient_name"], "Meera Sen")
        self.assertIn("combined_macro_targets", data)
        self.assertGreaterEqual(len(data["curated_superfoods"]), 4)

        # POST /rag-query
        res_rag = self.client.post("/api/v1/nutrition/rag-query", json={
            "query": "What is the recommended protein intake for elderly patients after surgery?"
        })
        self.assertEqual(res_rag.status_code, 200)
        self.assertIn("ESPEN", res_rag.json()["grounded_answer"])
        self.assertIn("leucine", res_rag.json()["grounded_answer"].lower())
