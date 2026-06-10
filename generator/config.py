"""
Static reference data for Maison Vellara — luxury leather goods brand.
"""

BRAND_NAME = "Maison Vellara"

# ---------------------------------------------------------------------------
# Stores
# ---------------------------------------------------------------------------
STORES = [
    {"store_id": "ST001", "name": "Paris Faubourg",           "city": "Paris",    "country": "FR", "timezone": "Europe/Paris",     "tier": "flagship", "avg_daily_tx": 50},
    {"store_id": "ST002", "name": "Paris Marais",              "city": "Paris",    "country": "FR", "timezone": "Europe/Paris",     "tier": "standard", "avg_daily_tx": 28},
    {"store_id": "ST003", "name": "London Mayfair",            "city": "London",   "country": "GB", "timezone": "Europe/London",    "tier": "flagship", "avg_daily_tx": 30},
    {"store_id": "ST004", "name": "Milan Via Montenapoleone",  "city": "Milan",    "country": "IT", "timezone": "Europe/Rome",      "tier": "standard", "avg_daily_tx": 22},
    {"store_id": "ST005", "name": "Dubai Mall",                "city": "Dubai",    "country": "AE", "timezone": "Asia/Dubai",       "tier": "flagship", "avg_daily_tx": 38},
    {"store_id": "ST006", "name": "Tokyo Ginza",               "city": "Tokyo",    "country": "JP", "timezone": "Asia/Tokyo",       "tier": "flagship", "avg_daily_tx": 35},
    {"store_id": "ST007", "name": "New York Madison",          "city": "New York", "country": "US", "timezone": "America/New_York", "tier": "flagship", "avg_daily_tx": 32},
    {"store_id": "ST008", "name": "Geneva Rue du Rhône",       "city": "Geneva",   "country": "CH", "timezone": "Europe/Zurich",    "tier": "standard", "avg_daily_tx": 15},
]

STORE_CURRENCY = {
    "ST001": "EUR", "ST002": "EUR", "ST003": "GBP",
    "ST004": "EUR", "ST005": "AED", "ST006": "JPY",
    "ST007": "USD", "ST008": "CHF",
}

CURRENCY_FX_TO_EUR = {
    "EUR": 1.00, "GBP": 1.17, "AED": 0.25,
    "JPY": 0.0061, "USD": 0.92, "CHF": 1.05,
}

# Store opening hours (local time)
STORE_HOURS = {
    "ST001": (10, 19), "ST002": (10, 19), "ST003": (10, 18),
    "ST004": (10, 19), "ST005": (10, 22), "ST006": (11, 20),
    "ST007": (10, 18), "ST008": (10, 18),
}

# ---------------------------------------------------------------------------
# Product catalogue
# ---------------------------------------------------------------------------
CATEGORIES = {
    "Handbags": {
        "styles": ["Alma", "Riviera", "Capucine", "Constella", "Seren"],
        "colors": ["Noir", "Cognac", "Burgundy", "Ivoire"],
        "base_price_eur": 2800,
        "price_variance": 600,
        "demand_weight": 0.35,
    },
    "Small Leather Goods": {
        "styles": ["Compact Wallet", "Card Holder", "Zip Coin Purse", "Key Pouch", "Passport Cover", "Long Wallet"],
        "colors": ["Noir", "Cognac", "Ivoire"],
        "base_price_eur": 380,
        "price_variance": 120,
        "demand_weight": 0.25,
    },
    "Shoes": {
        "styles": ["Loafer Classic", "Chelsea Boot", "Derby Oxford", "Mule Slide", "Ankle Boot"],
        "colors": ["Noir", "Cognac", "Burgundy"],
        "base_price_eur": 850,
        "price_variance": 200,
        "demand_weight": 0.15,
    },
    "Leather Jackets": {
        "styles": ["Biker Slim", "Blazer Nappa", "Overshirt", "Racer"],
        "colors": ["Noir", "Cognac", "Burgundy"],
        "base_price_eur": 3200,
        "price_variance": 800,
        "demand_weight": 0.10,
    },
    "Travel Bags": {
        "styles": ["Weekender", "Holdall", "Backpack", "Garment Carrier"],
        "colors": ["Noir", "Cognac", "Ivoire"],
        "base_price_eur": 1800,
        "price_variance": 400,
        "demand_weight": 0.08,
    },
    "Belts": {
        "styles": ["Classic Pin", "Double Tour", "Reversible"],
        "colors": ["Noir", "Cognac", "Burgundy"],
        "base_price_eur": 420,
        "price_variance": 80,
        "demand_weight": 0.07,
    },
}

# ---------------------------------------------------------------------------
# Advisors distributed across stores
# ---------------------------------------------------------------------------
ADVISORS = [
    {"advisor_id": "ADV001", "store_id": "ST001"},
    {"advisor_id": "ADV002", "store_id": "ST001"},
    {"advisor_id": "ADV003", "store_id": "ST001"},
    {"advisor_id": "ADV004", "store_id": "ST001"},
    {"advisor_id": "ADV005", "store_id": "ST002"},
    {"advisor_id": "ADV006", "store_id": "ST002"},
    {"advisor_id": "ADV007", "store_id": "ST002"},
    {"advisor_id": "ADV008", "store_id": "ST003"},
    {"advisor_id": "ADV009", "store_id": "ST003"},
    {"advisor_id": "ADV010", "store_id": "ST003"},
    {"advisor_id": "ADV011", "store_id": "ST004"},
    {"advisor_id": "ADV012", "store_id": "ST004"},
    {"advisor_id": "ADV013", "store_id": "ST004"},
    {"advisor_id": "ADV014", "store_id": "ST005"},
    {"advisor_id": "ADV015", "store_id": "ST005"},
    {"advisor_id": "ADV016", "store_id": "ST005"},
    {"advisor_id": "ADV017", "store_id": "ST005"},
    {"advisor_id": "ADV018", "store_id": "ST006"},
    {"advisor_id": "ADV019", "store_id": "ST006"},
    {"advisor_id": "ADV020", "store_id": "ST006"},
    {"advisor_id": "ADV021", "store_id": "ST006"},
    {"advisor_id": "ADV022", "store_id": "ST007"},
    {"advisor_id": "ADV023", "store_id": "ST007"},
    {"advisor_id": "ADV024", "store_id": "ST007"},
    {"advisor_id": "ADV025", "store_id": "ST007"},
    {"advisor_id": "ADV026", "store_id": "ST008"},
    {"advisor_id": "ADV027", "store_id": "ST008"},
    {"advisor_id": "ADV028", "store_id": "ST008"},
]

# ---------------------------------------------------------------------------
# Technicians (after-sales staff, not tied to advisors)
# ---------------------------------------------------------------------------
TECHNICIANS = [
    {"technician_id": "TECH001", "speciality": "leather_repair"},
    {"technician_id": "TECH002", "speciality": "leather_repair"},
    {"technician_id": "TECH003", "speciality": "hardware"},
    {"technician_id": "TECH004", "speciality": "engraving"},
    {"technician_id": "TECH005", "speciality": "cleaning"},
    {"technician_id": "TECH006", "speciality": "leather_repair"},
]

# ---------------------------------------------------------------------------
# Wholesale partners
# ---------------------------------------------------------------------------
WHOLESALE_PARTNERS = [
    {"partner_id": "GLF", "name": "Galeries Lafayette", "city": "Paris",   "country": "FR"},
    {"partner_id": "LBM", "name": "Le Bon Marché",      "city": "Paris",   "country": "FR"},
    {"partner_id": "PRT", "name": "Printemps",           "city": "Paris",   "country": "FR"},
]

# Each partner stocks a subset of SKUs — not the full catalogue
WHOLESALE_ASSORTMENT_RATE = 0.40  # partners carry ~40% of catalogue

# Wholesale price is ~60% of retail
WHOLESALE_PRICE_FACTOR = 0.60

# ---------------------------------------------------------------------------
# Seasonality
# ---------------------------------------------------------------------------
MONTHLY_MULTIPLIERS = [
    1.10,  # Jan  — post-holiday, fashion week buzz
    1.20,  # Feb  — Paris/Milan fashion week
    0.90,  # Mar
    0.85,  # Apr
    0.95,  # May
    1.00,  # Jun
    1.10,  # Jul  — tourist peak
    0.80,  # Aug  — locals away
    1.05,  # Sep  — fashion week
    1.00,  # Oct
    1.10,  # Nov  — pre-holiday
    1.40,  # Dec  — Christmas peak
]

DOW_MULTIPLIERS = {
    0: 0.75,  # Monday
    1: 0.85,  # Tuesday
    2: 0.90,  # Wednesday
    3: 0.95,  # Thursday
    4: 1.10,  # Friday
    5: 1.30,  # Saturday
    6: 0.80,  # Sunday
}

# ---------------------------------------------------------------------------
# Client demographics
# ---------------------------------------------------------------------------
CLIENT_NATIONALITIES = [
    ("FR", 0.18), ("CN", 0.16), ("US", 0.12), ("GB", 0.08),
    ("JP", 0.07), ("KR", 0.06), ("AE", 0.05), ("IT", 0.05),
    ("DE", 0.04), ("RU", 0.04), ("SA", 0.03), ("CH", 0.03),
    ("BR", 0.02), ("AU", 0.02), ("SG", 0.02), ("OTHER", 0.03),
]

NATIONALITY_LOCALE = {
    "FR": "fr_FR", "CN": "zh_CN", "US": "en_US", "GB": "en_GB",
    "JP": "ja_JP", "KR": "ko_KR", "AE": "ar_AA", "IT": "it_IT",
    "DE": "de_DE", "RU": "ru_RU", "SA": "ar_AA", "CH": "de_CH",
    "BR": "pt_BR", "AU": "en_AU", "SG": "en_SG", "OTHER": "en_US",
}

ACQUISITION_CHANNELS = ["boutique", "ecommerce", "event", "pr_gifting", "word_of_mouth", "wholesale_referral"]
ACQUISITION_CHANNEL_WEIGHTS = [0.45, 0.25, 0.10, 0.05, 0.10, 0.05]

PAYMENT_METHODS = ["card", "cash", "bank_transfer", "digital_wallet"]
PAYMENT_METHOD_WEIGHTS = [0.70, 0.10, 0.12, 0.08]

AFTER_SALES_SERVICE_TYPES = ["repair", "cleaning", "engraving", "authentication", "resizing"]
AFTER_SALES_SERVICE_WEIGHTS = [0.45, 0.25, 0.15, 0.10, 0.05]

AFTER_SALES_SERVICE_DURATION_DAYS = {
    "repair": (7, 21),
    "cleaning": (3, 7),
    "engraving": (2, 5),
    "authentication": (5, 14),
    "resizing": (3, 7),
}

AFTER_SALES_SERVICE_COST = {
    "repair": (80, 350),
    "cleaning": (40, 120),
    "engraving": (30, 80),
    "authentication": (50, 100),
    "resizing": (40, 90),
}

CORRECTION_REASON_CODES = ["price_adjustment", "vat_error", "wrong_sku", "quantity_error"]

# ---------------------------------------------------------------------------
# E-commerce
# ---------------------------------------------------------------------------
ECOM_SHIPPING_COUNTRIES = [
    ("FR", 0.22), ("DE", 0.10), ("GB", 0.10), ("US", 0.15),
    ("JP", 0.08), ("CN", 0.07), ("AE", 0.06), ("CH", 0.05),
    ("IT", 0.05), ("KR", 0.04), ("OTHER", 0.08),
]

ECOM_REFERRERS = ["direct", "google", "instagram", "email_campaign", "other"]
ECOM_REFERRER_WEIGHTS = [0.35, 0.30, 0.20, 0.10, 0.05]

ECOM_DEVICE_TYPES = ["mobile", "desktop", "tablet"]
ECOM_DEVICE_WEIGHTS = [0.60, 0.30, 0.10]

ECOM_EVENT_TYPES = ["session_start", "product_view", "add_to_cart", "checkout_started", "checkout_completed", "session_end"]

# Conversion funnel rates (conditional probabilities)
FUNNEL = {
    "session_to_product_view": 0.65,
    "product_view_to_add_to_cart": 0.18,
    "add_to_cart_to_checkout": 0.45,
    "checkout_to_complete": 0.72,
}
