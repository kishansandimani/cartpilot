"""Language helpers and spoken replies for the voice assistant.

Speech-to-text and text-to-speech run IN THE BROWSER (Web Speech API), which needs an internet connection in
Chrome/Edge and is not available in every browser. CartPilot does NOT provide offline voice.
"""
import re

SUPPORTED_LANGUAGES = [
    {"code": "en", "label": "English (India)", "recognition": "en-IN", "synthesis": "en-IN"},
    {"code": "hi", "label": "हिन्दी (Hindi)", "recognition": "hi-IN", "synthesis": "hi-IN"},
    {"code": "kn", "label": "ಕನ್ನಡ (Kannada)", "recognition": "kn-IN", "synthesis": "kn-IN",
     "note": "Kannada recognition/speech depends on your browser and installed voices."},
]
LANG_CODES = {l["code"] for l in SUPPORTED_LANGUAGES}


def detect_language(text: str, fallback: str = "en") -> str:
    """Guesses by Unicode script: Devanagari -> Hindi, Kannada script -> Kannada."""
    if re.search(r"[\u0C80-\u0CFF]", text):
        return "kn"
    if re.search(r"[\u0900-\u097F]", text):
        return "hi"
    return fallback if fallback in LANG_CODES else "en"


MESSAGES = {
    "navigate": {"en": "Opening {page}.", "hi": "{page} खोल रहा हूँ।", "kn": "{page} ತೆರೆಯುತ್ತಿದ್ದೇನೆ."},
    "searching": {"en": "Searching for that now.", "hi": "अभी खोज रहा हूँ।", "kn": "ಈಗ ಹುಡುಕುತ್ತಿದ್ದೇನೆ."},
    "added": {"en": "Added {title} to your cart.", "hi": "{title} आपकी कार्ट में जोड़ दिया।", "kn": "{title} ನಿಮ್ಮ ಕಾರ್ಟ್‌ಗೆ ಸೇರಿಸಲಾಗಿದೆ."},
    "removed": {"en": "Removed {title} from your cart.", "hi": "{title} कार्ट से हटा दिया।", "kn": "{title} ಅನ್ನು ಕಾರ್ಟ್‌ನಿಂದ ತೆಗೆಯಲಾಗಿದೆ."},
    "cart_total": {"en": "Your cart total is {total} for {count} items.", "hi": "आपकी कार्ट का कुल {total} है, {count} आइटम।", "kn": "ನಿಮ್ಮ ಕಾರ್ಟ್‌ನ ಒಟ್ಟು {total}, {count} ವಸ್ತುಗಳು."},
    "cart_empty": {"en": "Your cart is empty.", "hi": "आपकी कार्ट खाली है।", "kn": "ನಿಮ್ಮ ಕಾರ್ಟ್ ಖಾಲಿಯಾಗಿದೆ."},
    "confirm_purchase": {"en": "Your total is {total}. Please review the order summary on screen and confirm there. I will not pay without your confirmation.",
                         "hi": "आपका कुल {total} है। कृपया स्क्रीन पर ऑर्डर देखें और वहीं पुष्टि करें। आपकी पुष्टि के बिना भुगतान नहीं होगा।",
                         "kn": "ನಿಮ್ಮ ಒಟ್ಟು {total}. ದಯವಿಟ್ಟು ಪರದೆಯಲ್ಲಿ ಆರ್ಡರ್ ಪರಿಶೀಲಿಸಿ ಅಲ್ಲೇ ದೃಢೀಕರಿಸಿ. ನಿಮ್ಮ ದೃಢೀಕರಣವಿಲ್ಲದೆ ಪಾವತಿ ಆಗುವುದಿಲ್ಲ."},
    "spent": {"en": "You spent {amount} {period}.", "hi": "आपने {period} {amount} खर्च किए।", "kn": "ನೀವು {period} {amount} ಖರ್ಚು ಮಾಡಿದ್ದೀರಿ."},
    "no_spend": {"en": "I don't have any orders recorded {period}.", "hi": "{period} का कोई ऑर्डर दर्ज नहीं है।", "kn": "{period} ಯಾವುದೇ ಆರ್ಡರ್ ದಾಖಲಾಗಿಲ್ಲ."},
    "no_orders": {"en": "You have no orders yet.", "hi": "अभी कोई ऑर्डर नहीं है।", "kn": "ಇನ್ನೂ ಯಾವುದೇ ಆರ್ಡರ್ ಇಲ್ಲ."},
    "track": {"en": "Your latest order from {platform}, {product}, has status {status}. {tracking}",
              "hi": "{platform} से आपका ताज़ा ऑर्डर {product}, स्थिति {status}। {tracking}",
              "kn": "{platform} ನಿಂದ ನಿಮ್ಮ ಇತ್ತೀಚಿನ ಆರ್ಡರ್ {product}, ಸ್ಥಿತಿ {status}. {tracking}"},
    "need_product": {"en": "Which product do you mean? Ask me to search first, then say for example 'add the second product'.",
                     "hi": "कौन सा प्रोडक्ट? पहले खोजने को कहें, फिर बोलें 'दूसरा प्रोडक्ट जोड़ो'।",
                     "kn": "ಯಾವ ಉತ್ಪನ್ನ? ಮೊದಲು ಹುಡುಕಲು ಹೇಳಿ, ನಂತರ 'ಎರಡನೇ ಉತ್ಪನ್ನ ಸೇರಿಸು' ಎಂದು ಹೇಳಿ."},
    "need_two": {"en": "I need at least two products to compare. Search first, then ask me to compare.",
                 "hi": "तुलना के लिए कम से कम दो प्रोडक्ट चाहिए। पहले खोजें।", "kn": "ಹೋಲಿಸಲು ಕನಿಷ್ಠ ಎರಡು ಉತ್ಪನ್ನ ಬೇಕು. ಮೊದಲು ಹುಡುಕಿ."},
    "not_in_cart": {"en": "I couldn't find that item in your cart.", "hi": "वह आइटम कार्ट में नहीं मिला।", "kn": "ಆ ವಸ್ತು ಕಾರ್ಟ್‌ನಲ್ಲಿ ಸಿಗಲಿಲ್ಲ."},
    "no_reason": {"en": "I don't have a saved explanation for that product yet.", "hi": "इस प्रोडक्ट की कोई सहेजी हुई व्याख्या नहीं है।", "kn": "ಈ ಉತ್ಪನ್ನಕ್ಕೆ ಉಳಿಸಿದ ವಿವರಣೆ ಇಲ್ಲ."},
    "compare": {"en": "Comparing those products.", "hi": "इन प्रोडक्ट की तुलना कर रहा हूँ।", "kn": "ಆ ಉತ್ಪನ್ನಗಳನ್ನು ಹೋಲಿಸುತ್ತಿದ್ದೇನೆ."},
    "cheaper": {"en": "Looking for cheaper alternatives.", "hi": "सस्ते विकल्प खोज रहा हूँ।", "kn": "ಅಗ್ಗದ ಪರ್ಯಾಯಗಳನ್ನು ಹುಡುಕುತ್ತಿದ್ದೇನೆ."},
    "thinking": {"en": "Let me ask the shopping assistant.", "hi": "शॉपिंग असिस्टेंट से पूछता हूँ।", "kn": "ಶಾಪಿಂಗ್ ಸಹಾಯಕನನ್ನು ಕೇಳುತ್ತೇನೆ."},
}
PAGE_NAMES = {
    "assistant": {"en": "the shopping assistant", "hi": "शॉपिंग असिस्टेंट", "kn": "ಶಾಪಿಂಗ್ ಸಹಾಯಕ"},
    "cart": {"en": "your cart", "hi": "कार्ट", "kn": "ಕಾರ್ಟ್"},
    "orders": {"en": "your orders", "hi": "आपके ऑर्डर", "kn": "ನಿಮ್ಮ ಆರ್ಡರ್‌ಗಳು"},
    "profile": {"en": "your profile and settings", "hi": "प्रोफ़ाइल और सेटिंग", "kn": "ಪ್ರೊಫೈಲ್ ಮತ್ತು ಸೆಟ್ಟಿಂಗ್"},
    "platforms": {"en": "connected platforms", "hi": "कनेक्टेड प्लेटफ़ॉर्म", "kn": "ಸಂಪರ್ಕಿತ ಪ್ಲಾಟ್‌ಫಾರ್ಮ್‌ಗಳು"},
    "memory": {"en": "shopping memory", "hi": "शॉपिंग मेमोरी", "kn": "ಶಾಪಿಂಗ್ ಮೆಮೊರಿ"},
    "insights": {"en": "spending insights", "hi": "खर्च की जानकारी", "kn": "ಖರ್ಚಿನ ಒಳನೋಟ"},
    "discover": {"en": "product discovery", "hi": "प्रोडक्ट खोज", "kn": "ಉತ್ಪನ್ನ ಅನ್ವೇಷಣೆ"},
    "compare": {"en": "product comparison", "hi": "प्रोडक्ट तुलना", "kn": "ಉತ್ಪನ್ನ ಹೋಲಿಕೆ"},
    "overview": {"en": "the overview", "hi": "ओवरव्यू", "kn": "ಅವಲೋಕನ"},
}


def t(key: str, lang: str = "en", **kw) -> str:
    table = MESSAGES.get(key, {})
    template = table.get(lang) or table.get("en") or key
    return template.format(**kw)


def page_name(target: str, lang: str = "en") -> str:
    names = PAGE_NAMES.get(target, {})
    return names.get(lang) or names.get("en") or target
