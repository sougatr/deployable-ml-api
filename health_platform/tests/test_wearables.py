"""
Unit & Integration Tests for Wearables, Neuro-Device (40Hz Gamma Cap),
WHOOP Telemetry, Sleep Architecture, and Adaptive Gym Strength Training.
"""

import unittest
import uuid
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from health_platform.api.app import app, identity_service, clinical_service, wearables_service
from health_platform.core.identity.models import PatientRegistrationRequest
from health_platform.core.wearables.models import (
    DeviceType,
    DeviceConnectionStatus,
    RecoveryState,
    GymExerciseLog
)

class TestWearablesAndRecoveryIoT(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

        if not hasattr(cls, "mpi_id") or cls.mpi_id is None:
            # Register a patient with knee surgery context
            try:
                res = identity_service.resolve_or_create_patient(
                    PatientRegistrationRequest(
                        first_name="Meera",
                        last_name="Sen",
                        dob="1994-06-15",
                        gender="FEMALE",
                        primary_phone="+919811223344",
                        postal_code="110001",
                        identifiers=[]
                    )
                )
                cls.mpi_id = res.mpi_id
            except Exception:
                # If already registered, find from identity_service
                for p in identity_service._patients.values():
                    if p.first_name == "Meera" and p.last_name == "Sen":
                        cls.mpi_id = p.mpi_id
                        break

    def test_01_device_connection_and_discovery(self):
        """Verify WHOOP 4.0, 40Hz Gamma Cap, Pedometer, and Gym Sensor default initialization."""
        dashboard = wearables_service.sync_patient_wearables(self.mpi_id)
        self.assertEqual(len(dashboard.connected_devices), 4)
        
        dev_types = [d.device_type for d in dashboard.connected_devices]
        self.assertIn(DeviceType.WHOOP_4, dev_types)
        self.assertIn(DeviceType.GAMMA_40HZ_CAP, dev_types)
        self.assertIn(DeviceType.SMART_PEDOMETER, dev_types)
        self.assertIn(DeviceType.GYM_STRENGTH_TRACKER, dev_types)

        # Test disconnect and reconnect
        dis_res = wearables_service.disconnect_device(self.mpi_id, DeviceType.OURA_RING)
        self.assertFalse(dis_res) # not present
        dis_res2 = wearables_service.disconnect_device(self.mpi_id, DeviceType.WHOOP_4)
        self.assertTrue(dis_res2)

        # Reconnect
        recon = wearables_service.connect_device(self.mpi_id, DeviceType.WHOOP_4, "WHOOP 4.0 Biometric Band")
        self.assertEqual(recon.status, DeviceConnectionStatus.CONNECTED)

    def test_02_whoop_telemetry_and_sleep_architecture(self):
        """Verify WHOOP Recovery %, HRV, Resting HR, and Deep/REM Sleep tracking."""
        dashboard = wearables_service.sync_patient_wearables(self.mpi_id, whoop_recovery_override=84)
        whoop = dashboard.whoop_telemetry
        self.assertIsNotNone(whoop)
        self.assertEqual(whoop.recovery_score, 84)
        self.assertEqual(whoop.recovery_state, RecoveryState.GREEN)
        self.assertGreater(whoop.hrv_ms, 50.0)
        self.assertEqual(whoop.resting_heart_rate_bpm, 54)
        self.assertGreater(whoop.deep_sleep_minutes, 60) # Slow-wave deep sleep for tissue repair
        self.assertGreater(whoop.rem_sleep_minutes, 60) # REM sleep for neuro-recovery
        self.assertGreater(whoop.sleep_performance_pct, 80)

    def test_03_gamma_40hz_neuromodulation_cap(self):
        """Verify 40Hz Audio-Visual / tACS entrainment session compliance & cortical coherence."""
        dashboard = wearables_service.sync_patient_wearables(self.mpi_id)
        gamma = dashboard.gamma_40hz_telemetry
        self.assertIsNotNone(gamma)
        self.assertEqual(gamma.frequency_hz, 40.0)
        self.assertEqual(gamma.session_duration_minutes, 45)
        self.assertTrue(gamma.session_completed)
        self.assertGreaterEqual(gamma.cortical_entrainment_coherence_pct, 80)
        self.assertGreater(gamma.slow_wave_facilitation_index, 1.2) # Facilitates deep sleep slow waves

    def test_04_step_pacing_and_surgical_ceiling_alert(self):
        """Verify daily step pacing enforces post-op ceiling and triggers safety alert when exceeded."""
        # 1. Normal steps within safe target
        dash_safe = wearables_service.sync_patient_wearables(self.mpi_id, step_override=2100)
        self.assertFalse(dash_safe.step_telemetry.ceiling_exceeded)
        self.assertEqual(len(dash_safe.clinical_safety_alerts), 0)

        # 2. Exceed post-operative ceiling (e.g. 3,500 steps > 3,000 ceiling in phase 1)
        dash_exceeded = wearables_service.sync_patient_wearables(self.mpi_id, step_override=3450)
        self.assertTrue(dash_exceeded.step_telemetry.ceiling_exceeded)
        self.assertTrue(any("SAFETY ALERT" in a for a in dash_exceeded.clinical_safety_alerts))

    def test_05_adaptive_gym_strength_training_recommendations(self):
        """Verify adaptive gym strength prescription restricts ROM angles and prohibits deep squats."""
        # Optimal green recovery
        dashboard = wearables_service.sync_patient_wearables(self.mpi_id, whoop_recovery_override=82)
        rec = dashboard.adaptive_gym_recommendations
        self.assertEqual(rec.readiness_status, "CLEARED_FOR_STRENGTH_TRAINING")
        self.assertGreaterEqual(rec.training_readiness_score, 75)

        # Verify prescribed safe movements with explicit ROM angle limits
        rec_names = [m.name for m in rec.recommended_gym_movements]
        self.assertTrue(any("Leg Press" in n for n in rec_names))
        self.assertTrue(any("Isometric Leg Extension" in n for n in rec_names))
        
        # Verify prohibited movements protect graft
        prohib_names = [p.name for p in rec.contraindicated_gym_movements]
        self.assertTrue(any("Deep Barbell Back Squats" in p for p in prohib_names))
        self.assertTrue(any("Bulgarian Split Squats" in p for p in prohib_names))

        # Red recovery deload
        dash_red = wearables_service.sync_patient_wearables(self.mpi_id, whoop_recovery_override=28)
        self.assertEqual(dash_red.adaptive_gym_recommendations.readiness_status, "REST_AND_RECOVERY")
        self.assertTrue(any("RECOVERY ALERT" in a for a in dash_red.clinical_safety_alerts))

    def test_06_gym_workout_logging(self):
        """Verify logging strength workouts with velocity, ROM compliance, and volume calculation."""
        exercises = [
            GymExerciseLog(
                name="Seated Machine Leg Press",
                sets=3,
                reps=10,
                weight_kg=40.0,
                target_rom_degrees="0° to 70° flexion",
                actual_rom_degrees="0° to 65°",
                rpe=6,
                tempo="3-1-2-0",
                safety_compliance=True
            ),
            GymExerciseLog(
                name="Isometric VMO Quad Hold",
                sets=4,
                reps=5,
                weight_kg=15.0,
                target_rom_degrees="60° static hold",
                actual_rom_degrees="60°",
                rpe=7,
                tempo="10s hold",
                safety_compliance=True
            )
        ]
        workout = wearables_service.log_gym_workout(
            mpi_id=self.mpi_id,
            workout_name="Phase 2 Lower Kinetic Chain Workout",
            exercises=exercises,
            duration_minutes=35,
            strain_generated=8.2
        )
        self.assertEqual(workout.total_volume_kg, (3 * 10 * 40.0) + (4 * 5 * 15.0)) # 1200 + 300 = 1500
        self.assertEqual(workout.strain_generated, 8.2)
        self.assertIn("verified within post-op limits", workout.ai_post_workout_feedback)

    def test_07_ai_companion_wearable_queries(self):
        """Verify AI Health Companion answers questions on Whoop, Sleep, 40Hz Gamma Cap, and Gym."""
        # 1. WHOOP Query
        res_whoop = self.client.post("/api/v1/portal/ai-query", json={
            "mpi_id": str(self.mpi_id),
            "question": "What is my WHOOP recovery and strain today?"
        })
        self.assertEqual(res_whoop.status_code, 200)
        self.assertIn("GREEN zone", res_whoop.json()["answer"])
        self.assertIn("HRV", res_whoop.json()["answer"])

        # 2. Sleep Query
        res_sleep = self.client.post("/api/v1/portal/ai-query", json={
            "mpi_id": str(self.mpi_id),
            "question": "How is my deep sleep impacting my post-op recovery?"
        })
        self.assertEqual(res_sleep.status_code, 200)
        self.assertIn("Slow-Wave Deep Sleep", res_sleep.json()["answer"])
        self.assertIn("collagen", res_sleep.json()["answer"])

        # 3. 40Hz Gamma Cap Query
        res_gamma = self.client.post("/api/v1/portal/ai-query", json={
            "mpi_id": str(self.mpi_id),
            "question": "How should I use my 40Hz gamma cap?"
        })
        self.assertEqual(res_gamma.status_code, 200)
        self.assertIn("40Hz Gamma", res_gamma.json()["answer"])
        self.assertIn("entrainment", res_gamma.json()["answer"])

        # 4. Step Ceiling Query
        res_steps = self.client.post("/api/v1/portal/ai-query", json={
            "mpi_id": str(self.mpi_id),
            "question": "What is my step limit today and what happens if I walk too much?"
        })
        self.assertEqual(res_steps.status_code, 200)
        self.assertIn("3,000 steps", res_steps.json()["answer"])
        self.assertIn("effusion", res_steps.json()["answer"])

        # 5. Gym Strength Query
        res_gym = self.client.post("/api/v1/portal/ai-query", json={
            "mpi_id": str(self.mpi_id),
            "question": "Can I do leg press and gym strength training today?"
        })
        self.assertEqual(res_gym.status_code, 200)
        self.assertIn("CLEARED for Phase 2", res_gym.json()["answer"])
        self.assertIn("Seated Machine Leg Press", res_gym.json()["answer"])
        self.assertIn("Deep squats", res_gym.json()["answer"])

    def test_08_api_wearables_endpoints(self):
        """Verify FastAPI REST endpoints for wearables telemetry, sync, and workout logging."""
        # GET /wearables
        res = self.client.get(f"/api/v1/portal/patients/{self.mpi_id}/wearables")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["patient_name"], "Meera Sen")
        self.assertIn("whoop_telemetry", data)
        self.assertIn("gamma_40hz_telemetry", data)
        self.assertIn("step_telemetry", data)

        # POST /wearables/sync
        sync_res = self.client.post(
            f"/api/v1/portal/patients/{self.mpi_id}/wearables/sync",
            json={"mpi_id": str(self.mpi_id), "step_override": 2400, "whoop_recovery_override": 78}
        )
        self.assertEqual(sync_res.status_code, 200)
        self.assertEqual(sync_res.json()["step_telemetry"]["daily_steps"], 2400)
        self.assertEqual(sync_res.json()["whoop_telemetry"]["recovery_score"], 78)

        # POST /wearables/log-gamma
        gamma_res = self.client.post(
            "/api/v1/portal/wearables/log-gamma",
            json={"mpi_id": str(self.mpi_id), "duration_minutes": 45}
        )
        self.assertEqual(gamma_res.status_code, 200)
        self.assertEqual(gamma_res.json()["session_duration_minutes"], 45)
