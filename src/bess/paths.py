"""Project paths, defined once so every module saves to and reads from the same place."""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]  # src/bess/paths.py -> project root
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
