"""
Wearables & Recovery IoT Module.
"""

from health_platform.core.wearables.models import (
    DeviceType,
    DeviceConnectionStatus,
    RecoveryState,
    DeviceConnection,
    WhoopTelemetry,
    Gamma40HzTelemetry,
    StepActivityTelemetry,
    GymExerciseLog,
    GymStrengthWorkoutTelemetry,
    PrescribedGymExercise,
    ProhibitedGymExercise,
    AdaptiveGymRecommendation,
    PatientWearableDashboard,
    ConnectDeviceInput,
    DisconnectDeviceInput,
    SyncWearablesInput,
    LogWorkoutInput,
    LogGammaSessionInput
)
from health_platform.core.wearables.connectors import (
    WhoopAPIConnector,
    GammaCapConnector,
    HealthKitPedometerConnector,
    GymStrengthTrackerConnector
)
from health_platform.core.wearables.service import WearablesService

__all__ = [
    "DeviceType",
    "DeviceConnectionStatus",
    "RecoveryState",
    "DeviceConnection",
    "WhoopTelemetry",
    "Gamma40HzTelemetry",
    "StepActivityTelemetry",
    "GymExerciseLog",
    "GymStrengthWorkoutTelemetry",
    "PrescribedGymExercise",
    "ProhibitedGymExercise",
    "AdaptiveGymRecommendation",
    "PatientWearableDashboard",
    "ConnectDeviceInput",
    "DisconnectDeviceInput",
    "SyncWearablesInput",
    "LogWorkoutInput",
    "LogGammaSessionInput",
    "WhoopAPIConnector",
    "GammaCapConnector",
    "HealthKitPedometerConnector",
    "GymStrengthTrackerConnector",
    "WearablesService"
]
