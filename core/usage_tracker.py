import json
from datetime import datetime
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
USAGE_FILE = DATA_DIR / "usage.json"

FREE_OPERATION_LIMIT = 10


def _load_usage():
    DATA_DIR.mkdir(exist_ok=True)

    if not USAGE_FILE.exists():
        return {
            "operations": 0,
            "usage_month": datetime.now().strftime("%Y-%m"),
        }

    try:
        with open(USAGE_FILE, "r", encoding="utf-8") as file:
            return json.load(file)

    except (json.JSONDecodeError, OSError):
        return {
            "operations": 0,
            "usage_month": datetime.now().strftime("%Y-%m"),
        }


def _save_usage(data):
    DATA_DIR.mkdir(exist_ok=True)

    with open(
        USAGE_FILE,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            data,
            file,
            indent=4,
        )


def get_usage():
    data = _load_usage()

    current_month = datetime.now().strftime("%Y-%m")

    if data.get("usage_month") != current_month:
        data = {
            "operations": 0,
            "usage_month": current_month,
        }

        _save_usage(data)

    return data


def can_use():
    usage = get_usage()

    return usage["operations"] < FREE_OPERATION_LIMIT


def record_operation():
    usage = get_usage()

    if usage["operations"] >= FREE_OPERATION_LIMIT:
        return False

    usage["operations"] += 1

    _save_usage(usage)

    return True


def get_remaining_operations():
    usage = get_usage()

    return max(
        0,
        FREE_OPERATION_LIMIT - usage["operations"],
    )


def can_process():
    return can_use()