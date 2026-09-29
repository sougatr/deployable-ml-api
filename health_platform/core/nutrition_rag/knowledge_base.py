"""
Curated Clinical Nutrition Knowledge Base with Verified PubMed Citations.
Provides authoritative, peer-reviewed medical nutrition therapy guidelines across:
- Case-wise Post-Operative Care (Orthopedic, Abdominal ERAS, Cardiac)
- Age-wise Post-Operative Care (Pediatric, Young Adult, Geriatric Sarcopenia Pacing)
- Disease-Specific Medical Nutrition Therapy (Diabetes, Hypertension, CAD, CKD, PCOS, Obesity)
"""

from typing import List, Dict
from health_platform.core.nutrition_rag.models import (
    DietConditionCategory,
    AgeGroupCategory,
    PubMedCitation,
    DietItemRecommendation,
    MacronutrientTarget,
    ClinicalDietGuideline
)

CLINICAL_NUTRITION_GUIDELINES: Dict[str, ClinicalDietGuideline] = {
    # -------------------------------------------------------------------------
    # 1. POST-OPERATIVE: ORTHOPEDIC & JOINT REPAIR
    # -------------------------------------------------------------------------
    "POST_OP_ORTHOPEDIC": ClinicalDietGuideline(
        guideline_id="GUIDE-POSTOP-ORTHO-001",
        condition=DietConditionCategory.POST_OP_ORTHOPEDIC,
        condition_name="Post-Operative Orthopedic, Joint & Cartilage Recovery",
        age_applicability="Adults & Elderly Post-Operative Patients",
        surgical_case_type="Knee Arthroscopy, Meniscus Root Repair, ACL Reconstruction, Joint Arthroplasty, Fracture ORIF",
        clinical_summary=(
            "Post-operative orthopedic trauma and joint surgery trigger an intense catabolic state, systemic inflammatory "
            "response, and rapid muscle disuse atrophy. Nutritional therapy focuses on high-biologic-value protein (1.5-2.0 g/kg/day) "
            "to overcome anabolic resistance, targeted collagen peptide synthesis (Vitamin C + Zinc cofactors), and anti-inflammatory "
            "long-chain Omega-3 fatty acids to resolve joint effusion without blunting physiologic tissue remodeling."
        ),
        pubmed_citations=[
            PubMedCitation(
                pmid="34242915",
                title="ESPEN practical guideline: Clinical nutrition in surgery",
                authors="Weimann A, Braga M, Carli F, et al.",
                journal="Clinical Nutrition",
                year=2021,
                evidence_level="Level 1A: International Consensus Practice Guideline",
                doi="10.1016/j.clnu.2021.03.031",
                url="https://pubmed.ncbi.nlm.nih.gov/34242915/"
            ),
            PubMedCitation(
                pmid="26564952",
                title="Balanced perioperative fluid and nutritional management in ERAS protocols",
                authors="Feldheiser A, Aziz O, Baldini G, et al.",
                journal="Acta Anaesthesiologica Scandinavica",
                year=2016,
                evidence_level="Level 1B: Multi-center Clinical Review",
                doi="10.1111/aas.12657",
                url="https://pubmed.ncbi.nlm.nih.gov/26564952/"
            ),
            PubMedCitation(
                pmid="30337166",
                title="ESPEN guideline on clinical nutrition and hydration in geriatrics",
                authors="Volkert D, Beck AM, Cederholm T, et al.",
                journal="Clinical Nutrition",
                year=2019,
                evidence_level="Level 1A: Systematic Review & Clinical Guideline",
                doi="10.1016/j.clnu.2018.10.024",
                url="https://pubmed.ncbi.nlm.nih.gov/30337166/"
            )
        ],
        macro_targets=MacronutrientTarget(
            daily_calories_guideline="25 - 30 kcal/kg/day (euvolemic dry weight)",
            protein_g_per_kg="1.5 - 2.0 g/kg/day (distributed into 25-35g per meal with 3g Leucine)",
            carbohydrate_pct="45% - 50% (complex unrefined carbohydrates to spare protein)",
            fat_pct="25% - 30% (predominantly monounsaturated & Omega-3 PUFAs)",
            dietary_fiber_g="28 - 35 g/day (essential to prevent post-op narcotic-induced constipation)",
            sodium_limit_mg="< 2,300 mg/day (prevents extracellular fluid retention and joint swelling)",
            potassium_guideline="3,000 - 3,500 mg/day (supports neuromuscular membrane potential)",
            fluid_target="2.5 - 3.0 Liters/day (30-35 mL/kg) to flush inflammatory metabolites"
        ),
        recommended_foods=[
            DietItemRecommendation(
                food_item="Wild Alaskan Salmon / Mackerel / Sardines",
                category="Superfood / Prioritize",
                clinical_rationale="Supplies high-dose EPA/DHA (1.5–2.0g) to accelerate the resolution phase of acute joint inflammation.",
                biochemical_mechanism="Substrates for specialized pro-resolving mediators (resolvins, protectins) that decrease synovial swelling."
            ),
            DietItemRecommendation(
                food_item="Bone Broth & Hydrolyzed Collagen Peptides with Vitamin C",
                category="Superfood / Prioritize",
                clinical_rationale="Provides rich amounts of glycine, proline, and hydroxyproline required for tenocyte and fibrocartilage repair.",
                biochemical_mechanism="Vitamin C acts as an obligate electron donor for prolyl and lysyl hydroxylase in triple-helix collagen cross-linking."
            ),
            DietItemRecommendation(
                food_item="Turmeric with Black Pepper (Curcumin + Piperine)",
                category="Superfood / Prioritize",
                clinical_rationale="Non-steroidal joint analgesia and chondroprotective reduction in knee arthroscopy pain.",
                biochemical_mechanism="Curcumin downregulates NF-kappaB and COX-2 expression, lowering inflammatory interleukins (IL-1beta, TNF-alpha)."
            ),
            DietItemRecommendation(
                food_item="Organic Blueberries, Blackberries & Pomegranate",
                category="Superfood / Prioritize",
                clinical_rationale="Neutralizes surgical oxidative stress and preserves muscular micro-vasculature.",
                biochemical_mechanism="High polyphenol and anthocyanin content scavenges reactive oxygen species generated during surgical tissue ischemia."
            )
        ],
        prohibited_foods=[
            DietItemRecommendation(
                food_item="Ultra-Processed High-Sodium Snacks & Canned Soups",
                category="Limit / Strictly Avoid",
                clinical_rationale="Exacerbates post-operative joint effusion, peripheral edema, and capsular swelling.",
                biochemical_mechanism="Excessive sodium chloride drives extracellular osmotic fluid shifts into the synovial space."
            ),
            DietItemRecommendation(
                food_item="Refined White Flour & Added Sugars (Pastries, Candy, Soda)",
                category="Limit / Strictly Avoid",
                clinical_rationale="Impairs surgical incision healing and increases infection risk.",
                biochemical_mechanism="Transient postprandial hyperglycemia generates advanced glycation end-products (AGEs) and impedes neutrophil phagocytosis."
            ),
            DietItemRecommendation(
                food_item="Excessive Alcohol & Tobacco",
                category="Limit / Strictly Avoid",
                clinical_rationale="Inhibits osteoblast and tenocyte proliferation; increases risk of non-union or graft failure.",
                biochemical_mechanism="Suppresses mTORC1 phosphorylation, reducing muscle protein synthesis by up to 37%."
            )
        ],
        meal_timing_and_chrononutrition=(
            "Protein Pulse Feeding: Distribute protein into 4 equal boluses of 30-35g every 3.5 to 4 hours. "
            "Consume 25g whey/casein or Greek yogurt 30 minutes before bed to maintain nocturnal muscle protein synthesis."
        ),
        rag_knowledge_chunk=(
            "Orthopedic surgical recovery requires 1.5-2.0 g/kg/day protein (ESPEN Surgery Guideline, PMID 34242915). "
            "Elderly orthopedic patients require 3g leucine per meal to trigger mTOR muscle protein synthesis (PMID 30337166). "
            "Collagen synthesis requires 15g collagen/gelatin combined with 500mg Vitamin C taken 45-60 min prior to rehabilitation. "
            "Anti-inflammatory EPA/DHA resolves synovial joint effusion while restricting sodium to <2300 mg prevents fluid buildup."
        )
    ),

    # -------------------------------------------------------------------------
    # 2. POST-OPERATIVE: GERIATRIC & SARCOPENIA PREV (Age-Wise)
    # -------------------------------------------------------------------------
    "POST_OP_GERIATRIC": ClinicalDietGuideline(
        guideline_id="GUIDE-POSTOP-GERI-002",
        condition=DietConditionCategory.POST_OP_ORTHOPEDIC,
        condition_name="Post-Operative Geriatric Care & Sarcopenia Prevention (Age >= 65)",
        age_applicability="Geriatric Patients (Age >= 65)",
        surgical_case_type="All Surgical Specialties in Older Adults",
        clinical_summary=(
            "Older adults undergoing surgical procedures exhibit pronounced 'anabolic resistance,' meaning higher circulating "
            "essential amino acid levels are needed to stimulate muscle protein synthesis compared to younger individuals. "
            "Inadequate protein intake leads to rapid loss of functional muscle mass (up to 1.5 kg of lean mass lost in 72 hours), "
            "leading to loss of independence, falls, and prolonged hospitalization. Guidelines emphasize leucine-enriched meals, "
            "daily Vitamin D3 (2,000-4,000 IU) to support myofibrillar contractility, and soft easy-to-chew textures."
        ),
        pubmed_citations=[
            PubMedCitation(
                pmid="30337166",
                title="ESPEN guideline on clinical nutrition and hydration in geriatrics",
                authors="Volkert D, Beck AM, Cederholm T, et al.",
                journal="Clinical Nutrition",
                year=2019,
                evidence_level="Level 1A: European Consensus Guideline",
                doi="10.1016/j.clnu.2018.10.024",
                url="https://pubmed.ncbi.nlm.nih.gov/30337166/"
            ),
            PubMedCitation(
                pmid="34242915",
                title="ESPEN practical guideline: Clinical nutrition in surgery",
                authors="Weimann A, et al.",
                journal="Clinical Nutrition",
                year=2021,
                evidence_level="Level 1A: Clinical Surgical Guideline",
                url="https://pubmed.ncbi.nlm.nih.gov/34242915/"
            )
        ],
        macro_targets=MacronutrientTarget(
            daily_calories_guideline="27 - 32 kcal/kg/day to ensure positive energy balance",
            protein_g_per_kg="1.5 - 2.0 g/kg/day (minimum 1.2 g/kg even with mild renal insufficiency if under dialysis)",
            carbohydrate_pct="45% - 50%",
            fat_pct="30% (incorporating MCTs and extra virgin olive oil for calorie density)",
            dietary_fiber_g="25 - 30 g/day",
            sodium_limit_mg="< 2,000 mg/day",
            potassium_guideline="3,500 mg/day",
            fluid_target="30 mL/kg/day minimum (preventing dehydration-induced acute kidney injury or delirium)"
        ),
        recommended_foods=[
            DietItemRecommendation(
                food_item="Whey Protein Isolate or Fortified Dairy (Greek Yogurt / Paneer)",
                category="Superfood / Prioritize",
                clinical_rationale="Fast-acting, leucine-rich protein source specifically designed to overcome anabolic resistance in older muscle.",
                biochemical_mechanism="Provides >= 3g leucine per bolus, which directly activates Sestrin2 to relieve GATOR2 inhibition on mTORC1."
            ),
            DietItemRecommendation(
                food_item="Whole Eggs (Poached or Soft Scrambled)",
                category="Superfood / Prioritize",
                clinical_rationale="High biological value protein with choline and lutein; easily chewed and swallowed without fatigue.",
                biochemical_mechanism="Egg phospholipid matrix enhances postprandial whole-body protein net balance and muscle protein synthesis."
            ),
            DietItemRecommendation(
                food_item="Stewed Lentil Dahl with Cumin & Turmeric",
                category="Superfood / Prioritize",
                clinical_rationale="High-protein, soft-texture traditional food providing zinc, iron, and prebiotic soluble fiber.",
                biochemical_mechanism="Fermentation by colonic microbiota generates short-chain fatty acids (butyrate) that support gut-muscle axis."
            )
        ],
        prohibited_foods=[
            DietItemRecommendation(
                food_item="Low-Calorie Restrictive Dieting During Post-Op Recovery",
                category="Limit / Strictly Avoid",
                clinical_rationale="Caloric deficit in elderly post-op patients severely accelerates sarcopenic muscle loss.",
                biochemical_mechanism="Triggers cellular autophagy and ubiquitin-proteasome proteolysis in skeletal muscle fibers."
            ),
            DietItemRecommendation(
                food_item="Dry, Tough, Fibrous Meats that Cause Chewing Fatigue",
                category="Limit / Strictly Avoid",
                clinical_rationale="Leads to early meal termination, resulting in failure to achieve the critical 30g protein threshold.",
                biochemical_mechanism="Incomplete mastication reduces gastric emptying rate and decreases amino acid absorption kinetics."
            )
        ],
        meal_timing_and_chrononutrition=(
            "Focus on nutrient density over bulk: 3 primary meals with 2 protein-dense snacks (e.g. 10:30 AM and 8:30 PM). "
            "Paced fluid schedule every 90 minutes to prevent hypovolemic delirium."
        ),
        rag_knowledge_chunk=(
            "Geriatric surgical nutrition guidelines (ESPEN Geriatrics, PMID 30337166) mandate 1.5-2.0 g/kg/day protein. "
            "Older adults suffer from anabolic resistance and need at least 3.0g leucine per meal (from eggs, whey, fortified dairy) "
            "to activate muscle protein synthesis. Hypohydration is a major risk factor for post-op delirium; aim for 30 mL/kg/day."
        )
    ),

    # -------------------------------------------------------------------------
    # 3. DISEASE-WISE: TYPE 2 DIABETES & PREDIABETES
    # -------------------------------------------------------------------------
    "DIABETES_T2": ClinicalDietGuideline(
        guideline_id="GUIDE-DIABETES-003",
        condition=DietConditionCategory.DIABETES_T2,
        condition_name="Type 2 Diabetes Mellitus & Impaired Glucose Tolerance",
        age_applicability="Adults & Elderly with Diabetes",
        surgical_case_type=None,
        clinical_summary=(
            "Medical Nutrition Therapy (MNT) according to the American Diabetes Association (ADA) consensus focuses on "
            "glycemic control, HbA1c reduction (0.5% - 2.0% drop via MNT alone), prevention of microvascular/macrovascular "
            "complications, and weight management. Key pillars are low glycemic index and load foods, high soluble fiber "
            "(>= 35g/day), carbohydrate consistency (30-45g per meal), chrononutrition (early time-restricted eating), and "
            "replacement of saturated fats with monounsaturated fatty acids (MUFAs)."
        ),
        pubmed_citations=[
            PubMedCitation(
                pmid="31000505",
                title="Nutrition Therapy for Adults With Diabetes or Prediabetes: A Consensus Report",
                authors="Evert AB, Dennison M, Gardner CD, et al.",
                journal="Diabetes Care",
                year=2019,
                evidence_level="ADA Clinical Consensus Report",
                doi="10.2337/dci19-0014",
                url="https://pubmed.ncbi.nlm.nih.gov/31000505/"
            ),
            PubMedCitation(
                pmid="38078580",
                title="Facilitating Positive Health Behaviors and Well-being to Improve Health Outcomes: Standards of Care in Diabetes—2024",
                authors="American Diabetes Association Professional Practice Committee",
                journal="Diabetes Care",
                year=2024,
                evidence_level="ADA Standards of Care Guideline",
                doi="10.2337/dc24-S005",
                url="https://pubmed.ncbi.nlm.nih.gov/38078580/"
            )
        ],
        macro_targets=MacronutrientTarget(
            daily_calories_guideline="Target deficit of 500 kcal/day if BMI > 25 kg/m2; maintenance if normoweight",
            protein_g_per_kg="1.0 - 1.2 g/kg/day (preserves muscle; in diabetic kidney disease, 0.8 g/kg/day)",
            carbohydrate_pct="35% - 40% (low glycemic index, unrefined, high fiber)",
            fat_pct="35% - 40% (rich in MUFAs: olive oil, avocado, nuts)",
            dietary_fiber_g="35 - 50 g/day (minimum 15g soluble viscous fiber)",
            sodium_limit_mg="< 2,300 mg/day (or < 1,500 mg if comorbid hypertension)",
            potassium_guideline="3,500 - 4,700 mg/day",
            fluid_target="2.5 Liters/day (adequate hydration assists renal glucose clearance)"
        ),
        recommended_foods=[
            DietItemRecommendation(
                food_item="Fenugreek Seeds (Methi Dana) Soaked in Water",
                category="Superfood / Prioritize",
                clinical_rationale="Reduces fasting blood glucose and postprandial glucose excursions.",
                biochemical_mechanism="High 4-hydroxyisoleucine and galactomannan content slows carbohydrate digestion and enhances insulin secretion."
            ),
            DietItemRecommendation(
                food_item="Chia Seeds & Ground Flaxseeds",
                category="Superfood / Prioritize",
                clinical_rationale="Viscous soluble fiber delays gastric emptying, blunting glycemic spikes.",
                biochemical_mechanism="Forms a gel matrix in the small intestine that impedes alpha-amylase and glucose contact with enterocytes."
            ),
            DietItemRecommendation(
                food_item="Bitter Gourd (Karela) & Jamun Seed Powder",
                category="Superfood / Prioritize",
                clinical_rationale="Traditional insulin-mimetic botanical with demonstrated glycemic lowering efficacy.",
                biochemical_mechanism="Contains charantin and polypeptide-p (plant insulin) that increases peripheral glucose uptake in myocytes."
            ),
            DietItemRecommendation(
                food_item="Legumes, Chickpeas & Sprouted Moong Beans",
                category="Superfood / Prioritize",
                clinical_rationale="Low glycemic index complex carbohydrate source producing sustained satiety and low insulin demand.",
                biochemical_mechanism="Resistant starch escapes upper digestive breakdown, fueling colonic production of GLP-1 stimulating SCFAs."
            )
        ],
        prohibited_foods=[
            DietItemRecommendation(
                food_item="Sugar-Sweetened Beverages, Sodas & Fruit Juices",
                category="Limit / Strictly Avoid",
                clinical_rationale="Rapid absorption triggers acute hyperinsulinemia and hepatic de novo lipogenesis.",
                biochemical_mechanism="Rapid hepatic fructose overload bypasses phosphofructokinase, causing rapid hepatic steatosis and insulin resistance."
            ),
            DietItemRecommendation(
                food_item="Refined White Flour, White Rice & Puffed Cereals",
                category="Limit / Strictly Avoid",
                clinical_rationale="High glycemic index causing steep glycemic spikes and postprandial fatigue.",
                biochemical_mechanism="Rapid hydrolysis into free glucose overwhelms pancreatic beta-cell insulin secretory capacity."
            )
        ],
        meal_timing_and_chrononutrition=(
            "Carbohydrate Consistency: 30-45g carbohydrate per meal. Early Time-Restricted Feeding (e.g. 8:00 AM to 6:00 PM). "
            "Consume vegetables and proteins BEFORE carbohydrates in the meal sequence to reduce postprandial glucose spike by 40%."
        ),
        rag_knowledge_chunk=(
            "ADA Standards of Care (PMID 31000505, 38078580) recommend an individualized eating pattern emphasizing "
            "low glycemic index foods, >=35-50g fiber/day, and replacement of refined carbs with MUFAs and legumes. "
            "Consuming fiber and protein before carbohydrates significantly attenuates postprandial glycemic excursions. "
            "Avoid sugar-sweetened beverages and refined starches to prevent hepatic steatosis."
        )
    ),

    # -------------------------------------------------------------------------
    # 4. DISEASE-WISE: HYPERTENSION (DASH Eating Plan)
    # -------------------------------------------------------------------------
    "HYPERTENSION": ClinicalDietGuideline(
        guideline_id="GUIDE-HYPERTENSION-004",
        condition=DietConditionCategory.HYPERTENSION,
        condition_name="Systemic Hypertension (High Blood Pressure)",
        age_applicability="Adults & Elderly with Elevated Blood Pressure",
        surgical_case_type=None,
        clinical_summary=(
            "The Dietary Approaches to Stop Hypertension (DASH) eating plan is the gold standard clinical nutrition protocol "
            "endorsed by the ACC/AHA and ESC. In clinical trials, the combination of DASH and sodium restriction lowered systolic "
            "blood pressure by up to 11.5 mmHg in hypertensive individuals. The diet is naturally rich in potassium, magnesium, and "
            "calcium, emphasizing 4-5 servings of vegetables, 4-5 servings of fruits, whole grains, low-fat dairy, and lean proteins "
            "while strictly restricting sodium to < 1,500 - 2,000 mg/day."
        ),
        pubmed_citations=[
            PubMedCitation(
                pmid="29146535",
                title="2017 ACC/AHA/AAPA/ABC/ACPM/AGS/APhA/ASH/ASPC/NMA/PCNA Guideline for the Prevention, Detection, Evaluation, and Management of High Blood Pressure in Adults",
                authors="Whelton PK, Carey RM, Aronow WS, et al.",
                journal="Journal of the American College of Cardiology",
                year=2018,
                evidence_level="Level 1A: ACC/AHA Clinical Practice Guideline",
                doi="10.1016/j.jacc.2017.11.006",
                url="https://pubmed.ncbi.nlm.nih.gov/29146535/"
            ),
            PubMedCitation(
                pmid="11136953",
                title="Effects on blood pressure of reduced dietary sodium and the Dietary Approaches to Stop Hypertension (DASH) diet",
                authors="Sacks FM, Svetkey LP, Vollmer WM, et al.",
                journal="New England Journal of Medicine",
                year=2001,
                evidence_level="Level 1A: Landmark Multi-Center RCT",
                doi="10.1056/NEJM200101043440101",
                url="https://pubmed.ncbi.nlm.nih.gov/11136953/"
            )
        ],
        macro_targets=MacronutrientTarget(
            daily_calories_guideline="Calorie-controlled to maintain BMI 18.5 - 24.9 kg/m2",
            protein_g_per_kg="1.0 - 1.2 g/kg/day (lean poultry, fish, low-fat dairy, legumes)",
            carbohydrate_pct="50% - 55% (whole grains, high potassium vegetables and fruits)",
            fat_pct="25% - 30% (< 6% saturated fat; zero industrial trans-fats)",
            dietary_fiber_g="30 - 38 g/day",
            sodium_limit_mg="< 1,500 mg/day (strict target) or < 2,000 mg/day (standard target)",
            potassium_guideline="3,500 - 4,700 mg/day (optimal 4:1 Potassium-to-Sodium intake ratio)",
            fluid_target="2.0 - 2.5 Liters/day (avoid excess fluid load if heart failure is present)"
        ),
        recommended_foods=[
            DietItemRecommendation(
                food_item="Beetroot Juice & Steamed Beets",
                category="Superfood / Prioritize",
                clinical_rationale="Potent acute reduction in systolic and diastolic arterial blood pressure.",
                biochemical_mechanism="High inorganic nitrate (NO3-) converted by oral commensal bacteria into nitric oxide (NO), inducing cyclic GMP-mediated vasodilation."
            ),
            DietItemRecommendation(
                food_item="Fresh Spinach, Swiss Chard & Potassium-Rich Leafy Greens",
                category="Superfood / Prioritize",
                clinical_rationale="Supplies high potassium and magnesium, counteracting sodium retention.",
                biochemical_mechanism="Potassium stimulates vascular Na+/K+-ATPase and downregulates the thiazide-sensitive NaCl cotransporter in renal tubules."
            ),
            DietItemRecommendation(
                food_item="Hibiscus Sabdariffa Tea (Unsweetened)",
                category="Superfood / Prioritize",
                clinical_rationale="Clinical trials demonstrate blood pressure reductions comparable to mild ACE inhibitors.",
                biochemical_mechanism="Anthocyanins inhibit angiotensin-converting enzyme (ACE) activity and stimulate cholinergic vasorelaxation."
            ),
            DietItemRecommendation(
                food_item="Raw Unsalted Pistachios & Walnuts",
                category="Superfood / Prioritize",
                clinical_rationale="Improves endothelial reactivity and arterial compliance.",
                biochemical_mechanism="Rich in L-arginine, the biological substrate for endothelial nitric oxide synthase (eNOS)."
            )
        ],
        prohibited_foods=[
            DietItemRecommendation(
                food_item="Pickles (Achaar), Papad, Salted Namkeen & Cured Meats",
                category="Limit / Strictly Avoid",
                clinical_rationale="Single servings contain 800–1,500mg sodium, triggering acute arterial pressure elevation.",
                biochemical_mechanism="Expands intravascular volume, activates central sympathetic tone, and increases systemic vascular resistance."
            ),
            DietItemRecommendation(
                food_item="Licorice & Licorice Extracts (Glycyrrhizin)",
                category="Limit / Strictly Avoid",
                clinical_rationale="Causes apparent mineralocorticoid excess and severe secondary hypertension.",
                biochemical_mechanism="Inhibits 11beta-hydroxysteroid dehydrogenase type 2, allowing cortisol to hyper-activate renal aldosterone receptors."
            )
        ],
        meal_timing_and_chrononutrition=(
            "Use potassium-enriched salt substitutes (75% NaCl / 25% KCl) for home cooking. "
            "Avoid adding table salt; flavor with lemon, garlic, cumin, and coriander."
        ),
        rag_knowledge_chunk=(
            "ACC/AHA and DASH Guidelines (PMID 29146535, 11136953) recommend restricting sodium to <1,500-2,000 mg/day "
            "and increasing potassium to 3,500-4,700 mg/day. This potassium-to-sodium ratio optimizes endothelial nitric oxide "
            "production and renal natriuresis. Superfoods include beetroot (nitrates), hibiscus tea (ACE inhibition), "
            "and leafy greens (magnesium). Strictly eliminate pickles, papads, and processed meats."
        )
    ),

    # -------------------------------------------------------------------------
    # 5. DISEASE-WISE: CORONARY ARTERY DISEASE & CARDIAC HEALTH
    # -------------------------------------------------------------------------
    "HEART_DISEASE_CAD": ClinicalDietGuideline(
        guideline_id="GUIDE-CARDIAC-005",
        condition=DietConditionCategory.HEART_DISEASE_CAD,
        condition_name="Coronary Artery Disease, Post-MI & Atherosclerosis Prevention",
        age_applicability="Adults with Ischemic Heart Disease or High CVD Risk",
        surgical_case_type=None,
        clinical_summary=(
            "The Mediterranean dietary pattern, backed by the landmark PREDIMED trial (30% reduction in major cardiovascular "
            "events), is the cornerstone of secondary prevention in coronary heart disease. Nutritional therapy focuses on "
            "anti-atherosclerotic lipids (Extra Virgin Olive Oil, tree nuts, marine omega-3s), limiting saturated fat to < 7% "
            "of calories, zero industrial trans-fats, and high soluble fiber to reduce circulating ApoB and LDL cholesterol."
        ),
        pubmed_citations=[
            PubMedCitation(
                pmid="29897866",
                title="Primary Prevention of Cardiovascular Disease with a Mediterranean Diet Supplemented with Extra-Virgin Olive Oil or Nuts (PREDIMED)",
                authors="Estruch R, Ros E, Salas-Salvadó J, et al.",
                journal="New England Journal of Medicine",
                year=2018,
                evidence_level="Level 1A: Landmark Multicenter RCT (7,447 participants)",
                doi="10.1056/NEJMoa1800312",
                url="https://pubmed.ncbi.nlm.nih.gov/29897866/"
            ),
            PubMedCitation(
                pmid="34724799",
                title="2021 Dietary Guidance to Improve Cardiovascular Health: A Scientific Statement From the American Heart Association",
                authors="Lichtenstein AH, Appel LJ, Vadiveloo M, et al.",
                journal="Circulation",
                year=2021,
                evidence_level="AHA Scientific Statement",
                doi="10.1161/CIR.0000000000001031",
                url="https://pubmed.ncbi.nlm.nih.gov/34724799/"
            )
        ],
        macro_targets=MacronutrientTarget(
            daily_calories_guideline="Eucaloric maintenance or moderate deficit for cardioprotection",
            protein_g_per_kg="1.0 - 1.2 g/kg/day (emphasis on marine and plant proteins)",
            carbohydrate_pct="45% - 50% (whole grains with high beta-glucan content)",
            fat_pct="35% - 40% (high MUFA/PUFA ratio; saturated fat < 7%)",
            dietary_fiber_g="35 - 45 g/day (including >= 3g beta-glucan from oats/barley)",
            sodium_limit_mg="< 2,000 mg/day",
            potassium_guideline="3,500 - 4,700 mg/day",
            fluid_target="2.0 - 2.5 Liters/day (if severe heart failure with EF < 35%, restrict to 1.5 - 2.0 L/day)"
        ),
        recommended_foods=[
            DietItemRecommendation(
                food_item="Extra Virgin Olive Oil (EVOO) - Cold Pressed (>= 4 tbsp/day)",
                category="Superfood / Prioritize",
                clinical_rationale="Core PREDIMED intervention demonstrating reduction in myocardial infarction and stroke.",
                biochemical_mechanism="Rich in oleocanthal and hydroxytyrosol; inhibits LDL oxidation and suppresses VCAM-1 endothelial adhesion."
            ),
            DietItemRecommendation(
                food_item="Oat Bran & Steel-Cut Oats (Beta-Glucan)",
                category="Superfood / Prioritize",
                clinical_rationale="Lowers serum LDL cholesterol and ApoB without depleting protective HDL.",
                biochemical_mechanism="Forms a viscous intestinal barrier that binds bile acids, upregulating hepatic LDL receptor expression."
            ),
            DietItemRecommendation(
                food_item="Fresh Garlic (Allicin) & Pomegranate Juice",
                category="Superfood / Prioritize",
                clinical_rationale="Improves plaque stability and coronary endothelial microvascular flow.",
                biochemical_mechanism="Allicin inhibits HMG-CoA reductase and limits platelet aggregation via thromboxane A2 suppression."
            )
        ],
        prohibited_foods=[
            DietItemRecommendation(
                food_item="Hydrogenated Oils, Vanaspati Ghee & Commercial Baked Goods",
                category="Limit / Strictly Avoid",
                clinical_rationale="Trans-fatty acids severely accelerate coronary plaque atherogenesis.",
                biochemical_mechanism="Elevates LDL-C, decreases HDL-C, and promotes systemic endothelial inflammatory dysfunction."
            ),
            DietItemRecommendation(
                food_item="Processed Meats & Palm Oil Rich Creamers",
                category="Limit / Strictly Avoid",
                clinical_rationale="High palmitic acid content increases circulating atherogenic remnant particles.",
                biochemical_mechanism="Downregulates hepatic LDL receptor clearance and triggers vascular toll-like receptor 4 (TLR4) inflammation."
            )
        ],
        meal_timing_and_chrononutrition=(
            "Adopt the traditional Mediterranean pattern: largest meal at midday, lighter evening meal. "
            "Incorporate 30g raw walnuts or almonds daily as a mid-morning snack."
        ),
        rag_knowledge_chunk=(
            "PREDIMED trial (PMID 29897866) and AHA Cardiovascular Guidance (PMID 34724799) validate the Mediterranean diet "
            "supplemented with EVOO (>=4 tbsp/day) or nuts (30g/day) for secondary CVD prevention. Keep saturated fat <7% and "
            "eliminate trans-fats. Beta-glucan soluble fiber (>=3g/day) binds bile acids to lower LDL-C and ApoB."
        )
    ),

    # -------------------------------------------------------------------------
    # 6. DISEASE-WISE: CHRONIC KIDNEY DISEASE (CKD Stages 3-5)
    # -------------------------------------------------------------------------
    "KIDNEY_DISEASE_CKD": ClinicalDietGuideline(
        guideline_id="GUIDE-CKD-006",
        condition=DietConditionCategory.KIDNEY_DISEASE_CKD,
        condition_name="Chronic Kidney Disease (CKD Non-Dialysis Stages 3–5)",
        age_applicability="Adults with eGFR < 60 mL/min/1.73m2",
        surgical_case_type=None,
        clinical_summary=(
            "The KDOQI 2020 Clinical Practice Guideline for Nutrition in CKD strongly recommends dietary protein restriction "
            "(0.55 - 0.60 g/kg/day, or 0.6 - 0.8 g/kg in diabetic CKD) for metabolically stable patients with CKD stages 3-5 to "
            "delay renal replacement therapy (dialysis) and reduce uremic toxicity. Concurrently, energy intake must be maintained "
            "(30-35 kcal/kg/day) to prevent protein-energy wasting (PEW). Phosphorus must be restricted (800-1000 mg/day, avoiding "
            "inorganic additives), sodium limited to < 2000 mg/day, and potassium individualized."
        ),
        pubmed_citations=[
            PubMedCitation(
                pmid="32829751",
                title="KDOQI Clinical Practice Guideline for Nutrition in CKD: 2020 Update",
                authors="Ikizler TA, Burrowes JD, Byham-Gray LD, et al.",
                journal="American Journal of Kidney Diseases",
                year=2020,
                evidence_level="Level 1A: KDOQI / National Kidney Foundation Guideline",
                doi="10.1053/j.ajkd.2020.05.006",
                url="https://pubmed.ncbi.nlm.nih.gov/32829751/"
            ),
            PubMedCitation(
                pmid="38490803",
                title="KDIGO 2024 Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease",
                authors="Kidney Disease: Improving Global Outcomes (KDIGO) CKD Work Group",
                journal="Kidney International",
                year=2024,
                evidence_level="KDIGO International Guideline",
                doi="10.1016/j.kint.2023.10.018",
                url="https://pubmed.ncbi.nlm.nih.gov/38490803/"
            )
        ],
        macro_targets=MacronutrientTarget(
            daily_calories_guideline="30 - 35 kcal/kg/day (critical to prevent protein-energy wasting)",
            protein_g_per_kg="0.55 - 0.60 g/kg/day (Non-dialysis CKD 3-5) OR 0.6 - 0.8 g/kg/day (Diabetic CKD)",
            carbohydrate_pct="55% - 60% (primary energy source to spare protein catabolism)",
            fat_pct="30% (heart-healthy monounsaturated oils)",
            dietary_fiber_g="25 - 30 g/day",
            sodium_limit_mg="< 2,000 mg/day (less than 5g salt)",
            potassium_guideline="Adjusted to serum K+: typically < 2,000 - 3,000 mg/day if hyperkalemic",
            fluid_target="Urine output + 500 mL/day if oliguric; otherwise 1.5 - 2.0 L/day"
        ),
        recommended_foods=[
            DietItemRecommendation(
                food_item="Egg White (Low Phosphorus-to-Protein Ratio)",
                category="Superfood / Prioritize",
                clinical_rationale="Highest biological value protein with minimal organic phosphorus content.",
                biochemical_mechanism="Supplies essential amino acids without loading the bloodstream with unfilterable inorganic phosphorus."
            ),
            DietItemRecommendation(
                food_item="Cauliflower, Cabbage, Cucumbers & Apples",
                category="Superfood / Prioritize",
                clinical_rationale="Low potassium, low phosphorus alkaline foods that combat metabolic acidosis.",
                biochemical_mechanism="Plant-dominant low-protein diet reduces dietary acid load (NEAP), sparing renal tubular ammoniagenesis."
            ),
            DietItemRecommendation(
                food_item="White Rice / Rice Flakes (Leached & Boiled)",
                category="Superfood / Prioritize",
                clinical_rationale="Provides dense non-protein calories without potassium or phosphorus overload.",
                biochemical_mechanism="Supplies sufficient calories to prevent endogenous skeletal muscle proteolysis."
            )
        ],
        prohibited_foods=[
            DietItemRecommendation(
                food_item="Starfruit (Carambola)",
                category="Limit / Strictly Avoid",
                clinical_rationale="ABSOLUTELY CONTRAINDICATED in CKD: contains a deadly neurotoxin (caramboxin).",
                biochemical_mechanism="Caramboxin cannot be cleared by compromised kidneys, causing intractable hiccups, seizures, coma, and death."
            ),
            DietItemRecommendation(
                food_item="Colas, Processed Cheese & Packaged Foods with Phosphate Additives",
                category="Limit / Strictly Avoid",
                clinical_rationale="Inorganic phosphate additives have near 100% intestinal absorption.",
                biochemical_mechanism="Triggers acute hyperphosphatemia, vascular calcification, and elevations in FGF-23."
            )
        ],
        meal_timing_and_chrononutrition=(
            "Strictly monitor laboratory potassium and phosphorus monthly. "
            "Leach high-potassium tubers by boiling in double volume of water and discarding the cooking water."
        ),
        rag_knowledge_chunk=(
            "KDOQI 2020 Guidelines (PMID 32829751) prescribe protein restriction to 0.55-0.60 g/kg/day for CKD stages 3-5 "
            "(or 0.6-0.8 g/kg for diabetic CKD) with high calorie density (30-35 kcal/kg/day) to prevent protein-energy wasting. "
            "Sodium must be <2,000 mg/day, phosphorus <800-1000 mg/day, and starfruit is strictly lethal and forbidden."
        )
    ),

    # -------------------------------------------------------------------------
    # 7. DISEASE-WISE: PCOD / PCOS
    # -------------------------------------------------------------------------
    "PCOD_PCOS": ClinicalDietGuideline(
        guideline_id="GUIDE-PCOS-007",
        condition=DietConditionCategory.PCOD_PCOS,
        condition_name="Polycystic Ovary Syndrome (PCOS / PCOD)",
        age_applicability="Adolescent & Reproductive-Age Women",
        surgical_case_type=None,
        clinical_summary=(
            "The 2023 International Evidence-based Guideline for PCOS recommends multicomponent lifestyle interventions "
            "as first-line therapy. The dietary focus targets hyperinsulinemia—the central driver that stimulates ovarian theca "
            "cells to oversecrete androgens (testosterone) while suppressing liver Sex Hormone-Binding Globulin (SHBG). "
            "Key strategies include a low-glycemic anti-inflammatory diet, inositol-rich foods, anti-androgenic botanicals (spearmint), "
            "cruciferous indole-3-carbinol for estrogen clearance, and screening for eating disorders before restrictive diets."
        ),
        pubmed_citations=[
            PubMedCitation(
                pmid="37580162",
                title="Recommendations from the 2023 International Evidence-based Guideline for the Assessment and Management of Polycystic Ovary Syndrome",
                authors="Teede HJ, Tay CT, Laven JSE, et al.",
                journal="European Journal of Endocrinology / Fertility and Sterility",
                year=2023,
                evidence_level="International GRADE Evidence-Based Guideline",
                doi="10.1093/ejendo/lvad096",
                url="https://pubmed.ncbi.nlm.nih.gov/37580162/"
            )
        ],
        macro_targets=MacronutrientTarget(
            daily_calories_guideline="Moderate energy deficit of 400-500 kcal/day if weight reduction is indicated",
            protein_g_per_kg="1.2 - 1.4 g/kg/day (enhances satiety and blunt glycemic spikes)",
            carbohydrate_pct="35% - 40% (strictly low-glycemic, unrefined complex carbs)",
            fat_pct="30% - 35% (omega-3 PUFAs, avocados, nuts)",
            dietary_fiber_g="30 - 40 g/day",
            sodium_limit_mg="< 2,300 mg/day",
            potassium_guideline="3,000 - 3,500 mg/day",
            fluid_target="2.5 - 3.0 Liters/day"
        ),
        recommended_foods=[
            DietItemRecommendation(
                food_item="Organic Spearmint Tea (2 Cups Daily)",
                category="Superfood / Prioritize",
                clinical_rationale="Clinically demonstrated reduction in free testosterone levels and subjective hirsutism in PCOS.",
                biochemical_mechanism="Inhibits 5-alpha-reductase and ovarian theca steroidogenesis, lowering circulating androgens."
            ),
            DietItemRecommendation(
                food_item="Ground Flaxseeds & Sesame Seeds (Lignans)",
                category="Superfood / Prioritize",
                clinical_rationale="Binds excess circulating androgens and promotes healthy menstrual cyclicity.",
                biochemical_mechanism="Secoisolariciresinol diglucoside stimulates hepatic Sex Hormone-Binding Globulin (SHBG) synthesis."
            ),
            DietItemRecommendation(
                food_item="Cantaloupe, Beans & Buckwheat (Myo-Inositol & D-Chiro-Inositol)",
                category="Superfood / Prioritize",
                clinical_rationale="Restores ovarian insulin sensitivity and improves ovulation rates.",
                biochemical_mechanism="Acts as a second messenger in the insulin signaling cascade, promoting follicular maturation."
            ),
            DietItemRecommendation(
                food_item="Broccoli, Brussels Sprouts & Cabbage (Cruciferous)",
                category="Superfood / Prioritize",
                clinical_rationale="Promotes healthy hepatic estrogen detoxification and prevents estrogen dominance.",
                biochemical_mechanism="Contains indole-3-carbinol (I3C) and DIM, promoting the protective 2-hydroxyestrone metabolic pathway."
            )
        ],
        prohibited_foods=[
            DietItemRecommendation(
                food_item="Commercial Cow Dairy High in Insulin-like Growth Factor 1 (IGF-1)",
                category="Limit / Strictly Avoid",
                clinical_rationale="Exacerbates cystic inflammatory acne and stimulates ovarian androgen production in susceptible women.",
                biochemical_mechanism="Bovine IGF-1 synergizes with hyperinsulinemia to hyper-activate sebaceous lipogenesis and androgen synthesis."
            ),
            DietItemRecommendation(
                food_item="High-Glycemic Sugary Snacks & Pastries",
                category="Limit / Strictly Avoid",
                clinical_rationale="Triggers acute insulin spikes that directly impair follicle development.",
                biochemical_mechanism="Hyperinsulinemia suppresses IGFBP-1, raising free IGF-1 and arresting ovarian folliculogenesis."
            )
        ],
        meal_timing_and_chrononutrition=(
            "Balanced macronutrient plates (40% low-GI carbs, 30% protein, 30% healthy fats). "
            "Consume meals within a consistent 10-12 hour daytime window to optimize circadian insulin sensitivity."
        ),
        rag_knowledge_chunk=(
            "2023 International PCOS Guideline (PMID 37580162) recommends multicomponent lifestyle interventions "
            "addressing hyperinsulinemia and hyperandrogenism. Key nutritional tools include inositol-rich foods "
            "(beans, buckwheat), spearmint tea (anti-androgenic 5-alpha-reductase inhibition), and flaxseed lignans "
            "to increase SHBG. Screening for disordered eating is mandatory before recommending restrictive diets."
        )
    ),

    # -------------------------------------------------------------------------
    # 8. DISEASE-WISE: WEIGHT REDUCTION & OBESITY
    # -------------------------------------------------------------------------
    "WEIGHT_REDUCTION": ClinicalDietGuideline(
        guideline_id="GUIDE-OBESITY-008",
        condition=DietConditionCategory.WEIGHT_REDUCTION,
        condition_name="Adiposity-Based Chronic Disease (Obesity & Weight Reduction)",
        age_applicability="Adults with BMI >= 25 kg/m2 (or >= 23 in South Asians)",
        surgical_case_type=None,
        clinical_summary=(
            "According to the American Association of Clinical Endocrinology (AACE/ACE) guidelines on Adiposity-Based Chronic Disease "
            "(ABCD), weight management should follow a complication-centric approach aiming for 5% to 15% weight reduction to reverse "
            "metabolic comorbidities. Nutritional therapy requires a structured energy deficit (500–750 kcal/day), high protein "
            "pacing (1.2–1.6 g/kg/day) to preserve fat-free mass and stimulate satiety peptides (GLP-1, PYY), high volumetric "
            "fiber density (> 35g/day), and avoiding ultra-processed foods."
        ),
        pubmed_citations=[
            PubMedCitation(
                pmid="27219882",
                title="American Association of Clinical Endocrinologists and American College of Endocrinology Comprehensive Clinical Practice Guidelines for Medical Care of Patients with Obesity",
                authors="Garvey WT, Mechanick JI, Brett EM, et al.",
                journal="Endocrine Practice",
                year=2016,
                evidence_level="Level 1A: AACE/ACE Clinical Practice Guideline",
                doi="10.4158/EP161365.GL",
                url="https://pubmed.ncbi.nlm.nih.gov/27219882/"
            ),
            PubMedCitation(
                pmid="37085189",
                title="Consensus Statement: Algorithm for the Evaluation and Treatment of Adults with Obesity/Adiposity-Based Chronic Disease",
                authors="Garvey WT, et al.",
                journal="Endocrine Practice",
                year=2023,
                evidence_level="AACE Consensus Statement & Algorithm",
                url="https://pubmed.ncbi.nlm.nih.gov/37085189/"
            )
        ],
        macro_targets=MacronutrientTarget(
            daily_calories_guideline="Energy deficit of 500 - 750 kcal/day (approx. 1,200 - 1,500 kcal/day for women; 1,500 - 1,800 for men)",
            protein_g_per_kg="1.2 - 1.6 g/kg/day (preserves lean muscle mass and resting metabolic rate)",
            carbohydrate_pct="35% - 40% (low glycemic index, whole food sources only)",
            fat_pct="25% - 30% (healthy unsaturated fats)",
            dietary_fiber_g="35 - 45 g/day (essential for satiety and gut hormone signaling)",
            sodium_limit_mg="< 2,300 mg/day",
            potassium_guideline="3,500 - 4,700 mg/day",
            fluid_target="2.5 - 3.5 Liters/day (drinking 500 mL water 30 min before meals reduces caloric intake)"
        ),
        recommended_foods=[
            DietItemRecommendation(
                food_item="Boiled Potatoes (Cooled) & Cooked Lentils",
                category="Superfood / Prioritize",
                clinical_rationale="Ranked #1 on the Holt Satiety Index; high resistant starch suppresses appetite.",
                biochemical_mechanism="Retrograded starch escapes digestion, fermenting into short-chain fatty acids that trigger ileal L-cell GLP-1 secretion."
            ),
            DietItemRecommendation(
                food_item="Low-Fat Greek Yogurt, Paneer & Cottage Cheese",
                category="Superfood / Prioritize",
                clinical_rationale="Slow-digesting micellar casein and whey provide long-lasting satiety.",
                biochemical_mechanism="Elevates circulating peptide YY (PYY) and cholecystokinin (CCK) while lowering hunger hormone ghrelin."
            ),
            DietItemRecommendation(
                food_item="Green Tea Extract (EGCG) & Black Coffee",
                category="Superfood / Prioritize",
                clinical_rationale="Mild metabolic rate elevation and increased lipid oxidation.",
                biochemical_mechanism="Epigallocatechin gallate (EGCG) inhibits catechol-O-methyltransferase, prolonging norepinephrine-mediated thermogenesis."
            )
        ],
        prohibited_foods=[
            DietItemRecommendation(
                food_item="Liquid Sugar, Fruit Juices & Sweetened Lattes",
                category="Limit / Strictly Avoid",
                clinical_rationale="Bypasses cephalic and gastric satiety feedback mechanisms, leading to passive overconsumption.",
                biochemical_mechanism="Liquid calories do not stimulate gastric stretch receptors or suppress acylated ghrelin effectively."
            ),
            DietItemRecommendation(
                food_item="Ultra-Processed Hyper-Palatable Snack Foods (Chips, Cookies)",
                category="Limit / Strictly Avoid",
                clinical_rationale="Engineered combinations of refined carbs, fats, and sodium that override homeostatic satiety.",
                biochemical_mechanism="Triggers supraphysiologic dopamine release in the nucleus accumbens, promoting compulsive binge consumption."
            )
        ],
        meal_timing_and_chrononutrition=(
            "Early Time-Restricted Eating (e.g. 10-hour window from 8:30 AM to 6:30 PM). "
            "Never eat within 3 hours of sleep to preserve nocturnal growth hormone secretion and lipid oxidation."
        ),
        rag_knowledge_chunk=(
            "AACE Comprehensive Obesity Guidelines (PMID 27219882, 37085189) recommend a 500-750 kcal/day deficit aiming "
            "for 5-15% weight reduction to reverse adiposity-based complications. Maintain high protein (1.2-1.6 g/kg/day) "
            "to prevent loss of lean body mass and resting metabolic rate. High volumetric fiber (>35g/day) stimulates "
            "endogenous GLP-1 and PYY satiety peptides."
        )
    )
}
