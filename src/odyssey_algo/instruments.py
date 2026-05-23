"""Default instrument subscriptions (no secrets)."""

INSTRUMENTS = {
    "indexes": [
        "NSE_INDEX|Nifty 50",
        "NSE_INDEX|Nifty Bank",
        "NSE_INDEX|Nifty IT",
        "NSE_INDEX|Nifty Pharma",
    ],
    "stocks": [
        "NSE_EQ|INE020B01018",  # Reliance Industries
        "NSE_EQ|INE467B01029",  # TCS
        "NSE_EQ|INE062A01020",  # HDFC Bank
        "NSE_EQ|INE002A01015",  # Axis Bank
    ],
}


def get_all_instruments() -> list[str]:
    """Return all configured instrument keys."""
    instruments: list[str] = []
    instruments.extend(INSTRUMENTS.get("indexes", []))
    instruments.extend(INSTRUMENTS.get("stocks", []))
    return instruments
