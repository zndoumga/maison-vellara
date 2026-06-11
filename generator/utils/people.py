"""
Person attribute generation (names, emails, phones) localised by nationality.

Uses Faker with a per-locale instance. Each Faker is seeded per-call so output
is deterministic for a given (date, source) run.
"""
from __future__ import annotations

import random
import unicodedata
from functools import lru_cache

from faker import Faker
from unidecode import unidecode

import config

_EMAIL_DOMAINS = ["gmail.com", "outlook.com", "icloud.com", "yahoo.com", "proton.me", "hey.com"]

# Curated romanised name pools for nationalities whose native scripts don't
# transliterate cleanly. These read as a Western CRM would actually store them.
_CURATED = {
    "JP": {
        "first": ["Haruto", "Yuto", "Sota", "Yuki", "Hina", "Sakura", "Yui", "Aoi", "Riku",
                  "Ren", "Kaito", "Mei", "Akari", "Hiroshi", "Kenji", "Yuna", "Sho", "Rina"],
        "last": ["Sato", "Suzuki", "Takahashi", "Tanaka", "Watanabe", "Ito", "Yamamoto",
                 "Nakamura", "Kobayashi", "Kato", "Yoshida", "Yamada", "Sasaki", "Matsumoto"],
    },
    "CN": {
        "first": ["Wei", "Fang", "Jing", "Min", "Lei", "Yan", "Hui", "Na", "Tao", "Ming",
                  "Hao", "Lan", "Xin", "Yu", "Chen", "Jun", "Ling", "Mei"],
        "last": ["Wang", "Li", "Zhang", "Liu", "Chen", "Yang", "Huang", "Zhao", "Wu",
                 "Zhou", "Xu", "Sun", "Ma", "Zhu", "Hu", "Lin", "Guo", "He"],
    },
    "KR": {
        "first": ["Min-jun", "Seo-yeon", "Ji-woo", "Ha-eun", "Do-yoon", "Ji-ho", "Eun-woo",
                  "Soo-ah", "Hyun", "Jae-won", "Min-seo", "Yu-jin", "Seo-jun", "Ha-yoon"],
        "last": ["Kim", "Lee", "Park", "Choi", "Jung", "Kang", "Cho", "Yoon", "Jang",
                 "Lim", "Han", "Oh", "Seo", "Shin", "Kwon", "Hwang"],
    },
    "AE": {
        "first": ["Mohammed", "Ahmed", "Ali", "Omar", "Khalid", "Fatima", "Aisha", "Mariam",
                  "Noora", "Hessa", "Sara", "Hamad", "Saeed", "Rashid", "Layla", "Yousef"],
        "last": ["Al-Maktoum", "Al-Nahyan", "Al-Rashid", "Al-Falasi", "Al-Hashimi",
                 "Al-Suwaidi", "Al-Mansoori", "Al-Qassimi", "Al-Zaabi", "Al-Kaabi", "Al-Marri"],
    },
    "SA": {
        "first": ["Abdullah", "Mohammed", "Fahad", "Sultan", "Faisal", "Noura", "Reem",
                  "Sara", "Lulu", "Maha", "Turki", "Bandar", "Nayef", "Hessa", "Latifa"],
        "last": ["Al-Saud", "Al-Rashid", "Al-Otaibi", "Al-Qahtani", "Al-Ghamdi", "Al-Harbi",
                 "Al-Zahrani", "Al-Shehri", "Al-Dossari", "Al-Mutairi"],
    },
}


@lru_cache(maxsize=None)
def _faker_for(locale: str) -> Faker:
    try:
        return Faker(locale)
    except (AttributeError, ValueError):
        return Faker("en_US")


def _ascii_slug(value: str) -> str:
    """Strip accents / non-latin so an email handle is always typable."""
    normalized = unicodedata.normalize("NFKD", value)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    return "".join(ch for ch in ascii_only.lower() if ch.isalnum())


def _has_non_latin(value: str) -> bool:
    for ch in value:
        if ch.isalpha():
            try:
                if "LATIN" not in unicodedata.name(ch):
                    return True
            except ValueError:
                return True
    return False


def _romanize(value: str) -> str:
    """Romanise non-latin scripts (CJK, Arabic, Cyrillic) to Latin letters,
    but leave European Latin names (incl. accents like é, ü) untouched."""
    if _has_non_latin(value):
        out = unidecode(value).strip()
        out = " ".join(p.capitalize() for p in out.split())
        return out or value
    return value


def make_person(rng: random.Random, nationality: str) -> dict:
    """
    Return a person dict: first_name, last_name, email, phone, preferred_language.
    Email/phone occasionally come back empty to mirror real CRM sparseness — the
    caller decides whether to apply that (different sources null different fields).
    """
    locale = config.NATIONALITY_LOCALE.get(nationality, "en_US")
    fake = _faker_for(locale)
    fake.seed_instance(rng.random())

    if nationality in _CURATED:
        # use a culturally-appropriate romanised name
        first = rng.choice(_CURATED[nationality]["first"])
        last = rng.choice(_CURATED[nationality]["last"])
    else:
        # Faker name, romanising any non-latin script (e.g. Cyrillic) while
        # keeping European Latin accents intact.
        first = _romanize(fake.first_name())
        last = _romanize(fake.last_name())

    en = _faker_for("en_US")
    en.seed_instance(rng.random())
    handle_first = _ascii_slug(first) or en.first_name().lower()
    handle_last = _ascii_slug(last) or en.last_name().lower()
    sep = rng.choice([".", "_", ""])
    suffix = rng.choice(["", "", "", str(rng.randint(1, 99))])
    domain = rng.choice(_EMAIL_DOMAINS)
    email = f"{handle_first}{sep}{handle_last}{suffix}@{domain}"

    try:
        phone = fake.phone_number()
    except Exception:
        phone = fake.numerify("+33 6 ## ## ## ##")

    language = locale.split("_")[0]

    return {
        "first_name": first,
        "last_name": last,
        "email": email,
        "phone": phone,
        "preferred_language": language,
    }
