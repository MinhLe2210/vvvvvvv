import logging
import sys
from enum import Enum
from typing import Dict

from pydantic import BaseModel, Field

from src import configs


def get_logger():
    logger = logging.getLogger("cms_validation")
    if logger.handlers:
        return logger

    try:
        logger.setLevel(configs.LOG_LEVEL.upper())
    except Exception:
        logger.setLevel(logging.WARNING)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(handler)
    logger.propagate = False

    for log_name in ("openai", "httpx", "urllib3"):
        logging.getLogger(log_name).setLevel(logging.ERROR)

    return logger


logging_service = get_logger()


class ErrorCodes(Enum):
    OPENAI_ERROR = (5001, "OpenAI Error!")
    CONTENT_ERROR = (5002, "Content Null!")
    EVENT_ERROR = (5003, "Invalid Event ID!")
    TITLE_ERROR = (5004, "Title Null!")
    INTERNAL_ERROR = (500, "Internal Service Error!")
    CONFIG_ERROR = (5005, "Config Error!")

    def __init__(self, status_code: int, description: str):
        self.status_code = status_code
        self.description = description


class LocalTopic(str, Enum):
    KNOWN = "Known"
    ALERT = "Alert"
    SOCIAL_ORDER = "Social Order"
    SAR = "SAR"
    ACCIDENT = "Accident"
    COMPLAINT = "Complaint"
    SECURITY = "Security"
    CHILD = "Child"
    FICTION = "Fiction"
    SANITATION_POLLUTION = "SanitationPollution"
    CYBERSECURITY = "Cybersecurity"
    MOVEMENT = "Movement"
    OTHER = "Other"


class LocationResult(BaseModel):
    location: bool
    topic: LocalTopic


class ValidationResult(BaseModel):
    result: bool


class Severity2Lv(str, Enum):
    HIGH = "High"
    LOW = "Low"


class Severity3Lv(str, Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    LOW = "Low"


class Severity3Lv2(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class Severity4Lv(str, Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class SeverityResult2Lv(BaseModel):
    severity: Severity2Lv = Field(default=Severity2Lv.LOW)


class SeverityResult3Lv(BaseModel):
    severity: Severity3Lv = Field(default=Severity3Lv.LOW)


class SeverityResult3Lv2(BaseModel):
    severity: Severity3Lv2 = Field(default=Severity3Lv2.LOW)


class SeverityResult4Lv(BaseModel):
    severity: Severity4Lv = Field(default=Severity4Lv.LOW)


SEVERITY_MAPPING = {
    LocalTopic.SOCIAL_ORDER.value: SeverityResult4Lv,
    LocalTopic.ALERT.value: SeverityResult3Lv2,
    LocalTopic.COMPLAINT.value: SeverityResult3Lv,
    LocalTopic.SECURITY.value: SeverityResult3Lv,
    LocalTopic.SAR.value: SeverityResult3Lv,
    LocalTopic.ACCIDENT.value: SeverityResult4Lv,
    LocalTopic.CHILD.value: SeverityResult3Lv,
    LocalTopic.SANITATION_POLLUTION.value: SeverityResult2Lv,
    LocalTopic.CYBERSECURITY.value: SeverityResult2Lv,
    LocalTopic.MOVEMENT.value: SeverityResult2Lv,
}


class InputBase(BaseModel):
    content: str
    title: str
    description: str = ""
    display_name: str = ""
    event_id: str
    request_id: str = ""
    article_id: str = ""
    places_override: str | None = None


class OutputBase(BaseModel):
    result: bool | None = None
    request_id: str = ""
    status_code: int = 200
    description: str = "Successfully!"

    def set_error(self, error_code: ErrorCodes):
        self.status_code = error_code.status_code
        self.description = error_code.description


class OutputValidation(OutputBase):
    location: bool | None = None
    topic: str | None = None
    result_detail: Dict = Field(default_factory=dict)
    severity: str | None = None
