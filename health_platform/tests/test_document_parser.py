import unittest
from fastapi.testclient import TestClient
from health_platform.core.clinical.document_parser import ClinicalDocumentParser
from health_platform.api.app import app

client = TestClient(app)

class TestClinicalDocumentParser(unittest.TestCase):
    def test_parse_handwritten_clinical_text(self):
        sample_prescription_text = (
            "PATIENT OPD CASE SHEET\n"
            "C/O: Severe throbbing headache and fatigue x 1 week.\n"
            "O/E: BP: 145/95 mmHg, Pulse: 84 bpm.\n"
            "Impression: Essential Hypertension (Primary), Type 2 Diabetes.\n"
            "Rx:\n"
            "1. Tab Telma 40mg - 1-0-0 x 30 days (morning after food)\n"
            "2. Tab Glycomet 500mg - 1-0-1 x 30 days\n"
            "Advise:\n"
            "- HbA1c Blood Panel\n"
            "- Complete Blood Count (CBC)\n"
        )

        parsed = ClinicalDocumentParser.parse_clinical_text_to_columns(sample_prescription_text)
        
        # 1. Chief Complaint
        self.assertIn("Severe throbbing headache", parsed["chief_complaint"])

        # 2. Vitals
        vitals = {v["code_loinc"]: v for v in parsed["vitals"]}
        self.assertIn("8480-6", vitals)
        self.assertEqual(vitals["8480-6"]["value"], 145.0)
        self.assertEqual(vitals["8480-6"]["interpretation"], "HIGH")

        # 3. Diagnoses
        icd_codes = [d["code_icd10"] for d in parsed["diagnoses"]]
        self.assertIn("I10", icd_codes) # Hypertension
        self.assertIn("E11.9", icd_codes) # Diabetes

        # 4. Prescriptions
        drugs = [p["brand_name"] for p in parsed["prescriptions"]]
        self.assertIn("Telma 40", drugs)
        self.assertIn("Glycomet 500", drugs)

        # 5. Orders
        order_tariffs = [o["tariff_code"] for o in parsed["orders"]]
        self.assertIn("LAB-BIO-042", order_tariffs) # HbA1c
        self.assertIn("LAB-HEM-001", order_tariffs) # CBC

    def test_api_parse_document_endpoint(self):
        res = client.post("/api/v1/clinical/consultations/parse-document")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("parsed_columns", data)
        self.assertIn("vitals", data["parsed_columns"])
        self.assertIn("diagnoses", data["parsed_columns"])
        self.assertIn("prescriptions", data["parsed_columns"])
        self.assertIn("orders", data["parsed_columns"])

    def test_parse_fever_and_antibiotic_prescription(self):
        fever_rx = (
            "PATIENT OPD CASE SHEET\n"
            "C/O: High fever with chills, throat irritation x 3 days.\n"
            "O/E: BP: 122/80 mmHg, Pulse: 96 bpm, Temp: 101.2 F, SpO2: 98%.\n"
            "Impression: Acute upper respiratory tract infection (URTI).\n"
            "Rx:\n"
            "1. Tab Augmentin 625mg - 1-0-1 x 5 days\n"
            "2. Tab Paracetamol 650mg - 1-0-1-1 x 5 days\n"
            "3. Tab Pantocid 40mg - 1-0-0 x 5 days\n"
            "Advise:\n"
            "- Complete Blood Count (CBC)\n"
            "- Standard Chest X-Ray\n"
        )
        parsed = ClinicalDocumentParser.parse_clinical_text_to_columns(fever_rx)
        self.assertIn("High fever", parsed["chief_complaint"])
        icd_codes = [d["code_icd10"] for d in parsed["diagnoses"]]
        self.assertIn("J06.9", icd_codes) # URTI

        drugs = [p["brand_name"] for p in parsed["prescriptions"]]
        self.assertIn("Augmentin 625", drugs)
        self.assertIn("Paracetamol 650", drugs)
        self.assertIn("Pantocid 40", drugs)

        vitals = {v["code_loinc"]: v for v in parsed["vitals"]}
        self.assertIn("8480-6", vitals) # SBP
        self.assertIn("8867-4", vitals) # Pulse
        self.assertIn("59408-5", vitals) # SpO2
        self.assertIn("8310-5", vitals) # Temp

        tariffs = [o["tariff_code"] for o in parsed["orders"]]
        self.assertIn("LAB-HEM-001", tariffs) # CBC
        self.assertIn("RAD-XRAY-001", tariffs) # Chest X-Ray

    def test_vision_ocr_simulation_for_scanned_image(self):
        # Simulating file upload of a fever prescription photo
        text = ClinicalDocumentParser.extract_text_from_file(b"fake_image_bytes", "fever_case_sheet.jpg")
        self.assertIn("URTI", text)
        parsed = ClinicalDocumentParser.parse_clinical_text_to_columns(text)
        self.assertTrue(len(parsed["prescriptions"]) >= 2)
        self.assertTrue(len(parsed["diagnoses"]) >= 1)

    def test_parse_orthopaedic_prescription(self):
        ortho_text = (
            "Gleneagles Hospital, PAREL, MUMBAI\n"
            "Dr ANUP KHATRI\n"
            "Senior Consultant Orthopaedic Surgeon\n"
            "M sAndita Ray  55. / F\n"
            "2 wks F/u Right Medial meniscus Root repair\n"
            "Advise: Physiotherapy -> NWB x 10 days -> PWB to FWB over 10 days\n"
            "ROM beyond 90 degrees gradually after 2 wks\n"
            "- Tb Ezorb forte 0-1-0 x 3 mth\n"
            "- F/u after 2 mth."
        )
        parsed = ClinicalDocumentParser.parse_clinical_text_to_columns(ortho_text)
        self.assertIn("Meniscus Root Repair", parsed["chief_complaint"])
        icd_codes = [d["code_icd10"] for d in parsed["diagnoses"]]
        self.assertIn("M23.30", icd_codes) # Meniscus derangement

        drugs = [p["brand_name"] for p in parsed["prescriptions"]]
        self.assertIn("Ezorb Forte", drugs)
        self.assertEqual(parsed["prescriptions"][0]["timing"], "0-1-0")

        tariffs = [o["tariff_code"] for o in parsed["orders"]]
        self.assertIn("PT-REHAB-002", tariffs) # Physiotherapy

        self.assertIsNotNone(parsed.get("patient_info"))
        self.assertEqual(parsed["patient_info"]["first_name"], "Anindita")
        self.assertEqual(parsed["patient_info"]["last_name"], "Ray")

    def test_department_document_parser_reception(self):
        text = (
            "GOVERNMENT OF INDIA\nAADHAAR CARD\nName: Anindita Ray\n"
            "DOB: 28/07/1971\nAge: 55 Yrs\nGender: Female\nPhone: +919876543210\n"
            "Address: Flat 402, Mumbai - 400012\nAadhaar Number: 9812 4567 1234\n"
            "ABHA ID: anindita.ray@abdm"
        )
        parsed = ClinicalDocumentParser.parse_identity_document(text)
        self.assertEqual(parsed["first_name"], "Anindita")
        self.assertEqual(parsed["last_name"], "Ray")
        self.assertEqual(parsed["age"], 55)
        self.assertEqual(parsed["gender"], "FEMALE")
        self.assertEqual(parsed["aadhaar"], "9812 4567 1234")
        self.assertEqual(parsed["abha_address"], "anindita.ray@abdm")

    def test_department_document_parser_ipd(self):
        text = (
            "INPATIENT SUMMARY\nPatient: Anindita Ray (55/F)\n"
            "Attending Surgeon: Dr. Anup Khatri\n"
            "Procedure: Arthroscopic Meniscus Repair\n"
            "Ward: Deluxe Room (Ward: DELUXE)\n"
            "Vitals: BP: 120/80 mmHg, HR: 76 bpm, Temp: 98.4 F, SpO2: 99%, Resp: 16 /min\n"
            "Nursing Care: Patient stable, post-op cryocuff on.\n"
            "Doctor Rounds: Good passive ROM, minimal pain."
        )
        parsed = ClinicalDocumentParser.parse_ipd_document(text)
        self.assertEqual(parsed["recommended_ward"], "DELUXE")
        self.assertIn("Anup Khatri", parsed["admitting_doctor"])
        self.assertEqual(parsed["vitals"]["systolic"], 120)
        self.assertEqual(parsed["vitals"]["diastolic"], 80)
        self.assertEqual(parsed["vitals"]["spo2"], 99)
        self.assertIn("stable", parsed["nursing_notes"])

    def test_department_document_parser_diagnostics(self):
        text = (
            "CENTRAL LAB & PACS\nInvestigation: Complete Blood Count & X-Ray Knee\n"
            "Parameters:\n- Hemoglobin: 11.4 g/dL (Ref: 12.0 - 15.5) [LOW]\n"
            "- Total Leukocyte Count: 8200 /uL (Ref: 4000 - 11000) [NORMAL]\n"
            "Radiology Digital X-Ray Right Knee:\n"
            "Impression: Intact post-operative right knee meniscus repair."
        )
        parsed = ClinicalDocumentParser.parse_diagnostics_document(text)
        self.assertTrue(len(parsed["parameters"]) >= 2)
        hb = next(p for p in parsed["parameters"] if "Hemoglobin" in p["name"])
        self.assertEqual(hb["flag"], "LOW")
        self.assertIn("meniscus repair", parsed["radiology_impression"])

    def test_department_document_parser_pharmacy(self):
        text = (
            "SUPPLIER INVOICE\nSupplier: GlaxoSmithKline Ltd\nInvoice No: INV-2026-904\n"
            "1. Tab Ezorb Forte | Batch: EZ-8819 | Exp: 08/2027 | Qty: 90 Tabs | MRP: Rs 245.00\n"
            "2. Tab Pantocid 40 | Batch: PAN-4402 | Exp: 12/2026 | Qty: 30 Tabs | MRP: Rs 55.00"
        )
        parsed = ClinicalDocumentParser.parse_pharmacy_document(text)
        self.assertTrue(len(parsed["items"]) >= 2)
        ezorb = next(i for i in parsed["items"] if "Ezorb" in i["brand"])
        self.assertEqual(ezorb["batch_number"], "EZ-8819")
        self.assertEqual(ezorb["quantity"], 90)

    def test_department_document_parser_emergency(self):
        text = (
            "EMS RUN SHEET\nPatient: Anindita Ray\n"
            "Chief Complaint: Acute severe right knee trauma following slip and fall.\n"
            "Mechanism: Blunt musculoskeletal injury.\n"
            "Vitals on Arrival: BP: 138/88 mmHg, Pulse: 92 bpm, Temp: 98.8 F, SpO2: 99%, Resp: 18 /min, Pain Score: 8/10.\n"
            "GCS Score: 15/15.\n"
            "Manchester / ESI Triage Recommendation: Yellow (Category 3 - Urgent)."
        )
        parsed = ClinicalDocumentParser.parse_emergency_document(text)
        self.assertIn("fall", parsed["chief_complaint"].lower())
        self.assertEqual(parsed["recommended_esi"], "LEVEL_3_URGENT")
        self.assertEqual(parsed["priority"], "YELLOW")
        self.assertEqual(parsed["vitals"]["pain_score"], 8)
        self.assertEqual(parsed["vitals"]["gcs"], 15)

    def test_api_department_upload_and_parse_endpoint(self):
        from fastapi.testclient import TestClient
        from health_platform.api.app import app
        client = TestClient(app)

        for dept in ["reception", "diagnostics", "pharmacy", "ipd", "emergency"]:
            res = client.post("/api/v1/clinical/documents/upload-and-parse", data={"department": dept})
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data["status"], "success")
            self.assertEqual(data["department"], dept)
            self.assertIn("parsed_data", data)
            self.assertIn("raw_extracted_text", data)

    def test_parse_hcg_cancer_centre_letterhead_filtering(self):
        """Asserts letterhead, contact, CIN, app promo, and token lines are stripped from clinical notes."""
        hcg_raw = (
            "HCG ICS Khubchandani Cancer Centre\n"
            "Maharishi Karve Road, Opposite Cooperage Football Ground, Cooperage, Mumbai - 400 021\n"
            "Your Ph No. 6358883821 7406199999 | quer@hegel.comhcooncology.com /CIN: 1.15200KA1998P1.C02345\n"
            "can to download the new HCG CARE App today!\n"
            "T. No. - 83442N\n"
            "Dr. Ananya Sen, MD (Medical Oncology)\n"
            "Patient: Sunita Verma (52 Y / Female)\n"
            "C/O: Right breast lump follow-up, mild fatigue after cycle 3.\n"
            "O/E: BP: 120/80 mmHg, Pulse: 76 bpm, Temp: 98.4 F, SpO2: 99%.\n"
            "Impression: Carcinoma Breast (Invasive Ductal Carcinoma, Stage IIA)\n"
            "Rx:\n"
            "1. Tab Tamoxifen 20mg - 0-1-0 x 90 days\n"
            "2. Tab Pantocid 40mg - 1-0-0 x 30 days\n"
            "Advise:\n"
            "- Bilateral Mammography & Ultrasound Breast\n"
            "- Complete Blood Count (CBC) with Platelets\n"
            "Review with reports after 3 weeks."
        )

        parsed = ClinicalDocumentParser.parse_clinical_text_to_columns(hcg_raw)

        # 1. Letterhead / Metadata must NOT be in clinical narrative
        self.assertNotIn("Cooperage", parsed["clinical_narrative"])
        self.assertNotIn("6358883821", parsed["clinical_narrative"])
        self.assertNotIn("HCG CARE", parsed["clinical_narrative"])
        self.assertNotIn("CIN:", parsed["clinical_narrative"])

        # 2. Token No must NOT be chief complaint
        self.assertNotIn("T. No.", parsed["chief_complaint"])
        self.assertIn("breast lump", parsed["chief_complaint"].lower())

        # 3. Vitals must have physiological bounds (no phone number leakage like 610 or 348)
        vitals = {v["code_loinc"]: v for v in parsed["vitals"]}
        self.assertEqual(vitals["8867-4"]["value"], 76.0)
        self.assertEqual(vitals["59408-5"]["value"], 99.0)
        self.assertEqual(vitals["8480-6"]["value"], 120.0)

        # 4. Oncology Diagnoses
        icd_codes = [d["code_icd10"] for d in parsed["diagnoses"]]
        self.assertIn("C50.9", icd_codes) # Malignant neoplasm of breast

        # 5. Oncology Rx
        drugs = [p["brand_name"] for p in parsed["prescriptions"]]
        self.assertTrue(any("Tamoxifen" in d for d in drugs))

        # 6. Oncology Orders
        orders = [o["tariff_code"] for o in parsed["orders"]]
        self.assertTrue(any("MAMMO" in code or "HEM" in code for code in orders))

    def test_parse_inpatient_discharge_summary_metadata_filtering(self):
        """Asserts IPD number, admitting doctor, payer, naval command, dates, DAMA are filtered and a structured summary is generated."""
        discharge_text = (
            "Discharge Summary\n"
            "Name of the Patient\n"
            "Chandrakant Krishna Chavan\n"
            "Age\n"
            "69\n"
            "Gender\n"
            "IPD rumber\n"
            "Admitting Doctor\n"
            "Male\n"
            "MHHIK.0000013317\n"
            "HIKIP6101\n"
            "Dr.Ramkishan Nag\n"
            ": Patient Direct Billing\n"
            "Payer\n"
            "Headquarters westem\n"
            "naval command\n"
            "Date of Registration\n"
            ": 06/07/2026\n"
            "Date of Admission\n"
            ": 06/07/2026 01:19:00\n"
            "PM\n"
            "Date of Discharge\n"
            ":09/07/2026\n"
            "Date of Treatment\n"
            ":06/07/2026\n"
            "Type of Discharge\n"
            ":DAMA\n"
            "Department of Medical Oncology\n"
            "Admitting Diagnosis :Carcinoma colon\n"
            "with Hepatic mets\n"
            "Allergies\n"
            ":Not known\n"
            "Alerts"
        )

        parsed = ClinicalDocumentParser.parse_clinical_text_to_columns(discharge_text)

        # 1. Assert noise is filtered out of clinical notes
        narrative = parsed["clinical_narrative"]
        self.assertNotIn("IPD rumber", narrative)
        self.assertNotIn("HIKIP6101", narrative)
        self.assertNotIn("MHHIK.0000013317", narrative)
        self.assertNotIn("Dr.Ramkishan Nag", narrative)
        self.assertNotIn("naval command", narrative)
        self.assertNotIn("01:19:00", narrative)
        self.assertNotIn("DAMA", narrative)
        self.assertNotIn("Patient Direct Billing", narrative)

        # 2. Assert concise clinical summary was generated
        self.assertIn("Clinical Summary", narrative)
        self.assertIn("Carcinoma Colon", narrative)
        self.assertIn("Hepatic Metastases", narrative)

        # 3. Assert patient demographics extracted
        self.assertIsNotNone(parsed["patient_info"])
        self.assertEqual(parsed["patient_info"]["name"], "Chandrakant Krishna Chavan")
        self.assertEqual(parsed["patient_info"]["age"], 69)
        self.assertEqual(parsed["patient_info"]["gender"], "MALE")

        # 4. Assert diagnosis mapped to colorectal carcinoma C18.9
        icd_codes = [d["code_icd10"] for d in parsed["diagnoses"]]
        self.assertIn("C18.9", icd_codes)

    def test_parse_identity_from_discharge_summary_header(self):
        """Asserts hospital case sheet header extracts Chandrakant Krishna Chavan, not 'of the' or Anindita Ray."""
        discharge_text = (
            "Discharge Summary\n"
            "Name of the Patient\n"
            "Chandrakant Krishna Chavan\n"
            "Age\n"
            "69\n"
            "Gender\n"
            "IPD rumber\n"
            "Admitting Doctor\n"
            "Male\n"
            "MHHIK.0000013317\n"
            "HIKIP6101\n"
            "Dr.Ramkishan Nag\n"
            ": Patient Direct Billing\n"
            "Payer\n"
            "Headquarters westem\n"
            "naval command\n"
            "Date of Registration\n"
            ": 06/07/2026\n"
            "Date of Admission\n"
            ": 06/07/2026 01:19:00\n"
            "PM\n"
            "Date of Discharge\n"
            ":09/07/2026\n"
            "Date of Treatment\n"
            ":06/07/2026\n"
            "Type of Discharge\n"
            ":DAMA\n"
            "Department of Medical Oncology\n"
            "Admitting Diagnosis :Carcinoma colon\n"
            "with Hepatic mets"
        )
        parsed = ClinicalDocumentParser.parse_identity_document(discharge_text)
        self.assertEqual(parsed["name"], "Chandrakant Krishna Chavan")
        self.assertNotEqual(parsed["name"], "of the")
        self.assertEqual(parsed["first_name"], "Chandrakant Krishna")
        self.assertEqual(parsed["last_name"], "Chavan")
        self.assertEqual(parsed["age"], 69)
        self.assertEqual(parsed["gender"], "MALE")
        self.assertEqual(parsed["abha_address"], "chandrakant.chavan@abdm")
        self.assertNotEqual(parsed["aadhaar"], "9812 4567 1234")

    def test_parse_arbitrary_identity_document(self):
        """Asserts generic name and dynamic ABHA/Aadhaar generation for any new patient."""
        doc = (
            "Government of India\n"
            "Name of the Patient: Vikram Malhotra\n"
            "Age: 42\n"
            "Gender: Male\n"
            "Phone: 9820012345\n"
            "Address: Bandra West, Mumbai - 400050"
        )
        parsed = ClinicalDocumentParser.parse_identity_document(doc)
        self.assertEqual(parsed["name"], "Vikram Malhotra")
        self.assertEqual(parsed["first_name"], "Vikram")
        self.assertEqual(parsed["last_name"], "Malhotra")
        self.assertEqual(parsed["age"], 42)
        self.assertEqual(parsed["gender"], "MALE")
        self.assertEqual(parsed["phone"], "9820012345")
        self.assertEqual(parsed["postal_code"], "400050")
        self.assertEqual(parsed["abha_address"], "vikram.malhotra@abdm")
        self.assertNotEqual(parsed["aadhaar"], "9812 4567 1234")

if __name__ == "__main__":
    unittest.main()



