from __future__ import annotations

from collections import Counter

from app.schemas.domain import TextUnderstandingResult


KEYWORDS = {
    "academics": ["class", "exam", "deadline", "lab", "assignment", "grade"],
    "belonging": ["talked over", "left out", "alone", "friend", "roommate"],
    "time pressure": ["behind", "late", "too much", "stacked", "busy"],
    "self-judgment": ["my fault", "should have", "why didn't i", "annoyed at myself"],
    "relief": ["walk", "venting", "proud", "made it through", "better now"],
}

SELF_TALK_MARKERS = [
    "i should have",
    "i keep replaying",
    "i am behind",
    "why didn't i",
    "i made it through",
]


class TextUnderstandingService:
    def analyze_transcript_text(
        self,
        transcript: str,
        user_context: dict,
        prior_context: dict,
    ) -> TextUnderstandingResult:
        lowered = transcript.lower()
        themes = [theme for theme, words in KEYWORDS.items() if any(word in lowered for word in words)]
        if not themes:
            themes = ["general stress"]

        triggers = []
        if "deadline" in lowered or "exam" in lowered or "class" in lowered:
            triggers.append("academic pressure")
        if "talked over" in lowered or "meeting" in lowered:
            triggers.append("interpersonal friction")
        if "behind" in lowered or "too much" in lowered:
            triggers.append("feeling behind")
        if "tomorrow" in lowered:
            triggers.append("anticipatory stress")

        self_talk = [marker for marker in SELF_TALK_MARKERS if marker in lowered]
        repeated = [item for item, count in Counter(themes + triggers).items() if count >= 1]

        mixed = []
        if "proud" in lowered and ("exhausted" in lowered or "tired" in lowered):
            mixed.append("proud but drained")
        if "annoyed" in lowered and "myself" in lowered:
            mixed.append("frustrated with others and yourself")
        if "better" in lowered and "still" in lowered:
            mixed.append("relieved but still carrying tension")
        if "behind" in lowered and "starts" in lowered:
            mixed.append("already pressured before the day fully began")

        return TextUnderstandingResult(
            themes=themes,
            trigger_tags=triggers or ["general overload"],
            self_talk_markers=self_talk or ["trying to stay afloat"],
            repeated_concerns=repeated,
            candidate_mixed_feelings=mixed or ["stress mixed with a need for relief"],
        )
