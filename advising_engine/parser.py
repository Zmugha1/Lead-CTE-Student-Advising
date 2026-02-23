"""
Extract structured data from Stellic audit report text.
Uses regex + heuristics to handle messy text.
"""
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


def extract_student_info_from_pdf(pdf_source: Union[str, Path, Any]) -> Dict[str, Any]:
    """
    Extract student name and ID from Stellic degree audit PDF.
    Returns: {name, student_id, raw_text}
    """
    try:
        try:
            from pypdf import PdfReader
        except ImportError:
            from PyPDF2 import PdfReader

        if hasattr(pdf_source, "read"):
            reader = PdfReader(pdf_source)
            filename = getattr(pdf_source, "name", "") or ""
        else:
            path = Path(pdf_source)
            reader = PdfReader(str(path))
            filename = path.name

        text = ""
        n = len(reader.pages) if hasattr(reader, "pages") else getattr(reader, "numPages", 0)
        for i in range(n):
            page = reader.pages[i] if hasattr(reader, "pages") else reader.getPage(i)
            t = getattr(page, "extract_text", None) or getattr(page, "extractText", None)
            text += (t() if t else "") or ""

        # Extract name from text (appears at top of audit)
        name_match = re.search(r"([A-Z][a-z]+\s+[A-Z][a-z]+)", text[:2000])
        name = name_match.group(1).strip() if name_match else None

        # Fallback: extract from filename (e.g., "... _ James Frye _ ...")
        if not name and filename:
            m = re.search(r"_\s*([A-Z][a-z]+\s+[A-Z][a-z]+)\s*_", filename)
            name = m.group(1).strip() if m else None

        # Extract student ID (8-digit)
        id_match = re.search(r"\b\d{8}\b", text)
        student_id = id_match.group(0) if id_match else None

        return {
            "name": name or "Unknown Student",
            "student_id": student_id,
            "raw_text": text,
        }
    except Exception:
        return {"name": "Unknown Student", "student_id": None, "raw_text": ""}


@dataclass
class ParsedCourse:
    """Single course from audit."""
    code: str
    credits: float
    term: Optional[str] = None
    grade: Optional[str] = None
    status: str = "taken"  # taken, in_progress, planned
    category: Optional[str] = None
    attributes: List[str] = field(default_factory=list)  # RES, GLP, etc.
    does_not_count: bool = False


@dataclass
class ParsedPlaceholder:
    """Placeholder for unmet requirement (e.g., ENGL-102 PLANNED FOR SPRING '29)."""
    course_code: str
    planned_term: Optional[str] = None
    planned_year: Optional[str] = None
    category: Optional[str] = None


def normalize_course_code(raw: str) -> str:
    """Normalize course code to hyphen form (e.g., ENGL 101 -> ENGL-101)."""
    s = re.sub(r"\s+", "-", raw.strip().upper())
    return s


def parse_credits(text: str) -> Optional[float]:
    """Extract credits from text like '3.00' or '3 cr'."""
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:cr|credits?)?", text, re.I)
    return float(m.group(1)) if m else None


def parse_stellic_report(raw_text: str) -> Dict[str, Any]:
    """
    Parse Stellic audit text into structured data.
    Returns: {
        courses: [ParsedCourse],
        placeholders: [ParsedPlaceholder],
        unmet_requirements: [...],
        attributes_seen: {RES: n, GLP: n},
        total_credits_earned: float,
        total_credits_in_progress: float,
        total_credits_planned: float,
    }
    """
    courses: List[ParsedCourse] = []
    placeholders: List[ParsedPlaceholder] = []
    unmet: List[str] = []
    total_earned = 0.0
    total_in_progress = 0.0
    total_planned = 0.0

    # Course pattern: CODE credits [term] [grade] [status]
    # Common formats: "ENGL 101 3.00 Fall 2024 A"
    # "CTE 302 2.00 In Progress"
    # "Placeholder: ENGL-102 ... PLANNED FOR SPRING '29"
    course_pat = re.compile(
        r"(?:^|\n)\s*([A-Z]{2,5}[\s\-]\d{2,3}[A-Z]?)\s+(\d+(?:\.\d+)?)\s*(?:cr|credits?)?\s*"
        r"(?:(Fall|Spring|Summer|Winterm)\s+(\d{2,4}))?\s*"
        r"(In Progress|Planned|IP|Completed)?",
        re.I | re.MULTILINE,
    )

    # Placeholder pattern
    placeholder_pat = re.compile(
        r"Placeholder:\s*([A-Z\-]+\d+[A-Z]?)\s*[^\n]*"
        r"(?:PLANNED\s+FOR\s+(Fall|Spring|Summer|Winterm)\s+['\"]?(\d{2,4}))?",
        re.I,
    )

    # RES / GLP
    res_glp_pat = re.compile(r"\b(RES|GLP)\b", re.I)

    lines = raw_text.split("\n")
    for line in lines:
        # Placeholder
        pm = placeholder_pat.search(line)
        if pm:
            code = normalize_course_code(pm.group(1))
            term = pm.group(2)
            year = pm.group(3)
            placeholders.append(
                ParsedPlaceholder(course_code=code, planned_term=term, planned_year=year)
            )
            continue

        # Regular course
        cm = course_pat.search(line)
        if cm:
            code = normalize_course_code(cm.group(1))
            cred = parse_credits(cm.group(2) or "0")
            term = cm.group(3)
            year = cm.group(4)
            status_str = (cm.group(5) or "").lower()
            does_not = "does not count" in line.lower() or "do not count" in line.lower()
            attrs = res_glp_pat.findall(line)
            attrs = [a.upper() for a in attrs]

            if "in progress" in status_str or "ip" in status_str:
                status = "in_progress"
                total_in_progress += cred or 0
            elif "planned" in status_str:
                status = "planned"
                total_planned += cred or 0
            else:
                status = "taken"
                total_earned += cred or 0

            courses.append(
                ParsedCourse(
                    code=code,
                    credits=cred or 0,
                    term=f"{term} {year}" if term and year else None,
                    status=status,
                    attributes=attrs,
                    does_not_count=does_not,
                )
            )

    # Fallback: simple course patterns (CODE + digits)
    simple_pat = re.compile(
        r"\b([A-Z]{2,5})\s*[-]?\s*(\d{2,3}[A-Z]?)\s+(\d+(?:\.\d+)?)\s*",
        re.I,
    )
    seen_codes = {c.code for c in courses}
    for m in simple_pat.finditer(raw_text):
        code = f"{m.group(1).upper()}-{m.group(2).upper()}"
        if code not in seen_codes:
            cred = float(m.group(3))
            courses.append(ParsedCourse(code=code, credits=cred, status="taken"))
            total_earned += cred
            seen_codes.add(code)

    return {
        "courses": courses,
        "placeholders": placeholders,
        "unmet_requirements": unmet,
        "attributes_seen": _count_attributes(courses),
        "total_credits_earned": total_earned,
        "total_credits_in_progress": total_in_progress,
        "total_credits_planned": total_planned,
        "raw_snippet": raw_text[:2000] if raw_text else "",
    }


def _count_attributes(courses: List[ParsedCourse]) -> Dict[str, int]:
    res, glp = 0, 0
    for c in courses:
        for a in c.attributes:
            if a.upper() == "RES":
                res += 1
            elif a.upper() == "GLP":
                glp += 1
    return {"RES": res, "GLP": glp}


def evaluate_placeholder_delay(
    placeholder: ParsedPlaceholder, total_credits: float
) -> Optional[str]:
    """
    If student is near graduation (e.g., 113 credits) but placeholder is far out
    (e.g., Spring '29), return a risk message.
    """
    if not placeholder.planned_year or total_credits < 90:
        return None
    try:
        yr = int(placeholder.planned_year)
        if yr >= 2000 and yr < 100:
            yr += 2000
        elif yr < 100:
            yr += 2000
        if total_credits >= 105 and yr >= 2029:
            return f"Placeholder {placeholder.course_code} planned for {placeholder.planned_term} {placeholder.planned_year} may be unreasonably delayed given credits ({total_credits}). Consider pulling forward."
    except (ValueError, TypeError):
        pass
    return None
