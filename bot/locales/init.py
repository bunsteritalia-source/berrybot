import json
import os

_locales = {}

def load_locale(lang):
    path = os.path.join(os.path.dirname(__file__), f'{lang}.json')
    with open(path, 'r', encoding='utf-8') as f:
        _locales[lang] = json.load(f)

def get_text(lang, key):
    if lang not in _locales:
        load_locale(lang)
    return _locales[lang].get(key, key)
