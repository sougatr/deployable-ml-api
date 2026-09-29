"""
Cardiometabolic & Lifestyle Disease Risk Calculator.
Computes evidence-grounded clinical risk scores:
1. ASCVD (Atherosclerotic Cardiovascular Disease) 10-Year Risk Score (ACC/AHA 2013 Pooled Cohort Equations)
2. TyG Index (Triglyceride-Glucose Index for Insulin Resistance and NAFLD)
3. FIB-4 Index (Fibrosis-4 Index for Non-Alcoholic Fatty Liver & Hepatic Fibrosis)
4. eGFR (Estimated Glomerular Filtration Rate via CKD-EPI 2021)
5. Metabolic Syndrome Assessment (NCEP ATP III Criteria)
"""

import math
from typing import Dict, Any, Optional

def calculate_ascvd_risk(
    age: int,
    gender: str, # "MALE" or "FEMALE"
    total_cholesterol: float, # mg/dL
    hdl_cholesterol: float, # mg/dL
    systolic_bp: float, # mmHg
    is_treated_htn: bool = False,
    is_smoker: bool = False,
    is_diabetic: bool = False
) -> Dict[str, Any]:
    """
    Computes 10-year ASCVD risk using ACC/AHA pooled cohort equations.
    Reference: Goff DC Jr, et al. 2013 ACC/AHA Guideline on the Assessment of Cardiovascular Risk.
    """
    age_clamped = max(20, min(79, age))
    ln_age = math.log(age_clamped)
    ln_tc = math.log(max(100.0, min(400.0, total_cholesterol)))
    ln_hdl = math.log(max(20.0, min(120.0, hdl_cholesterol)))
    ln_sbp = math.log(max(90.0, min(200.0, systolic_bp)))

    is_female = "female" in str(gender).lower()

    if is_female:
        # Non-Hispanic White Female coefficients (standard baseline)
        if is_treated_htn:
            sbp_term = 2.019 * ln_sbp
        else:
            sbp_term = 1.957 * ln_sbp

        indiv = (
            -29.799 * ln_age
            + 4.884 * (ln_age ** 2)
            + 13.540 * ln_tc
            - 3.114 * (ln_age * ln_tc)
            - 13.578 * ln_hdl
            + 3.149 * (ln_age * ln_hdl)
            + sbp_term
            + (7.574 * (1 if is_smoker else 0))
            - (1.665 * (ln_age * (1 if is_smoker else 0)))
            + (0.661 * (1 if is_diabetic else 0))
        )
        mean_coeff = -29.18
        baseline_survival = 0.9665
    else:
        # Non-Hispanic White Male coefficients
        if is_treated_htn:
            sbp_term = 1.916 * ln_sbp
        else:
            sbp_term = 1.809 * ln_sbp

        indiv = (
            12.344 * ln_age
            + 11.853 * ln_tc
            - 2.664 * (ln_age * ln_tc)
            - 7.990 * ln_hdl
            + 1.769 * (ln_age * ln_hdl)
            + sbp_term
            + (7.837 * (1 if is_smoker else 0))
            - (1.795 * (ln_age * (1 if is_smoker else 0)))
            + (0.658 * (1 if is_diabetic else 0))
        )
        mean_coeff = 61.18
        baseline_survival = 0.9144

    exponent = indiv - mean_coeff
    # Clamp exponent to prevent numerical overflow
    exponent = max(-10.0, min(10.0, exponent))
    risk = (1.0 - (baseline_survival ** math.exp(exponent))) * 100.0
    risk = max(0.5, min(99.0, risk))
    risk_pct = round(risk, 1)

    if risk_pct < 5.0:
        category = "Low Risk (<5%)"
        severity = "LOW"
        color = "#15803d"
        guidance = "Lifestyle optimization, heart-healthy nutrition (DASH/Mediterranean), regular physical activity."
    elif risk_pct < 7.5:
        category = "Borderline Risk (5.0 - 7.4%)"
        severity = "BORDERLINE"
        color = "#d97706"
        guidance = "Consider coronary artery calcium (CAC) scoring. Intensify diet and lifestyle interventions."
    elif risk_pct < 20.0:
        category = "Intermediate Risk (7.5 - 19.9%)"
        severity = "INTERMEDIATE"
        color = "#ea580c"
        guidance = "Moderate-intensity statin therapy recommended; strict BP target < 130/80 mmHg."
    else:
        category = "High Risk (≥20%)"
        severity = "HIGH"
        color = "#dc2626"
        guidance = "High-intensity statin indicated; aggressive LDL reduction goal < 70 mg/dL; cardiology follow-up."

    return {
        "score_name": "ASCVD 10-Year Cardiovascular Risk",
        "value": risk_pct,
        "unit": "%",
        "category": category,
        "severity": severity,
        "color": color,
        "clinical_guidance": guidance
    }

def calculate_tyg_index(fasting_triglycerides: float, fasting_glucose: float) -> Dict[str, Any]:
    """
    Computes Triglyceride-Glucose (TyG) Index for insulin resistance and NAFLD/MASLD.
    Formula: ln(TG [mg/dL] * Fasting Glucose [mg/dL] / 2)
    Reference: Simental-Mendía LE, et al. J Clin Endocrinol Metab. 2008.
    """
    tg = max(30.0, fasting_triglycerides)
    glu = max(40.0, fasting_glucose)
    product = (tg * glu) / 2.0
    tyg = round(math.log(product), 2)

    if tyg < 8.5:
        category = "Normal (Optimal Insulin Sensitivity)"
        severity = "LOW"
        color = "#15803d"
        guidance = "Excellent metabolic flexibility. Maintain current dietary and activity balance."
    elif tyg < 9.0:
        category = "Mild Insulin Resistance / Borderline NAFLD Risk"
        severity = "MODERATE"
        color = "#d97706"
        guidance = "Subclinical insulin resistance. Adopt early Time-Restricted Eating (TRE) and low-glycemic meal sequencing."
    else:
        category = "Significant Insulin Resistance & High Metabolic Syndrome Risk"
        severity = "HIGH"
        color = "#dc2626"
        guidance = "Elevated risk for NAFLD/hepatic steatosis and cardiometabolic events. Strength training, visceral fat loss, and carbohydrate restriction indicated."

    return {
        "score_name": "TyG Index (Triglyceride-Glucose)",
        "value": tyg,
        "unit": "index",
        "category": category,
        "severity": severity,
        "color": color,
        "clinical_guidance": guidance
    }

def calculate_fib4_index(age: int, ast: float, alt: float, platelet_count: float) -> Dict[str, Any]:
    """
    Computes Fibrosis-4 (FIB-4) index for hepatic fibrosis in metabolic fatty liver disease.
    Formula: (Age * AST) / (Platelets * sqrt(ALT))
    Platelets in 10^9/L (e.g. 240 for 240,000/uL).
    Reference: Sterling RK, et al. Hepatology. 2006.
    """
    # Normalize platelets to 10^9 / L (if user passed 240000, convert to 240)
    plt = platelet_count if platelet_count < 1000 else platelet_count / 1000.0
    plt = max(10.0, plt)
    ast_val = max(5.0, ast)
    alt_val = max(5.0, alt)

    fib4 = (age * ast_val) / (plt * math.sqrt(alt_val))
    fib4 = round(fib4, 2)

    cutoff_low = 2.0 if age >= 65 else 1.30
    if fib4 < cutoff_low:
        category = "Low Risk of Advanced Liver Fibrosis"
        severity = "LOW"
        color = "#15803d"
        guidance = "High negative predictive value (>90%). Advanced hepatic fibrosis is unlikely. Annual metabolic monitoring."
    elif fib4 <= 2.67:
        category = "Indeterminate Zone (Moderate Risk)"
        severity = "MODERATE"
        color = "#d97706"
        guidance = "Intermediate fibrosis risk. Consider secondary non-invasive testing (Transient Elastography / FibroScan)."
    else:
        category = "High Risk of Advanced Liver Fibrosis"
        severity = "HIGH"
        color = "#dc2626"
        guidance = "Hepatology consultation recommended. FibroScan, liver ultrasound, and intensive metabolic lifestyle management."

    return {
        "score_name": "FIB-4 Liver Fibrosis Index",
        "value": fib4,
        "unit": "score",
        "category": category,
        "severity": severity,
        "color": color,
        "clinical_guidance": guidance
    }

def calculate_egfr(age: int, gender: str, serum_creatinine: float) -> Dict[str, Any]:
    """
    Computes Estimated Glomerular Filtration Rate (eGFR) using CKD-EPI 2021 Creatinine equation.
    Reference: Inker LA, et al. N Engl J Med. 2021.
    """
    is_female = "female" in str(gender).lower()
    cr = max(0.2, serum_creatinine)

    if is_female:
        kappa = 0.7
        alpha = -0.241
        gender_mult = 1.012
    else:
        kappa = 0.9
        alpha = -0.302
        gender_mult = 1.0

    min_ratio = min(cr / kappa, 1.0)
    max_ratio = max(cr / kappa, 1.0)

    egfr = 142.0 * (min_ratio ** alpha) * (max_ratio ** -1.200) * (0.9938 ** age) * gender_mult
    egfr = round(egfr, 1)

    if egfr >= 90.0:
        stage = "Stage 1 (Normal / Optimal eGFR)"
        severity = "LOW"
        color = "#15803d"
        guidance = "Healthy renal filtration. Maintain hydration > 2.5 L/day. Safe for standard post-op analgesics."
    elif egfr >= 60.0:
        stage = "Stage 2 (Mild eGFR Reduction)"
        severity = "BORDERLINE"
        color = "#d97706"
        guidance = "Mild age-related or metabolic reduction. Avoid chronic high-dose NSAID overuse post-surgery."
    elif egfr >= 45.0:
        stage = "Stage 3a (Mild-to-Moderate CKD)"
        severity = "MODERATE"
        color = "#ea580c"
        guidance = "Dose adjustments required for renally excreted drugs. Strictly avoid nephrotoxic combinations."
    elif egfr >= 30.0:
        stage = "Stage 3b (Moderate-to-Severe CKD)"
        severity = "HIGH"
        color = "#dc2626"
        guidance = "Nephrology co-management. Monitor serum potassium, phosphorus, and urinary albumin/creatinine ratio."
    elif egfr >= 15.0:
        stage = "Stage 4 (Severe CKD)"
        severity = "HIGH"
        color = "#991b1b"
        guidance = "Severe renal impairment. Active preparation for renal replacement therapy and tight BP/fluid control."
    else:
        stage = "Stage 5 (Kidney Failure)"
        severity = "CRITICAL"
        color = "#7f1d1d"
        guidance = "Dialysis or transplant evaluation required. Urgent nephrology management."

    return {
        "score_name": "eGFR (Kidney Filtration Rate)",
        "value": egfr,
        "unit": "mL/min/1.73m²",
        "category": stage,
        "severity": severity,
        "color": color,
        "clinical_guidance": guidance
    }

def calculate_metabolic_syndrome_score(
    systolic_bp: float,
    diastolic_bp: float,
    fasting_glucose: float,
    triglycerides: float,
    hdl: float,
    gender: str,
    bmi: Optional[float] = None
) -> Dict[str, Any]:
    """
    Evaluates NCEP ATP III / IDF Metabolic Syndrome criteria.
    Criteria:
    1. Blood Pressure: SBP >= 130 or DBP >= 85 mmHg
    2. Fasting Blood Glucose: >= 100 mg/dL (or diagnosed T2D)
    3. Triglycerides: >= 150 mg/dL
    4. HDL Cholesterol: < 40 mg/dL (Men) or < 50 mg/dL (Women)
    5. BMI >= 25 kg/m² (Asian-Indian cutoff) or elevated waist
    """
    is_female = "female" in str(gender).lower()
    criteria_met = []

    if systolic_bp >= 130 or diastolic_bp >= 85:
        criteria_met.append("Elevated Blood Pressure (≥130/85 mmHg)")
    if fasting_glucose >= 100:
        criteria_met.append("Impaired Fasting Glucose (≥100 mg/dL)")
    if triglycerides >= 150:
        criteria_met.append("Hypertriglyceridemia (≥150 mg/dL)")
    
    hdl_cutoff = 50.0 if is_female else 40.0
    if hdl < hdl_cutoff:
        criteria_met.append(f"Low HDL Cholesterol (<{int(hdl_cutoff)} mg/dL)")
    
    if bmi and bmi >= 25.0:
        criteria_met.append(f"Elevated BMI ({bmi:.1f} kg/m² ≥ 25.0)")

    count = len(criteria_met)
    is_positive = count >= 3

    if is_positive:
        category = f"Metabolic Syndrome Present ({count}/5 criteria met)"
        severity = "HIGH"
        color = "#dc2626"
        guidance = "Meeting metabolic syndrome criteria elevates 10-year risk of cardiovascular disease 2-fold and diabetes 5-fold. Structured lifestyle intervention recommended."
    elif count >= 1:
        category = f"Metabolically Vulnerable ({count}/5 criteria met)"
        severity = "MODERATE"
        color = "#d97706"
        guidance = "Subclinical cardiometabolic risk factors identified. Early dietary and exercise intervention can reverse progression."
    else:
        category = "Optimal Metabolic Health (0/5 criteria met)"
        severity = "LOW"
        color = "#15803d"
        guidance = "All tested metabolic criteria are in the optimal physiological range."

    return {
        "score_name": "Metabolic Syndrome Score",
        "value": count,
        "unit": "of 5 criteria",
        "category": category,
        "severity": severity,
        "color": color,
        "is_positive": is_positive,
        "criteria_met": criteria_met,
        "clinical_guidance": guidance
    }

def compute_all_cardiometabolic_scores(
    age: int,
    gender: str,
    systolic_bp: float = 120.0,
    diastolic_bp: float = 80.0,
    total_cholesterol: float = 195.0,
    hdl_cholesterol: float = 48.0,
    triglycerides: float = 155.0,
    fasting_glucose: float = 98.0,
    serum_creatinine: float = 0.95,
    ast: float = 26.0,
    alt: float = 30.0,
    platelets: float = 240.0,
    is_smoker: bool = False,
    is_diabetic: bool = False,
    is_treated_htn: bool = False,
    bmi: float = 24.5
) -> Dict[str, Any]:
    """
    Computes all 5 key cardiometabolic & lifestyle disease risk scores
    and synthesizes a personalized clinical recommendation.
    """
    ascvd = calculate_ascvd_risk(
        age=age,
        gender=gender,
        total_cholesterol=total_cholesterol,
        hdl_cholesterol=hdl_cholesterol,
        systolic_bp=systolic_bp,
        is_treated_htn=is_treated_htn,
        is_smoker=is_smoker,
        is_diabetic=is_diabetic
    )
    tyg = calculate_tyg_index(
        fasting_triglycerides=triglycerides,
        fasting_glucose=fasting_glucose
    )
    fib4 = calculate_fib4_index(
        age=age,
        ast=ast,
        alt=alt,
        platelet_count=platelets
    )
    egfr = calculate_egfr(
        age=age,
        gender=gender,
        serum_creatinine=serum_creatinine
    )
    mets = calculate_metabolic_syndrome_score(
        systolic_bp=systolic_bp,
        diastolic_bp=diastolic_bp,
        fasting_glucose=fasting_glucose,
        triglycerides=triglycerides,
        hdl=hdl_cholesterol,
        gender=gender,
        bmi=bmi
    )

    # Holistic Clinical Takeaway
    risk_points = 0
    if ascvd["severity"] in ["INTERMEDIATE", "HIGH"]:
        risk_points += 1
    if tyg["severity"] in ["MODERATE", "HIGH"]:
        risk_points += 1
    if fib4["severity"] in ["MODERATE", "HIGH"]:
        risk_points += 1
    if egfr["severity"] in ["MODERATE", "HIGH"]:
        risk_points += 1
    if mets["is_positive"]:
        risk_points += 1

    if risk_points >= 2:
        overall_status = "Action Recommended: Multi-System Metabolic Optimization"
        takeaway = (
            "Even if your primary hospital admission is for surgical repair (e.g. knee meniscus), "
            "optimizing insulin sensitivity (TyG) and cardiovascular health (ASCVD) is vital. "
            "Lowering insulin resistance accelerates tissue collagen synthesis, reduces systemic inflammation, "
            "and protects long-term organ health."
        )
    else:
        overall_status = "Optimal to Low Cardiometabolic Risk"
        takeaway = (
            "Your metabolic markers demonstrate healthy physiological balance. "
            "Continue emphasizing lean protein intake, anti-inflammatory micronutrients, and progressive "
            "rehabilitation exercises to support recovery."
        )

    return {
        "ascvd": ascvd,
        "tyg": tyg,
        "fib4": fib4,
        "egfr": egfr,
        "metabolic_syndrome": mets,
        "overall_status": overall_status,
        "clinical_takeaway": takeaway,
        "input_biomarkers": {
            "age": age,
            "gender": gender,
            "systolic_bp": systolic_bp,
            "diastolic_bp": diastolic_bp,
            "total_cholesterol": total_cholesterol,
            "hdl_cholesterol": hdl_cholesterol,
            "triglycerides": triglycerides,
            "fasting_glucose": fasting_glucose,
            "serum_creatinine": serum_creatinine,
            "ast": ast,
            "alt": alt,
            "platelets": platelets,
            "bmi": bmi,
            "is_smoker": is_smoker,
            "is_diabetic": is_diabetic
        }
    }
