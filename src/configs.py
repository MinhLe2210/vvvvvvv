import json
import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

SRC_DIR = Path(__file__).resolve().parent
def load_json(path: str | Path):
    path = Path(path)
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


PROMPT_PATH = SRC_DIR / "cms_prompt.json"
CUSTOM_PROMPT_PATH = SRC_DIR / "cms_customized_prompt.json"
SEVERITY_PROMPT_PATH = SRC_DIR / "cms_severity.json"
LOCATION_PATH = SRC_DIR / "cms_location.json"
CENSORED_LOCATION_PATH = SRC_DIR / "cms_censored_location.json"
CENSORED_KEYWORD_PATH = SRC_DIR / "cms_censored_keyword.json"

DEFAULT_PROMPT = load_json(PROMPT_PATH)
DEFAULT_PROMPT_CUSTOM = load_json(CUSTOM_PROMPT_PATH)
DEFAULT_PROMPT_SEVERITY = load_json(SEVERITY_PROMPT_PATH)
DEFAULT_CENSORED_LOCATION = load_json(CENSORED_LOCATION_PATH)
DEFAULT_CENSORED_KEYWORD = load_json(CENSORED_KEYWORD_PATH)

MODE_VALIDATION = "validation"
LOCATION = "Location"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_PROXY = os.getenv("OPENAI_PROXY", "")
TIMEOUT = int(os.getenv("TIMEOUT", 50))
MAX_TRY = int(os.getenv("MAX_TRY", 2))
MODEL_DEFAULT = os.getenv("MODEL_DEFAULT", "gpt-4.1-mini")
MODEL_SEVERITY = os.getenv("MODEL_SEVERITY", "gpt-4.1-mini")

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", 25001))

CMS_VALIDATION_URL = os.getenv("CMS_VALIDATION_URL", "/v1/cms-validation")
