# ADR-001: Technology Stack, Database Engines, and Architecture Standards (V1.0)
*Status: ACCEPTED*  
*Date: 2026-09-24*  
*Context: Sprint 1 Engineering Kickoff for Patient-Centric Digital Health & Hospital Operating Platform*

---

## 1. Context & Problem Statement
The platform must implement the frozen foundation:
"One Patient. One Identity. One Longitudinal Health Record. One Clinical-Financial Journey. Open to Every Healthcare Network."
It must support high-throughput ambulatory clinics up to 500+ bed enterprise hospital networks, remain ABDM/UHI/NHCX compliant, enforce strict DPDP/HIPAA clinical safety invariants, and maintain deterministic in-order event processing per patient.

---

## 2. Decision Outcomes

### 2.1 Core Backend Runtime & Language
* **Decision:** Python 3.12+ / 3.14 with **FastAPI** (ASGI via Uvicorn/uvloop) + **Pydantic V2** for Core Domain APIs; **asyncpg / SQLAlchemy 2.0 async** for persistence.
* **Rationale:**
  * Native synergy with AI, RAG, and clinical data science libraries already resident in the health tech ecosystem.
  * Pydantic V2 (Rust core) provides $> 10\times$ faster JSON serialization and schema validation, essential for handling large FHIR bundles and clinical observation arrays.
  * High developer velocity for complex healthcare domain model evolution.

### 2.2 Primary Database & Multi-Tenancy Architecture
* **Decision:** **PostgreSQL 16+** with:
  * **Row-Level Security (RLS)** for strict multi-tenant isolation keyed by `tenant_id`.
  * **pgcrypto** for column-level AES-256-GCM encryption of sensitive PII (Aadhaar hash, raw mobile).
  * **pg_trgm** and **fuzzystrmatch** for phonetic (Double Metaphone / Soundex) and trigram indexing for MPI candidate blocking.
  * **JSONB** for storing flexible, validated FHIR extension payloads alongside relational relational invariants.
* **Rationale:** Battle-tested ACID compliance is non-negotiable for double-entry financial ledgers and medical record immutability.

### 2.3 Event Streaming & Broker Architecture
* **Decision:** **Apache Kafka / Redpanda** with partitioned topics keyed deterministically on `mpi_id`.
* **Pattern:** **Transactional Outbox Pattern** using an `outbox_event` table committed atomically within the same database transaction as domain changes.
* **Rationale:** Guarantees zero dual-write failure modes, strict chronological ordering per patient, and at-least-once delivery with idempotent consumer deduplication.

### 2.4 Caching, Session & Fast Locking Store
* **Decision:** **Redis 7.2+** for:
  * Temporary slot reservation locks (`SETNX` with TTL) during appointment booking to prevent double-booking.
  * Ephemeral de-identification session token vaults.
  * Terminology and SNOMED-CT / LOINC in-memory code autocompletion.

### 2.5 API Communication & Protocol Standards
* **Synchronous Internal RPC:** gRPC with Protocol Buffers (`proto3`) for high-throughput inter-service queries; RESTful JSON (OpenAPI 3.1) for Experience Layer (BFF) gateways.
* **Event Message Format:** CloudEvents v1.0 standard envelope serialized in JSON Schema / Avro.
* **External Integration Standard:** HL7 FHIR R4 (NRCES Indian Profiles), ABDM Milestone APIs, NHCX FHIR Claims, Beckn Protocol (UHI), and DICOMweb.

---

## 3. Invariants Enforced by this Decision
1. **Clinical-Financial Invariant:** Every `charge_item` row MUST have a valid foreign key to a `service_request`, `medication_dispense`, or `procedure`.
2. **Double-Entry Balance:** Financial ledger debits must balance credits to ₹0.00 for every journal entry.
3. **Deterministic Partitioning:** All clinical, identity, and billing events MUST partition on `mpi_id`.
