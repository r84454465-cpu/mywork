import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List

HISTORY_FILE = Path(__file__).parent.parent / "history.json"


# Ensure JSON file exists and always returns a DICT
def _read_all() -> Dict[str, List[Dict]]:
    try:
        if not HISTORY_FILE.exists():
            HISTORY_FILE.write_text("{}")

        raw = HISTORY_FILE.read_text().strip()

        if not raw:
            return {}

        data = json.loads(raw)

        # If corrupted (list instead of dict), fix it automatically
        if not isinstance(data, dict):
            HISTORY_FILE.write_text("{}")
            return {}

        return data

    except Exception:
        HISTORY_FILE.write_text("{}")
        return {}


def _write_all(data: Dict[str, List[Dict]]):
    HISTORY_FILE.write_text(json.dumps(data, indent=2))


def add_history(username: str, prompt: str, response: str):
    data = _read_all()

    user_hist = data.get(username, [])

    user_hist.append({
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "prompt": prompt,
        "response": response
    })

    data[username] = user_hist
    _write_all(data)


def get_history(username: str) -> List[Dict]:
    data = _read_all()
    return data.get(username, [])
