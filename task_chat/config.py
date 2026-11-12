import os

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "120"))
FUZZY_MATCH_THRESHOLD = int(os.getenv("FUZZY_MATCH_THRESHOLD", "80"))
MAX_TASK_RESULTS = int(os.getenv("MAX_TASK_RESULTS", "100"))
APP_TIMEZONE = os.getenv("APP_TIMEZONE", "Asia/Kolkata")
