"""
Central configuration for the RFI Knowledge Assistant.
Reads optional settings from a .env file (see .env.example).
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "rfi_assistant.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

# --- LLM provider settings (all optional) ---
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5").strip()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()

# --- Embedding model settings ---
# Used only if sentence-transformers is installed; otherwise a TF-IDF
# fallback is used automatically so the app always runs.
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")

# --- Hybrid search weights (must sum to 1.0, but code will normalize anyway) ---
DEFAULT_KEYWORD_WEIGHT = float(os.getenv("KEYWORD_WEIGHT", "0.4"))
DEFAULT_SEMANTIC_WEIGHT = float(os.getenv("SEMANTIC_WEIGHT", "0.6"))
