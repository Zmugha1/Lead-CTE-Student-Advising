"""
Build substitution/waiver packets with justification text.
Stellic 2023+ vs BPLogix for pre-2023.
"""
from typing import Any, Dict, List


def build_exceptions_packet(
    student: Dict[str, Any],
    proposed: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Build packet for substitutions/waivers.
    proposed: list of {requirement, exception_type, substitute_course, workflow, justification}
    """
    plan_year = student.get("plan_year", "2023")
    try:
        year_int = int(plan_year)
        use_stellic = year_int >= 2023
    except (ValueError, TypeError):
        use_stellic = True

    routing = (
        "Stellic: Select three dots next to requirement → Request an Exception → "
        "Major or Stout Core Workflow → Substitution/Waiver → pick substitute and paste justification. "
        "Students can see the justification; use measured academic language."
        if use_stellic
        else "Use BPLogix substitution/waiver form (Stellic exception not available for pre-2023 plan)."
    )

    items = []
    for p in proposed:
        items.append({
            "requirement": p.get("requirement", ""),
            "exception_type": p.get("exception_type", "Substitution"),
            "substitute_course": p.get("substitute_course", ""),
            "workflow": p.get("workflow", "Major or Stout Core"),
            "justification": p.get("justification", ""),
            "routing_note": routing,
        })

    return {
        "use_stellic": use_stellic,
        "routing_note": routing,
        "items": items,
    }


def format_exceptions_md(packet: Dict[str, Any]) -> str:
    """Format exceptions packet as markdown for export."""
    lines = ["# Substitutions / Waivers Packet", ""]
    lines.append(f"**Plan Year:** {packet.get('plan_year', 'N/A')}")
    lines.append(f"**Workflow:** {packet.get('routing_note', '')}")
    lines.append("")
    for item in packet.get("items", []):
        lines.append(f"## {item.get('requirement', '')}")
        lines.append(f"- **Type:** {item.get('exception_type', '')}")
        lines.append(f"- **Substitute:** {item.get('substitute_course', '')}")
        lines.append(f"- **Workflow:** {item.get('workflow', '')}")
        lines.append(f"- **Justification (no line breaks):** {item.get('justification', '')}")
        lines.append("")
    return "\n".join(lines)
