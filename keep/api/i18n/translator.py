import json
import os
from pathlib import Path
from typing import Optional

from starlette.requests import Request

LOCALES_DIR = Path(__file__).parent / "locales"
DEFAULT_LOCALE = os.environ.get("KEEP_DEFAULT_LOCALE", "zh_CN")

_translations_cache: dict[str, dict[str, str]] = {}


def _load_translations(locale: str) -> dict[str, str]:
    """Load translations from JSON file."""
    if locale in _translations_cache:
        return _translations_cache[locale]

    locale_file = LOCALES_DIR / f"{locale}.json"
    if locale_file.exists():
        with open(locale_file, "r", encoding="utf-8") as f:
            translations = json.load(f)
    else:
        translations = {}

    _translations_cache[locale] = translations
    return translations


def _get_locale(request: Optional[Request] = None) -> str:
    """Get locale from request headers or fall back to default."""
    if request is not None:
        accept_language = request.headers.get("accept-language", "")
        if accept_language:
            for lang in accept_language.split(","):
                lang = lang.strip().split(";")[0].strip()
                # Normalize: zh-CN -> zh_CN, en-US -> en_US
                lang = lang.replace("-", "_")
                if lang in ("zh_CN", "zh"):
                    return "zh_CN"
                if lang in ("en_US", "en"):
                    return "en_US"
    return DEFAULT_LOCALE


def t(key: str, **kwargs) -> str:
    """Translate a key string, optionally with format parameters.

    Falls back to the original key if no translation is found.
    Supports both static strings and parameterized strings via kwargs.

    Usage:
        t("Alert not found")
        t("Provider {provider_type} not found", provider_type="slack")
    """
    # Use thread-local or context to get request if available
    # For route handlers, pass request explicitly via tr()
    locale = DEFAULT_LOCALE
    translations = _load_translations(locale)

    translated = translations.get(key, key)
    if kwargs:
        translated = translated.format(**kwargs)
    return translated


def tr(request: Request, key: str, **kwargs) -> str:
    """Translate with explicit Request context for Accept-Language support.

    Usage:
        tr(request, "Alert not found")
        tr(request, "Provider {provider_type} not found", provider_type="slack")
    """
    locale = _get_locale(request)
    translations = _load_translations(locale)

    translated = translations.get(key, key)
    if kwargs:
        translated = translated.format(**kwargs)
    return translated
