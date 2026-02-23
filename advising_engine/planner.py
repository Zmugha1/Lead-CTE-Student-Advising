"""
Semester-by-semester planning using course matrix and constraints.
Respects CTE 360/560 year-based availability.
"""
from typing import Any, Dict, List, Optional

from advising_engine import rules
from utils.term import get_current_academic_year, get_term_for_ay


def build_semester_plan(
    parsed: Dict[str, Any],
    student: Dict[str, Any],
    num_terms: int = 6,
) -> List[Dict[str, str]]:
    """
    Build semester plan rows.
    Each row: Term, Recommended courses, Credits, Why this term, Notes
    """
    plan_year = student.get("plan_year", "2023")
    pacing = student.get("pacing", "full")
    credits_per_term = 9 if pacing == "full" else 6
    if pacing == "part":
        credits_per_term = min(credits_per_term, 6)

    ay = get_current_academic_year()
    ay_start = int(ay.split("-")[0])

    core_status = rules.check_stout_core_status(parsed, plan_year)
    courses_taken = {c.code.upper() for c in parsed.get("courses", []) if hasattr(c, "code")}
    # Handle both ParsedCourse objects and dicts
    if parsed.get("courses"):
        first = parsed["courses"][0]
        if isinstance(first, dict):
            courses_taken = {c.get("code", "").upper() for c in parsed["courses"]}
        else:
            courses_taken = {c.code.upper() for c in parsed["courses"]}

    rows = []
    terms_ordered = ["summer", "fall", "spring"]
    term_idx = 0
    current_ay = ay_start
    remaining_ctet = _get_remaining_ctet_courses(courses_taken)
    remaining_core = _get_remaining_core_needs(core_status)

    for _ in range(num_terms):
        if term_idx % 3 == 0:
            term_name = "summer"
        elif term_idx % 3 == 1:
            term_name = "fall"
        else:
            term_name = "spring"

        term_label = get_term_for_ay(term_name, current_ay)
        if term_name == "fall":
            ay_key = f"{current_ay}-{current_ay + 1}"
        else:
            ay_key = f"{current_ay - 1}-{current_ay}"

        rec_courses = []
        cred_sum = 0
        why = []
        notes = []

        # Prioritize completion-risk items when within 12 credits of graduation
        total_credits = (
            parsed.get("total_credits_earned", 0)
            + parsed.get("total_credits_in_progress", 0)
            + sum(r.get("Credits", 0) if isinstance(r.get("Credits"), (int, float)) else 0 for r in rows)
        )
        near_graduation = total_credits >= 105

        # Add CTET courses based on availability
        for ccode in list(remaining_ctet)[:3]:
            if cred_sum >= credits_per_term:
                break
            avail, note = rules.get_course_availability(ccode, ay_key, term_name)
            if avail:
                cred = _get_credits_for_course(ccode)
                rec_courses.append(ccode)
                cred_sum += cred
                why.append(f"{ccode} available per matrix")
                if ccode in remaining_ctet:
                    remaining_ctet.remove(ccode)

        # Add core fill-ins if needed (placeholder - real logic would use course catalog)
        if cred_sum < credits_per_term and remaining_core and near_graduation:
            if "ENGL-102" in remaining_core:
                rec_courses.append("ENGL-102 (if needed)")
                cred_sum += 3
                why.append("Complete COMSK")
                remaining_core.discard("ENGL-102")
            if "NSLAB" in remaining_core and cred_sum < credits_per_term:
                rec_courses.append("Natural Science w/ Lab (confirm in Access Stout)")
                cred_sum += 4
                why.append("Complete ARNS lab science")
                remaining_core.discard("NSLAB")

        if is_future_term(term_label):
            notes.append("Tentative until published in Access Stout")

        rows.append({
            "Term": term_label,
            "Recommended Courses": ", ".join(rec_courses) if rec_courses else "—",
            "Credits": str(cred_sum),
            "Why This Term": "; ".join(why) if why else "Availability to confirm in Access Stout",
            "Notes": "; ".join(notes) if notes else "",
        })

        term_idx += 1
        if term_name == "spring":
            current_ay += 1

    return rows


def _get_remaining_ctet_courses(taken: set) -> List[str]:
    """Return CTET courses not yet taken (prioritized for planning)."""
    from advising_engine.rules import COURSE_MATRIX
    all_ctet = set(COURSE_MATRIX.get("courses", {}).keys())
    taken_norm = {str(t).upper().replace(" ", "-") for t in taken}
    remaining = all_ctet - taken_norm
    # Priority order for planning: core CTE courses first
    priority = ["CTE-302", "CTE-350", "CTE-405", "CTE-360", "CTE-442", "EDUC-403", "CTE-334", "CTE-370", "CTE-408"]
    ordered = [c for c in priority if c in remaining]
    ordered += sorted(remaining - set(ordered))
    return ordered


def _get_credits_for_course(code: str) -> float:
    from advising_engine.rules import COURSE_MATRIX
    c = COURSE_MATRIX.get("courses", {}).get(code.upper().replace(" ", "-"), {})
    cred = c.get("credits", 3)
    if isinstance(cred, str) and "-" in cred:
        return float(cred.split("-")[0])
    return float(cred) if cred else 3


def _get_remaining_core_needs(core_status: Dict[str, Any]) -> set:
    needs = set()
    if not core_status.get("comsk_complete"):
        needs.add("ENGL-102")  # Often the missing one
    if not core_status.get("arns_has_lab_science"):
        needs.add("NSLAB")
    return needs


def is_future_term(term_label: str) -> bool:
    from datetime import datetime
    import re
    m = re.search(r"(Fall|Spring|Summer)\s+(\d{4})", term_label, re.I)
    if not m:
        return True
    year = int(m.group(2))
    now = datetime.now()
    return year > now.year or (year == now.year and "Fall" in m.group(1) and now.month < 9)
