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
        return "Мне жаль, что вам приходится с этим сталкиваться. Я могу помочь только с нейтральной ориентировочной оценкой еды, но не с диагнозом, лечебной диетой или опасной компенсацией. Пожалуйста, обсудите это с врачом или профильным специалистом; если есть непосредственная опасность — обратитесь в экстренную службу."
    return "I'm sorry you're dealing with this. I can only provide a neutral approximate food estimate, not a diagnosis, medical diet, or harmful compensation advice. Please speak with a doctor or qualified specialist; if there is immediate danger, contact emergency services."
