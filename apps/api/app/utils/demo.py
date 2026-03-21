from __future__ import annotations

from datetime import datetime, timedelta


DEMO_TRANSCRIPTS = [
    {
        "offset_hours": 8,
        "preset": "anxious",
        "transcript": "I woke up already thinking about my lab and I keep replaying everything I still have to do. It feels like I am behind before the day even starts.",
        "avg_hr": 91,
        "peak_hr": 108,
        "baseline_delta": 15,
    },
    {
        "offset_hours": 12,
        "preset": "overwhelmed",
        "transcript": "I am trying to keep it together between classes, but I missed one deadline and now everything feels stacked on top of me.",
        "avg_hr": 97,
        "peak_hr": 119,
        "baseline_delta": 18,
    },
    {
        "offset_hours": 15,
        "preset": "frustrated",
        "transcript": "That meeting really threw me off. I felt talked over and now I am annoyed at them and at myself for not speaking up.",
        "avg_hr": 102,
        "peak_hr": 124,
        "baseline_delta": 21,
    },
    {
        "offset_hours": 20,
        "preset": "emotionally released",
        "transcript": "I finally got some of the stress out by venting on a walk. I still feel tired, but not as trapped in it.",
        "avg_hr": 84,
        "peak_hr": 96,
        "baseline_delta": 8,
    },
    {
        "offset_hours": 23,
        "preset": "calm but tired",
        "transcript": "I am exhausted and still thinking about tomorrow, but I also feel a little proud that I made it through today without fully shutting down.",
        "avg_hr": 76,
        "peak_hr": 87,
        "baseline_delta": 4,
    },
]


def generate_demo_sessions(base_time: datetime) -> list[dict[str, object]]:
    return [
        {
            **entry,
            "timestamp": base_time.replace(hour=0, minute=0, second=0, microsecond=0)
            + timedelta(hours=entry["offset_hours"]),
        }
        for entry in DEMO_TRANSCRIPTS
    ]
