"""
File I/O utilities: uploads, exports, student data persistence.
"""
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

# Privacy notice — do not paste SSNs
SSN_WARNING = "Do not paste SSNs or other sensitive identifiers into this app."


def load_json(path: Path) -> List[Dict[str, Any]]:
    """Load JSON array from file."""
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else [data]


def save_json(path: Path, data: List[Dict[str, Any]]) -> None:
    """Save JSON array to file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def ensure_student_dir(base: Path, student_id: str) -> Path:
    """Ensure student data directory exists."""
    d = base / "students" / student_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def export_notes_txt(content: str, filename: str = "advising_notes.txt") -> str:
    """Return content as UTF-8 string for download."""
    return content


def export_notes_md(content: str, filename: str = "advising_notes.md") -> str:
    """Return markdown content for download."""
    return content


def export_plan_csv(rows: List[Dict[str, str]]) -> str:
    """Convert semester plan rows to CSV string."""
    if not rows:
        return "Term,Recommended Courses,Credits,Why This Term,Notes\n"
    import csv
    import io
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=rows[0].keys() if rows else [])
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue()


def export_exceptions_md(sections: List[Dict[str, Any]]) -> str:
    """Build exceptions packet as markdown."""
    lines = ["# Substitutions / Waivers Packet", ""]
    for s in sections:
        if "heading" in s:
            lines.append(f"## {s['heading']}")
            lines.append("")
        if "items" in s:
            for item in s["items"]:
                lines.append(f"- **{item.get('requirement', '')}**: {item.get('text', '')}")
        if "text" in s:
            lines.append(s["text"])
        lines.append("")
    return "\n".join(lines)
