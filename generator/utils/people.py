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

import config

_EMAIL_DOMAINS = ["gmail.com", "outlook.com", "icloud.com", "yahoo.com", "proton.me", "hey.com"]


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


def make_person(rng: random.Random, nationality: str) -> dict:
    """
    Return a person dict: first_name, last_name, email, phone, preferred_language.
    Email/phone occasionally come back empty to mirror real CRM sparseness — the
    caller decides whether to apply that (different sources null different fields).
    """
    locale = config.NATIONALITY_LOCALE.get(nationality, "en_US")
    fake = _faker_for(locale)
    fake.seed_instance(rng.random())

    first = fake.first_name()
    last = fake.last_name()

    # Email handles must be latin/typable. Non-latin names (JP/CN/KR/AE/RU)
    # strip to empty, so fall back to a romanised handle — realistic, since
    # those clients commonly use a romanised or unrelated email alias.
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
