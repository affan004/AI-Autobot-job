# In this file, you can set the configurations of the app.
import os
from dotenv import load_dotenv
from constants import (
    BING,
    BRAVE,
    DEBUG,
    GOOGLE,
    INFO,
    TRACE,
    GEMINI_GROUNDING,
    AI_STUDIO,
    VERTEX,
)

load_dotenv()

#config related to logging must have prefix LOG_
LOG_LEVEL = TRACE
LOG_SELENIUM_LEVEL = INFO
LOG_TO_FILE = True
LOG_TO_CONSOLE = True

MINIMUM_WAIT_TIME_IN_SECONDS = 1

JOB_APPLICATIONS_DIR = "job_applications"
JOB_SUITABILITY_SCORE = 7

JOB_MAX_APPLICATIONS = 5
JOB_MIN_APPLICATIONS = 1

# Browser engine configuration
BROWSER_ENGINE = os.getenv("BROWSER_ENGINE", "playwright").lower()
BROWSER_HEADLESS = os.getenv("BROWSER_HEADLESS", "False").lower() == "true"
JOB_PORTAL = os.getenv("JOB_PORTAL", "lever").lower()

# TensorZero Gateway Configuration
TENSORZERO_GATEWAY_URL = os.getenv("TENSORZERO_GATEWAY_URL", "http://localhost:3000")
TENSORZERO_DEFAULT_FUNCTION = "generate_haiku"

# Legacy search keys (kept for backward compatibility)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", None)
GOOGLE_SEARCH_ENGINE_ID = os.getenv("GOOGLE_SEARCH_ENGINE_ID", None)
BING_API_KEY = os.getenv("BING_API_KEY", None)
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY", None)

# Search + Grounding configuration
GOOGLE_AI_STUDIO_API_KEY = os.getenv("GOOGLE_AI_STUDIO_API_KEY", GOOGLE_API_KEY)
GEMINI_SEARCH_MODEL = os.getenv("GEMINI_SEARCH_MODEL", "gemini-2.5-flash")
GEMINI_SEARCH_USE_VERTEX = (
    os.getenv("GEMINI_SEARCH_USE_VERTEX", "False").lower() == "true"
)
GEMINI_SEARCH_DEFAULT_SITES = os.getenv(
    "GEMINI_SEARCH_DEFAULT_SITES",
    "jobs.lever.co,boards.greenhouse.io",
)

ALLOWED_SEARCH_ENGINES = [GEMINI_GROUNDING]
DEFAULT_SEARCH_ENGINE = GEMINI_GROUNDING

# LLM provider configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", AI_STUDIO).lower()
GEMINI_LLM_MODEL = os.getenv("GEMINI_LLM_MODEL", "gemini-2.5-flash")

# Vertex AI configuration
VERTEX_PROJECT_ID = os.getenv("VERTEX_PROJECT_ID", "")
VERTEX_LOCATION = os.getenv("VERTEX_LOCATION", "us-central1")
VERTEX_API_ENDPOINT = os.getenv(
    "VERTEX_API_ENDPOINT", f"https://{VERTEX_LOCATION}-aiplatform.googleapis.com"
)
VERTEX_ACCESS_TOKEN = os.getenv("VERTEX_ACCESS_TOKEN", "")
VERTEX_GEMINI_MODEL = os.getenv("VERTEX_GEMINI_MODEL", "gemini-2.5-flash")

APPLY_ONCE_PER_COMPANY = False
CACHE = False

ANSWERS_CACHE_FILE = "answers.json"


def validate_config():
    """
    Validate that all required API keys and configurations are set.
    Raises an exception if any critical configuration is missing.
    """
    missing_keys = []

    if ALLOWED_SEARCH_ENGINES == []:
        missing_keys.append("ALLOWED_SEARCH_ENGINES cannot be empty")

    if GEMINI_GROUNDING in ALLOWED_SEARCH_ENGINES:
        if not GOOGLE_AI_STUDIO_API_KEY and not (
            VERTEX_PROJECT_ID and (VERTEX_ACCESS_TOKEN or GEMINI_SEARCH_USE_VERTEX)
        ):
            missing_keys.append(
                "GOOGLE_AI_STUDIO_API_KEY (or Vertex AI credentials/project settings)"
            )

    if LLM_PROVIDER not in {AI_STUDIO, VERTEX, "tensorzero"}:
        missing_keys.append("LLM_PROVIDER must be one of: ai_studio, vertex, tensorzero")

    if missing_keys:
        raise EnvironmentError(
            f"Missing required configuration(s): {', '.join(missing_keys)}. "
            "Please set these as environment variables."
        )

print(f'ENV: {os.getenv("ENV")}')

# Run validation on import
if not os.getenv('ENV') == 'test':
    validate_config()
