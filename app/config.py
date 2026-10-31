import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load_env(filepath: str = ".env"):
    if not os.path.isabs(filepath):
        filepath = os.path.join(BASE_DIR, filepath)
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip("'\"")
                    if k not in os.environ:
                        os.environ[k] = v

load_env()

class Settings:
    PORT: int = int(os.getenv("PORT", "8001"))
    HOST: str = os.getenv("HOST", "0.0.0.0")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1")
    
    DATA_DIR: str = os.getenv("DATA_DIR", os.path.join(BASE_DIR, "data"))
    UPLOADS_DIR: str = os.path.join(DATA_DIR, "uploads")
    CLEANED_DIR: str = os.path.join(DATA_DIR, "cleaned")
    TEMP_DIR: str = os.path.join(DATA_DIR, "temp")
    METADATA_DIR: str = os.path.join(DATA_DIR, "metadata")

settings = Settings()

os.makedirs(settings.UPLOADS_DIR, exist_ok=True)
os.makedirs(settings.CLEANED_DIR, exist_ok=True)
os.makedirs(settings.TEMP_DIR, exist_ok=True)
os.makedirs(settings.METADATA_DIR, exist_ok=True)
