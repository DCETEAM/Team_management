import os
from dotenv import load_dotenv

# Load .env file
load_dotenv(override=True)


class Config:
    DEBUG = False
    TESTING = False
    SECRET_KEY = os.getenv("SECRET_KEY")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URI")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = "src/assets/"
    SERVE_STATIC_FOLDER = os.path.abspath("src/assets")
    ALGORITHM = "HS256"

    MONITOR_IDLE_THRESHOLD_SECONDS = int(os.getenv("MONITOR_IDLE_THRESHOLD_SECONDS", "30"))
    MONITOR_HEARTBEAT_STALE_SECONDS = int(os.getenv("MONITOR_HEARTBEAT_STALE_SECONDS", "120"))
    MONITOR_HEARTBEAT_INTERVAL_SECONDS = int(os.getenv("MONITOR_HEARTBEAT_INTERVAL_SECONDS", "45"))