"""
Stout Core + BS CTET advising rules engine.
"""
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml


def load_yaml(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


# Load configs from data/
_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
STOUT_CORE = load_yaml(_DATA_DIR / "stout_core_rules.yaml")
COURSE_MATRIX = load_yaml(_DATA_DIR / "course_matrix.yaml")

STOUT_CORE_TOTAL = STOUT_CORE.get("total_credits", 40)
RES_REQUIRED = STOUT_CORE.get("RES", {}).get("count", 2)
GLP_REQUIRED = STOUT_CORE.get("GLP", {}).get("count", 2)
COMSK_COURSES = STOUT_CORE.get("categories", {}).get("COMSK", {}).get("required_courses", [])
ARNS_EXCLUDE = STOUT_CORE.get("categories", {}).get("ARNS", {}).get("exclude_developmental", [])


def is_developmental_math(code: str) -> bool:
    """True if course is developmental (does not count toward ARNS)."""
    code_upper = code.upper().replace(" ", "-")
    for exc in ARNS_EXCLUDE:
        if exc.upper().replace(" ", "-") in code_upper or code_upper in exc.upper():
            return True
    return "MATH-90" in code_upper or "INTERMEDIATE ALGEBRA" in code_upper


def get_course_availability(
    course_code: str, academic_year: str, term: str
) -> Tuple[bool, str]:
    """
    Return (available: bool, note: str).
    Handles CTE 360/560 special rule by academic year:
    - AY 2026-2027: Fall + Summer
    - AY 2027-2028+: Spring + Summer
    """
    code = course_code.upper().replace(" ", "-")
    courses = COURSE_MATRIX.get("courses", {})
    c = courses.get(code)
    if not c:
        return False, "Availability to confirm in Access Stout"

    special = c.get("special_rule")
    if special:
        ay_logic = COURSE_MATRIX.get("academic_year_logic", {}).get(special, {})
        default_ay = ay_logic.get("default_future", "2027-2028")
        ay_data = ay_logic.get(academic_year)
        if not ay_data:
            # Use 2027-2028 pattern for any future year not explicitly listed
            ay_data = ay_logic.get(default_ay)
        if ay_data:
            term_lower = term.lower()
            avail = ay_data.get(term_lower, False)
            # Summer is always available for 360/560
            if term_lower == "summer":
                avail = True
            note = f"AY {academic_year}: {term} {'available' if avail else 'not in rotation'}"
            return bool(avail), note

    base_terms = c.get("terms", [])
    avail = term.lower() in [t.lower() for t in base_terms]
    note = c.get("notes", "See matrix")
    return avail, note


def check_stout_core_status(
    parsed: Dict[str, Any], plan_year: str
) -> Dict[str, Any]:
    """
    Evaluate Stout Core completion from parsed audit.
    Returns status by category + RES/GLP counts.
    """
    courses = parsed.get("courses", [])
    attrs = parsed.get("attributes_seen", {})
    res_count = attrs.get("RES", 0)
    glp_count = attrs.get("GLP", 0)

    earned = parsed.get("total_credits_earned", 0)
    in_prog = parsed.get("total_credits_in_progress", 0)

    status = {
        "comsk_credits": 0,
        "comsk_complete": False,
        "arns_credits": 0,
        "arns_has_math_stat": False,
        "arns_has_lab_science": False,
        "arns_complete": False,
        "arhum_credits": 0,
        "sbsc_credits": 0,
        "srer_credits": 0,
        "electives_credits": 0,
        "res_count": res_count,
        "glp_count": glp_count,
        "res_complete": res_count >= RES_REQUIRED,
        "glp_complete": glp_count >= GLP_REQUIRED,
        "total_core_credits": 0,
        "remaining_credits": STOUT_CORE_TOTAL,
        "risk_flags": [],
    }

    # Heuristic: map common courses to categories (handle ParsedCourse or dict)
    for pc in courses:
        dnq = getattr(pc, "does_not_count", pc.get("does_not_count", False) if isinstance(pc, dict) else False)
        if dnq:
            continue
        code = (getattr(pc, "code", None) or pc.get("code", "") or "").upper()
        cred = getattr(pc, "credits", pc.get("credits", 0) if isinstance(pc, dict) else 0)
        if code in ["ENGL-101", "ENGL-102", "COMST-100"]:
            status["comsk_credits"] += cred
        elif not is_developmental_math(code):
            if "MATH" in code or "STAT" in code:
                status["arns_credits"] += cred
                status["arns_has_math_stat"] = True
            elif any(x in code for x in ["BIO", "CHEM", "PHYS", "GEOL", "ASTR"]):
                status["arns_credits"] += cred
                if "LAB" in code or "L" in code or cred >= 4:
                    status["arns_has_lab_science"] = True
            elif "ARHU" in str(getattr(pc, "category", pc.get("category") if isinstance(pc, dict) else None) or "") or any(a in code for a in ["ART", "HIST", "MUS", "PHIL"]):
                status["arhum_credits"] += cred
            elif any(a in code for a in ["SOC", "PSYC", "ECON", "POL"]):
                status["sbsc_credits"] += cred
            elif "SRER" in str(getattr(pc, "category", pc.get("category") if isinstance(pc, dict) else None) or ""):
                status["srer_credits"] += cred

    status["comsk_complete"] = status["comsk_credits"] >= 9
    status["arns_complete"] = (
        status["arns_credits"] >= 10
        and status["arns_has_math_stat"]
        and status["arns_has_lab_science"]
    )
    status["total_core_credits"] = (
        status["comsk_credits"]
        + status["arns_credits"]
        + status["arhum_credits"]
        + status["sbsc_credits"]
        + status["srer_credits"]
        + status["electives_credits"]
    )
    status["remaining_credits"] = max(0, STOUT_CORE_TOTAL - status["total_core_credits"])

    if not status["arns_has_lab_science"]:
        status["risk_flags"].append("Missing ARNS lab science")
    if not status["arns_has_math_stat"]:
        status["risk_flags"].append("Missing MATH/STAT in ARNS")
    if not status["res_complete"]:
        status["risk_flags"].append(f"RES shortfall: need {RES_REQUIRED - res_count} more")
    if not status["glp_complete"]:
        status["risk_flags"].append(f"GLP shortfall: need {GLP_REQUIRED - glp_count} more")

    return status


def get_double_count_candidates(
    need_res: bool, need_glp: bool, unmet_categories: List[str]
) -> List[Dict[str, str]]:
    """
    Suggest courses that satisfy RES/GLP AND an unmet Stout Core category.
    Returns list of {course, knocks_out, category}.
    """
    # Common double-count options (RES+SBSC, GLP+ARHUM, etc.)
    candidates = []
    if need_res and "SBSC" in unmet_categories:
        candidates.append({
            "course": "SOC 225",
            "knocks_out": "1 RES + remaining SBSC credit",
            "category": "RES + SBSC",
        })
    if need_glp and "ARHUM" in unmet_categories:
        candidates.append({
            "course": "HIST 2XX (GLP)",
            "knocks_out": "1 GLP + ARHUM credit",
            "category": "GLP + ARHUM",
        })
    if need_res and "ARHUM" in unmet_categories:
        candidates.append({
            "course": "PHIL 2XX (RES)",
            "knocks_out": "1 RES + ARHUM credit",
            "category": "RES + ARHUM",
        })
    if need_glp and "SBSC" in unmet_categories:
        candidates.append({
            "course": "PSYC 2XX (GLP)",
            "knocks_out": "1 GLP + SBSC credit",
            "category": "GLP + SBSC",
        })
    return candidates
