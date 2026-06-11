"""
CRM clients.

Clients are registered at the till during a sale (the boutique flow), so new
clients are created on demand by the POS generator via `make_new_client`.
At the end of a day the CRM "delta" export is just the set of client records
created or modified that day — exactly what a real CRM nightly extract emits.

`vip_tier` is always 'standard' here; tiering from cumulative spend is dbt's job.
"""
from __future__ import annotations

import random
from datetime import date

import config
from utils import identity, people
from utils.rng import chance, weighted_pairs

# Country of residence usually tracks nationality; this maps the nationality
# code to a default residence country (a few are expat-skewed).
_NATIONALITY_COUNTRY = {
    "FR": "FR", "CN": "CN", "US": "US", "GB": "GB", "JP": "JP", "KR": "KR",
    "AE": "AE", "IT": "IT", "DE": "DE", "RU": "RU", "SA": "SA", "CH": "CH",
    "BR": "BR", "AU": "AU", "SG": "SG", "OTHER": "FR",
}


def choose_nationality(rng: random.Random) -> str:
    return weighted_pairs(rng, config.CLIENT_NATIONALITIES)


def make_new_client(
    state, rng: random.Random, d: date, store_id: str, advisor_id: str, when_iso: str
) -> dict:
    """Create, persist and return a new client record."""
    seq = state.next_seq("client")
    nationality = choose_nationality(rng)
    person = people.make_person(rng, nationality)

    # residence: mostly home country, ~20% resident elsewhere (global jet-set)
    if chance(rng, 0.20):
        residence = choose_nationality(rng)
        residence = _NATIONALITY_COUNTRY.get(residence, "FR")
    else:
        residence = _NATIONALITY_COUNTRY.get(nationality, "FR")

    email = person["email"] if not chance(rng, 0.05) else None
    phone = person["phone"]  # every boutique client is captured with a phone

    rec = {
        "client_id": identity.client_id(seq),
        "first_name": person["first_name"],
        "last_name": person["last_name"],
        "email": email,
        "phone": phone,
        "nationality": nationality,
        "country_of_residence": residence,
        "preferred_language": person["preferred_language"],
        "assigned_advisor_id": advisor_id,
        "assigned_store_id": store_id,
        "acquisition_channel": "boutique",
        "vip_tier": "standard",
        "gdpr_consent": chance(rng, 0.88),
        "created_at": when_iso,
        "updated_at": when_iso,
    }
    state.add_client(rec)
    return rec


def generate_delta(d: date, state) -> list[dict]:
    """Flatten all clients created/updated on `d` into CRM export rows."""
    changed = state.clients_changed_on(d)
    rows = []
    for rec in changed:
        rows.append(
            {
                "client_id": rec["client_id"],
                "first_name": rec["first_name"],
                "last_name": rec["last_name"],
                "email": rec.get("email"),
                "phone": rec.get("phone"),
                "nationality": rec["nationality"],
                "country_of_residence": rec["country_of_residence"],
                "preferred_language": rec["preferred_language"],
                "assigned_advisor_id": rec["assigned_advisor_id"],
                "assigned_store_id": rec["assigned_store_id"],
                "acquisition_channel": rec["acquisition_channel"],
                "vip_tier": rec["vip_tier"],
                "gdpr_consent": rec["gdpr_consent"],
                "created_at": rec["created_at"],
                "updated_at": rec["updated_at"],
            }
        )
    return rows
