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

if __name__ == "__main__":
    unittest.main()
