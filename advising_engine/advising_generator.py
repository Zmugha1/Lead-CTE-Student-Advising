"""
Generate Program Lead-style advising output.
Structure: Progress Summary, Strategic Priorities, SUMMER PLAN, FALL PLAN,
Two Pathways, Risk Flags, Field Experience, Substitution Notes, Graduation Outlook.
"""
from typing import Any, Dict, List, Optional

from .rules import check_stout_core_status, get_double_count_candidates, get_course_availability
from .planner import build_semester_plan


# 2028-2029 placeholders that are risk flags (recommend pull forward)
RISK_PLACEHOLDER_TERMS = {"2028", "2029", "28", "29"}


def generate_advising_notes(
    parsed: Dict[str, Any],
    student: Dict[str, Any],
) -> str:
    """Generate full advising notes in Program Lead structure."""
    student_name = parsed.get("student_name") or student.get("name", "Student")
    plan_year = student.get("plan_year", "2023")
    credits_earned = parsed.get("total_credits_earned") or student.get("credits_earned", 0)
    placeholders = parsed.get("placeholders", [])
    attrs = parsed.get("attributes_seen", {})
    core_status = check_stout_core_status(parsed, plan_year)
    plan_rows = build_semester_plan(parsed, student)

    total_credits = credits_earned + parsed.get("total_credits_in_progress", 0)
    remaining_to_120 = max(0, 120 - total_credits)
    res_count = attrs.get("RES", core_status.get("res_count", 0))
    glp_count = attrs.get("GLP", core_status.get("glp_count", 0))
    res_short = max(0, 2 - res_count)
    glp_short = max(0, 2 - glp_count)

    # Risk flags: 2028-2029 placeholders
    risk_placeholders = []
    risk_flags = list(core_status.get("risk_flags", []))
    for ph in placeholders:
        yr = (getattr(ph, "planned_year", None) or (ph.get("planned_year") if isinstance(ph, dict) else None) or "").strip()
        if any(r in str(yr) for r in RISK_PLACEHOLDER_TERMS):
            code = getattr(ph, "course_code", None) or (ph.get("course_code", "") if isinstance(ph, dict) else "")
            term = getattr(ph, "planned_term", None) or (ph.get("planned_term", "") if isinstance(ph, dict) else "")
            risk_placeholders.append(
                f"{code} planned {term} '{yr}' — recommend pulling forward"
            )
    risk_flags.extend(risk_placeholders)

    # Remaining high-risk requirements
    high_risk = []
    if not core_status.get("comsk_complete", True):
        high_risk.append("COMSK (ENGL-102)")
    if not core_status.get("arns_has_lab_science"):
        high_risk.append("ARNS Natural Science with Lab")
    if not core_status.get("arns_has_math_stat"):
        high_risk.append("ARNS Math/Stat")
    if res_short > 0:
        high_risk.append(f"RES ({res_short} needed)")
    if glp_short > 0:
        high_risk.append(f"GLP ({glp_short} needed)")
    if core_status.get("srer_credits", 0) < 3:
        high_risk.append("SRER")
    high_risk = high_risk or ["None identified"]

    # Double-count candidates
    need_res = res_short > 0
    need_glp = glp_short > 0
    unmet_cats = []
    if core_status.get("sbsc_credits", 0) < 6:
        unmet_cats.append("SBSC")
    if core_status.get("arhum_credits", 0) < 6:
        unmet_cats.append("ARHUM")
    if core_status.get("srer_credits", 0) < 3:
        unmet_cats.append("SRER")
    double_options = get_double_count_candidates(need_res, need_glp, unmet_cats)

    # POWER MOVE: course that closes 2+ gaps
    power_moves = []
    for d in double_options:
        power_moves.append(f"**POWER MOVE:** {d['course']} — {d['knocks_out']}")

    # Build SUMMER and FALL plans from semester plan rows
    summer_plan = []
    fall_plan = []
    for row in plan_rows:
        term = row.get("Term", "")
        if "Summer" in term:
            summer_plan.append(row)
        elif "Fall" in term and "Summer" not in term:
            fall_plan.append(row)

    # Format output
    lines = [
        "--------------------------------------------------",
        f"ADVISING NOTES — {student_name}",
        "--------------------------------------------------",
        "",
        "## Progress Summary",
        f"- Credits earned: {credits_earned:.0f} / 120 minimum",
        f"- Remaining to graduation: ~{remaining_to_120:.0f} credits",
        f"- Remaining high-risk requirements: {', '.join(high_risk)}",
        f"- Major progression: See planned courses below",
        "",
        "## Strategic Priorities",
        "1) Reduce Stout Core risk early",
        "2) Maximize double-counting (RES/GLP + category)",
        "3) Maintain manageable load",
        "4) Align with CTET matrix",
        "",
    ]

    # SUMMER PLAN
    lines.append("## SUMMER PLAN (next logical term)")
    if summer_plan:
        for r in summer_plan[:2]:  # First 2 summer terms
            courses = r.get("Recommended Courses", "—")
            why = r.get("Why This Term", "")
            lines.append(f"- **Courses:** {courses}")
            lines.append(f"- **Why recommended:** {why}")
            lines.append(f"- **Requirement satisfied:** Per matrix availability")
            lines.append("")
    else:
        # Extract from plan_rows
        for row in plan_rows:
            if "Summer" in str(row.get("Term", "")):
                lines.append(f"- **Courses:** {row.get('Recommended Courses', '—')}")
                lines.append(f"- **Why recommended:** {row.get('Why This Term', '')}")
                break
        if not any("Summer" in str(r.get("Term", "")) for r in plan_rows):
            lines.append("- CTE 360 available Summer per matrix. Consider if needed for major.")
            lines.append("- Stout Core: RES/GLP course that also satisfies SBSC or ARHUM (double-count).")
        lines.append("")

    # FALL PLAN
    lines.append("## FALL PLAN")
    if fall_plan:
        for r in fall_plan[:2]:
            courses = r.get("Recommended Courses", "—")
            why = r.get("Why This Term", "")
            lines.append(f"- **Courses:** {courses}")
            lines.append(f"- **Why recommended:** {why}")
            lines.append(f"- **Double-count impact:** Maximize RES/GLP + category when applicable")
            lines.append("")
    else:
        for row in plan_rows:
            if "Fall" in str(row.get("Term", "")) and "Summer" not in str(row.get("Term", "")):
                lines.append(f"- **Courses:** {row.get('Recommended Courses', '—')}")
                lines.append(f"- **Why recommended:** {row.get('Why This Term', '')}")
                lines.append("- **Double-count impact:** Prioritize courses satisfying RES/GLP + ARHUM/SBSC/SRER")
                break
        lines.append("")

    # Two Strategic Pathways
    lines.append("## Two Strategic Pathways")
    lines.append("**PATH A – Fast Track Core Completion**")
    lines.append("- Higher-impact summer: ENGL-102 (if needed), Natural Science with Lab, RES/GLP option")
    lines.append("- Reduces risk before Fall; aligns with pull-forward recommendation for 2028-2029 placeholders")
    lines.append("")
    lines.append("**PATH B – Lighter Summer**")
    lines.append("- Spread Stout Core across Summer + Fall; focus CTET major courses in Fall when rotation allows")
    lines.append("- Lower summer load; may extend timeline slightly")
    lines.append("")

    # Power Moves
    if power_moves:
        lines.append("## POWER MOVE Recommendations")
        for pm in power_moves:
            lines.append(pm)
        lines.append("")

    # Risk Flags
    lines.append("## Risk Flags")
    for f in risk_flags:
        lines.append(f"- {f}")
    if not risk_flags:
        lines.append("- None identified")
    lines.append("")

    # Field Experience
    lines.append("## Field Experience Planning")
    internship = parsed.get("internship_status")
    capstone = parsed.get("capstone_status")
    if internship:
        lines.append(f"- Internship (TRHRD 389): {internship}")
    if capstone:
        lines.append(f"- Capstone (CTE 408): {capstone}")
    if not internship and not capstone:
        lines.append("- Ensure CTET core and instructional courses completed before capstone.")
        lines.append("- Do not substitute capstone without program director approval.")
    lines.append("")

    # Substitution/Waiver
    lines.append("## Substitution/Waiver Notes")
    if int(str(plan_year)) >= 2023 if str(plan_year).isdigit() else False:
        lines.append("- Stellic: Request Exception → Major or Stout Core Workflow. Use measured academic language.")
        lines.append("- Students can see justification; avoid informal language.")
    else:
        lines.append("- Use BPLogix substitution/waiver form (pre-2023 plan).")
    lines.append("")

    # Graduation Outlook
    lines.append("## Graduation Outlook")
    if remaining_to_120 <= 30:
        lines.append(f"- Within ~{remaining_to_120:.0f} credits of 120. Prioritize completion-risk items (ENGL-102, NSLAB, RES/GLP, SRER) before lower-risk placeholders.")
    else:
        lines.append(f"- ~{remaining_to_120:.0f} credits remaining. Follow semester plan; pull forward high-risk placeholders when feasible.")
    lines.append("")
    lines.append("--------------------------------------------------")

    return "\n".join(lines)
