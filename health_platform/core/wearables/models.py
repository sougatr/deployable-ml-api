"""
Wearable, Neuro-Device & Strength Training Domain Models.
Supports integration with consumer and clinical wearables:
- WHOOP 4.0 (HRV, Recovery, Strain, Sleep Performance & Architecture)
- 40Hz Gamma Sensory / Neuromodulation Headset (Entrainment, Coherence, Sleep & Pain Pacing)
- Activity & Gait Trackers (Post-Operative Step Ceilings & Symmetry)
- Gym Strength Training (Velocity, Reps, ROM Limits, RPE & Hypertrophy Pacing)
"""

from typing import List, Optional, Dict, Any
from enum import Enum
import uuid
from datetime import datetime, timezone
from pydantic import BaseModel, Field

class DeviceType(str, Enum):
    WHOOP_4 = "WHOOP_4"
    GAMMA_40HZ_CAP = "GAMMA_40HZ_CAP"
    SMART_PEDOMETER = "SMART_PEDOMETER"
    GYM_STRENGTH_TRACKER = "GYM_STRENGTH_TRACKER"
    APPLE_HEALTH = "APPLE_HEALTH"
    OURA_RING = "OURA_RING"

class DeviceConnectionStatus(str, Enum):
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    SYNCING = "SYNCING"
    PAIRING_REQUIRED = "PAIRING_REQUIRED"

class RecoveryState(str, Enum):
    GREEN = "GREEN"      # 67% - 100%: Optimal readiness for strength/rehab loading
    YELLOW = "YELLOW"    # 34% - 66%: Moderate readiness, maintain low-to-moderate volume
    RED = "RED"          # 0% - 33%: High systemic strain / compromised recovery, rest only

class DeviceConnection(BaseModel):
    device_id: str
    mpi_id: uuid.UUID
    device_type: DeviceType
    device_name: str
    status: DeviceConnectionStatus = DeviceConnectionStatus.CONNECTED
    battery_level_pct: int = Field(default=85, ge=0, le=100)
    last_synced_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    firmware_version: str = "v2.4.1"
    connection_protocol: str = "Cloud OAuth2 / BLE"

class WhoopTelemetry(BaseModel):
    recovery_score: int = Field(default=82, ge=0, le=100)
    recovery_state: RecoveryState = RecoveryState.GREEN
    hrv_ms: float = Field(default=68.5, description="Heart Rate Variability in milliseconds (RMSSD)")
    resting_heart_rate_bpm: int = Field(default=54, ge=30, le=140)
    day_strain: float = Field(default=9.4, ge=0.0, le=21.0)
    sleep_performance_pct: int = Field(default=88, ge=0, le=100)
    sleep_hours_total: float = Field(default=7.4, ge=0.0)
    deep_sleep_minutes: int = Field(default=92, description="Slow wave sleep, crucial for cellular & graft healing")
    rem_sleep_minutes: int = Field(default=105, description="Rapid eye movement sleep, neuro-recovery & cognition")
    light_sleep_minutes: int = Field(default=247)
    awake_minutes: int = Field(default=36)
    sleep_efficiency_pct: int = Field(default=91, ge=0, le=100)
    skin_temp_delta_celsius: float = Field(default=0.1, description="Deviation from baseline. Useful for early inflammation/infection alert")
    respiratory_rate_rpm: float = Field(default=14.2)
    synced_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Gamma40HzTelemetry(BaseModel):
    device_name: str = "NeuroShield 40Hz Gamma EEG Cap"
    session_completed: bool = True
    session_duration_minutes: int = Field(default=45, ge=0)
    target_duration_minutes: int = Field(default=45)
    frequency_hz: float = Field(default=40.0)
    cortical_entrainment_coherence_pct: int = Field(default=84, ge=0, le=100, description="PLV / Phase-Locking Value across sensory & motor cortices")
    session_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    protocol_name: str = "Post-Op Neuro-Analgesia & Circadian Deep Sleep Alignment"
    subjective_pain_reduction: str = "VAS score reduced from 5.0 to 2.5 following 40Hz sensory entrainment"
    daily_adherence_streak_days: int = 5
    slow_wave_facilitation_index: float = 1.35 # 35% boost in subsequent SWS slow delta power
    status: str = "COMPLETED"

class StepActivityTelemetry(BaseModel):
    daily_steps: int = Field(default=2150, ge=0)
    post_op_step_target: int = Field(default=2500, description="Recommended daily limit based on post-op week")
    post_op_step_ceiling: int = Field(default=3000, description="Hard ceiling to avoid graft swelling or micro-damage")
    cadence_avg_spm: int = Field(default=86, description="Steps per minute")
    distance_km: float = Field(default=1.65)
    active_calories_kcal: int = Field(default=180)
    gait_weight_bearing_symmetry_pct: str = "45% Operated Leg / 55% Sound Leg"
    ceiling_exceeded: bool = False
    gait_alert: Optional[str] = None
    synced_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class GymExerciseLog(BaseModel):
    name: str
    sets: int
    reps: int
    weight_kg: float
    target_rom_degrees: str # e.g. "0° - 70° flexion"
    actual_rom_degrees: str
    rpe: int = Field(default=6, ge=1, le=10, description="Rate of Perceived Exertion (1 to 10)")
    tempo: str = "3-1-2-0 (Controlled eccentric)"
    safety_compliance: bool = True

class GymStrengthWorkoutTelemetry(BaseModel):
    workout_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    workout_name: str = "Post-Op Phase 2 Kinetic Chain & Upper Body Hypertrophy"
    workout_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    total_volume_kg: float = 3850.0
    strain_generated: float = 8.6
    duration_minutes: int = 42
    exercises: List[GymExerciseLog] = Field(default_factory=list)
    ai_post_workout_feedback: str = (
        "Excellent controlled biomechanics. Maintained prescribed knee flexion under 70°. "
        "Post-workout cryotherapy recommended."
    )

class PrescribedGymExercise(BaseModel):
    name: str
    target_muscle_group: str
    recommended_sets_and_reps: str
    load_intensity: str
    rom_limit: str
    tempo: str
    biomechanical_rationale: str

class ProhibitedGymExercise(BaseModel):
    name: str
    danger_risk: str
    safe_alternative: str

class AdaptiveGymRecommendation(BaseModel):
    training_readiness_score: int = Field(default=85, ge=0, le=100)
    readiness_status: str # "CLEARED_FOR_STRENGTH_TRAINING", "MODIFIED_LOW_INTENSITY", "REST_AND_RECOVERY"
    target_day_strain_range: str = "8.0 - 11.5"
    whoop_recovery_influence: str
    gamma_neuro_pacing_influence: str
    cardio_and_step_pacing: str
    recommended_gym_movements: List[PrescribedGymExercise] = Field(default_factory=list)
    contraindicated_gym_movements: List[ProhibitedGymExercise] = Field(default_factory=list)
    post_workout_protocol: str

class PatientWearableDashboard(BaseModel):
    mpi_id: uuid.UUID
    uhid: str
    patient_name: str
    post_op_days: int = 21 # e.g., 3 weeks post-surgery
    surgical_procedure: str = "Right Knee Arthroscopy - Medial Meniscus Posterior Root Repair"
    connected_devices: List[DeviceConnection] = Field(default_factory=list)
    whoop_telemetry: Optional[WhoopTelemetry] = None
    gamma_40hz_telemetry: Optional[Gamma40HzTelemetry] = None
    step_telemetry: Optional[StepActivityTelemetry] = None
    recent_gym_workouts: List[GymStrengthWorkoutTelemetry] = Field(default_factory=list)
    adaptive_gym_recommendations: AdaptiveGymRecommendation
    clinical_safety_alerts: List[str] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ConnectDeviceInput(BaseModel):
    mpi_id: uuid.UUID
    device_type: DeviceType
    device_name: str

class DisconnectDeviceInput(BaseModel):
    mpi_id: uuid.UUID
    device_type: DeviceType

class SyncWearablesInput(BaseModel):
    mpi_id: uuid.UUID
    step_override: Optional[int] = None
    whoop_recovery_override: Optional[int] = None

class LogWorkoutInput(BaseModel):
    mpi_id: uuid.UUID
    workout_name: str = "Lower Body Phase 2 Rehabilitation & Upper Body Pull"
    exercises: List[GymExerciseLog] = Field(default_factory=list)
    duration_minutes: int = 40
    strain_generated: float = 8.5

class LogGammaSessionInput(BaseModel):
    mpi_id: uuid.UUID
    duration_minutes: int = 45
    protocol: str = "Post-Op Neuro-Analgesia & Circadian Deep Sleep Alignment"

