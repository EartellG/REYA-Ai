# utils/translate.py
from deep_translator import GoogleTranslator

def translate_to_english(text):
    try:
        return GoogleTranslator(source='auto', target='en').translate(text)
    except Exception as e:
        return text  # fallback: return original if translation fails
