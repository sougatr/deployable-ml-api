import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class CloudEventEnvelope(BaseModel):
    specversion: str = "1.0"
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    source: str = "urn:service:platform-health-core"
    type: str # E.g. health.identity.patient_registered.v1
    time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    datacontenttype: str = "application/json"
    
    # Healthcare Enterprise Extensions
    tenantid: uuid.UUID
    mpiid: uuid.UUID
    traceid: str = Field(default_factory=lambda: uuid.uuid4().hex)
    actorid: Optional[uuid.UUID] = None
    actorrole: str = "SYSTEM"
    
    data: Dict[str, Any]

class TransactionalOutboxPublisher:
    """
    Simulates the Transactional Outbox pattern, persisting events 
    within the domain transaction boundary before streaming to Kafka/Redpanda.
    """
    def __init__(self):
        self._outbox_records: list = []

    def stage_event(self, event: CloudEventEnvelope) -> uuid.UUID:
        record = {
            "event_id": event.id,
            "aggregate_type": event.type.split(".")[1].upper(),
            "aggregate_id": str(event.mpiid),
            "event_type": event.type,
            "partition_key": str(event.mpiid), # Strict deterministic in-order patient partitioning
            "payload": event.model_dump(mode="json"),
            "status": "PENDING",
            "created_at": event.time
        }
        self._outbox_records.append(record)
        return event.id

    def get_pending_events(self) -> list:
        return [r for r in self._outbox_records if r["status"] == "PENDING"]

    def mark_published(self, event_id: uuid.UUID):
        for r in self._outbox_records:
            if r["event_id"] == event_id:
                r["status"] = "PUBLISHED"
                break
