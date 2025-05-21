import json

def get_localization(lang: str, key: str) -> str:
    with open(f'locales/{lang}.json', 'r', encoding='utf-8') as f:
        translations = json.load(f)
    return translations.get(key, key)