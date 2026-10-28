from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / ".data"
RUNS = DATA / "runs"
UPLOADS = DATA / "uploads"
FRONTEND = ROOT / "frontend" / "dist"


def prepare():
    for path in (DATA, RUNS, UPLOADS):
        path.mkdir(parents=True, exist_ok=True)
