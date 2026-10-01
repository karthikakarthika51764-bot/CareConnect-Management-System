import re

UNKNOWN_ANSWER = "I don't have that information right now. I can connect you with our staff."


def detect_language(message: str) -> str:
    if re.search(r"[\u0B80-\u0BFF]", message):
        return "ta"
    words = set(re.findall(r"[a-z]+", message.lower()))
    if words.intersection({"enakku", "venum", "irukka", "pannunga", "sollunga"}):
        return "ta-en"
    return "en"


def detect_intent(message: str) -> str:
    normalized = message.lower()
    if any(word in normalized for word in ("human", "person", "staff", "agent", "representative", "பேச", "மனிதர்")):
        return "HUMAN_HANDOFF"
    if any(word in normalized for word in ("cancel", "ரத்து")):
        return "CANCEL_APPOINTMENT"
    if any(word in normalized for word in ("reschedule", "change appointment", "மாற்ற")):
        return "RESCHEDULE_APPOINTMENT"
    if any(word in normalized for word in ("appointment", "book", "doctor", "டாக்டர்", "மருத்துவர்", "நேரம்")):
        return "BOOK_APPOINTMENT"
    if any(word in normalized for word in ("price", "fee", "cost", "விலை", "கட்டணம்")):
        return "PRICE_ENQUIRY"
    if any(word in normalized for word in ("time", "hours", "open", "timing", "நேரம்")):
        return "CLINIC_TIMING"
    return "GENERAL_ENQUIRY"


def handle_message(message: str, knowledge_answer: str = UNKNOWN_ANSWER) -> tuple[str, str, str, bool]:
    language = detect_language(message)
    intent = detect_intent(message)
    handoff = intent == "HUMAN_HANDOFF"
    if handoff:
        response = "I can connect you with our staff now." if language == "en" else "எங்கள் பணியாளருடன் உங்களை இணைக்கிறேன்."
    elif intent == "BOOK_APPOINTMENT":
        response = "I can help book that. Which doctor or service and preferred date would you like?" if language == "en" else "நிச்சயமாக. எந்த மருத்துவர் அல்லது சேவை, எந்த தேதி வேண்டும்?"
    elif intent in {"CANCEL_APPOINTMENT", "RESCHEDULE_APPOINTMENT"}:
        response = "Please share the appointment details so I can locate it securely." if language == "en" else "உங்கள் appointment விவரங்களைச் சொல்லுங்கள்."
    else:
        response = knowledge_answer
    return language, intent, response, handoff
