from __future__ import annotations

from datetime import date, datetime, timedelta


def parse_date_or_today(date_value: str | None) -> date:
    if date_value:
        return date.fromisoformat(date_value)
    return datetime.utcnow().date()


def start_of_week(target_date: date) -> date:
    return target_date - timedelta(days=target_date.weekday())


def format_time_window(timestamp: datetime) -> str:
    hour = timestamp.hour
    if hour < 11:
        return "Morning"
    if hour < 15:
        return "Midday"
    if hour < 19:
        return "Afternoon"
    return "Evening"
