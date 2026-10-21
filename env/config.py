import json
from pathlib import Path

CONFIG_DIR = Path(__file__).resolve().parent.parent / "configs"


def load_config(name="default"):
    with open(CONFIG_DIR / f"{name}.json") as f:
        return json.load(f)
