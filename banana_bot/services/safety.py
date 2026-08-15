from __future__ import annotations


RISK_MARKERS = {
    "RU": ("вызвать рвоту", "не есть", "голодать", "очищение", "компенсировать ед", "лечебн", "диабет", "беремен", "почки"),
    "EN": ("make myself vomit", "stop eating", "starve", "purge", "compensate food", "medical diet", "diabetes", "pregnan", "kidney"),
}


def safety_reply(value: str, lang: str) -> str | None:
    lowered = value.lower()
    if not any(marker in lowered for marker in RISK_MARKERS.get(lang, RISK_MARKERS["EN"])):
        return None
    if lang == "RU":
        return "С этим лучше поможет врач или профильный специалист. Я могу только посчитать еду 💛"
    return "A doctor or qualified specialist can help with this. I can only estimate food 💛"
