from typing import List, Optional
from pydantic import BaseModel, Field
from enum import Enum
import uuid

class GenderEnum(str, Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"

class Coding(BaseModel):
    system: str
    version: Optional[str] = None
    code: str
    display: str

class CodeableConcept(BaseModel):
    coding: List[Coding] = Field(default_factory=list)
    text: Optional[str] = None

class Reference(BaseModel):
    id: uuid.UUID
    resource_type: str
    display: Optional[str] = None
    identifier: Optional[str] = None

class Money(BaseModel):
    currency: str = "INR"
    amount: float = Field(..., ge=0.0)
