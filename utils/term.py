"""
Academic year and term calculations for BS CTET advising.
AY 2026-2027 = Fall 2026 + Spring 2027 + Summer 2027
"""
from datetime import datetime
from typing import Optional, Tuple

TERMS = ["fall", "spring", "summer", "winterm"]


def get_current_academic_year() -> str:
    """Return current AY as 'YYYY-YYYY' (e.g., 2026-2027)."""
    now = datetime.now()
    # Fall starts new AY (e.g., Fall 2026 = AY 2026-2027)
    if now.month >= 8:  # Aug onwards = next academic year
        return f"{now.year}-{now.year + 1}"
    return f"{now.year - 1}-{now.year}"


def parse_academic_year(ay_str: str) -> Optional[Tuple[int, int]]:
    """Parse '2026-2027' -> (2026, 2027)."""
    try:
        parts = ay_str.strip().split("-")
        if len(parts) == 2:
            return (int(parts[0]), int(parts[1]))
    except (ValueError, IndexError):
        pass
    return None


def get_term_for_ay(term: str, start_year: int) -> str:
    """Return label like 'Fall 2026', 'Spring 2027', etc."""
    if term.lower() == "fall":
        return f"Fall {start_year}"
    if term.lower() == "spring":
        return f"Spring {start_year + 1}"
    if term.lower() == "summer":
        return f"Summer {start_year + 1}"
    if term.lower() == "winterm":
        return f"Winterm {start_year}"
    return f"{term} {start_year}"


def get_ay_for_term_label(label: str) -> Optional[str]:
    """Extract AY from term label like 'Fall 2026' -> '2026-2027'."""
    import re
    m = re.search(r"(Fall|Spring|Summer|Winterm)\s+(\d{4})", label, re.I)
    if m:
        year = int(m.group(2))
        term_name = m.group(1).lower()
        if term_name == "fall":
            return f"{year}-{year + 1}"
        if term_name in ("spring", "summer", "winterm"):
            return f"{year - 1}-{year}"
    return None


def is_future_term(term_label: str) -> bool:
    """True if term is in the future (not yet published in Access Stout)."""
    import re
    m = re.search(r"(Fall|Spring|Summer|Winterm)\s+(\d{4})", term_label, re.I)
    if not m:
        return True
    year = int(m.group(2))
    term_name = m.group(1).lower()
    now = datetime.now()
    if term_name == "fall":
        term_month = 9
    elif term_name == "spring":
        term_month = 1
    elif term_name == "summer":
        term_month = 6
    elif term_name == "winterm":
        term_month = 1
    else:
        return True
    if year > now.year:
        return True
    if year == now.year and term_month > now.month:
        return True
    return False
