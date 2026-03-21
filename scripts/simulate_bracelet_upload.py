from __future__ import annotations

import json
import os
import urllib.request
from datetime import datetime, timedelta


API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

TRANSCRIPTS = [
    {
        "transcript_override": "I keep thinking about the quiz I might have messed up and I cannot stop checking the class portal.",
        "tone_preset": "anxious",
        "avg_hr": 92,
        "peak_hr": 112,
        "baseline_delta": 14,
    },
    {
        "transcript_override": "I feel behind again. It is like every time I catch up, two more things pop up.",
        "tone_preset": "overwhelmed",
        "avg_hr": 98,
        "peak_hr": 121,
        "baseline_delta": 19,
    },
    {
        "transcript_override": "Talking it out helped a little. I am still tired, but I feel less trapped than before.",
        "tone_preset": "emotionally released",
        "avg_hr": 81,
        "peak_hr": 93,
        "baseline_delta": 6,
    },
]


def post_json(path: str, payload: dict) -> dict:
    request = urllib.request.Request(
        f"{API_BASE_URL}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))


def get_json(path: str) -> dict:
    with urllib.request.urlopen(f"{API_BASE_URL}{path}") as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    seeded = post_json("/seed/demo", {"reset": True})
    user_id = seeded["data"]["user"]["id"]
    device_id = seeded["data"]["device"]["id"]

    base_time = datetime.utcnow().replace(hour=9, minute=15, second=0, microsecond=0)
    for index, item in enumerate(TRANSCRIPTS):
        payload = {
            "user_id": user_id,
            "device_id": device_id,
            "timestamp": (base_time + timedelta(hours=index * 4)).isoformat(),
            **item,
            "battery_status": 73 - index,
        }
        post_json("/simulate/session", payload)

    today = datetime.utcnow().date().isoformat()
    summary = get_json(f"/summaries/daily?user_id={user_id}&date={today}")
    patterns = get_json(f"/patterns/weekly?user_id={user_id}&week_start={today}")
    print(json.dumps({"daily": summary["data"], "weekly": patterns["data"]}, indent=2))


if __name__ == "__main__":
    main()
