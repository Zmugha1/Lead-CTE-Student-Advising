"""
Parse Stellic degree audit PDF to extract structured data.
Extracts: student name, catalog term, credits, placeholders, RES/GLP, major, internship/capstone.
"""
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .parser import (
    ParsedCourse,
    ParsedPlaceholder,
    parse_stellic_report,
    normalize_course_code,
)


def extract_text_from_pdf(source: Union[str, Path, Any]) -> str:
    """Extract text from PDF file path or file-like object."""
    try:
        try:
            from pypdf import PdfReader
        except ImportError:
            from PyPDF2 import PdfReader

        if hasattr(source, "read"):
            reader = PdfReader(source)
        else:
            path = Path(source)
            if not path.exists():
                return ""
            reader = PdfReader(str(path))

        text_parts = []
        n = len(reader.pages) if hasattr(reader, "pages") else getattr(reader, "numPages", 0)
        for i in range(n):
            p = reader.pages[i] if hasattr(reader, "pages") else reader.getPage(i)
            t = getattr(p, "extract_text", None) or getattr(p, "extractText", None)
            text_parts.append(t() if t else "")
        return "\n".join(filter(None, text_parts))
    except Exception:
        return ""


def parse_stellic_pdf(source: Union[str, Path, Any]) -> Dict[str, Any]:
    """
    Parse Stellic degree audit PDF.
    Returns structured data including:
    - student_name, catalog_term, total_credits_earned
    - placeholders (with planned term/year)
    - attributes_seen (RES, GLP)
    - major_courses, internship_status, capstone_status
    """
    raw_text = extract_text_from_pdf(source)
    name_from_path = None
    if hasattr(source, "name"):
        name_from_path = _extract_name_from_filename(str(source.name))
    elif isinstance(source, (str, Path)):
        name_from_path = _extract_name_from_filename(Path(source).name)
    if not raw_text.strip():
        return {
            "student_name": name_from_path or "Unknown",
            "catalog_term": None,
            "total_credits_earned": 0.0,
            "courses": [],
            "placeholders": [],
            "attributes_seen": {"RES": 0, "GLP": 0},
            "total_credits_earned": 0,
            "total_credits_in_progress": 0,
            "total_credits_planned": 0,
            "major_courses_planned": [],
            "internship_status": None,
            "capstone_status": None,
            "unmet_stout_core": [],
            "raw_text": "",
        }

    parsed = parse_stellic_report(raw_text)

    # Extract student name (common patterns: "Degree Audit | Name" or "Name - University of Wisconsin-Stout")
    name = _extract_student_name(raw_text) or name_from_path or "Unknown"
    catalog_term = _extract_catalog_term(raw_text)
    total_earned = _extract_total_credits_earned(raw_text, parsed)

    # Enhanced placeholder detection for Stellic format
    placeholders = _extract_placeholders(raw_text, parsed.get("placeholders", []))

    # RES / GLP from text
    res_glp = _extract_res_glp(raw_text, parsed)

    # Major and field experience
    major_planned = _extract_major_planned(raw_text)
    internship_status = _extract_internship_status(raw_text)
    capstone_status = _extract_capstone_status(raw_text)

    # Unmet Stout Core categories
    unmet_core = _extract_unmet_stout_core(raw_text, placeholders)

    return {
        "student_name": name,
        "catalog_term": catalog_term,
        "total_credits_earned": total_earned or parsed.get("total_credits_earned", 0),
        "total_credits_in_progress": parsed.get("total_credits_in_progress", 0),
        "total_credits_planned": parsed.get("total_credits_planned", 0),
        "courses": parsed.get("courses", []),
        "placeholders": placeholders,
        "attributes_seen": res_glp,
        "major_courses_planned": major_planned,
        "internship_status": internship_status,
        "capstone_status": capstone_status,
        "unmet_stout_core": unmet_core,
        "raw_text": raw_text[:5000],
    }


def _extract_name_from_filename(filename: str) -> Optional[str]:
    """Extract 'First Last' from filename like '... _ James Frye _ ...'."""
    m = re.search(r"_\s*([A-Z][a-z]+\s+[A-Z][a-z]+)\s*_", filename)
    return m.group(1).strip() if m else None


def _extract_student_name(text: str) -> str:
    """Extract student name from audit header."""
    # "Degree Audit | James Frye" or "James Frye - University of Wisconsin-Stout"
    m = re.search(r"Degree\s+Audit\s*[|_]\s*([A-Za-z\s\-\.]+?)(?:\s*[|_\n]|\s+University)", text, re.I)
    if m:
        return m.group(1).strip()
    m = re.search(r"(?:for|student)\s*:\s*([A-Za-z\s\-\.]+?)(?:\n|$)", text, re.I)
    if m:
        return m.group(1).strip()
    m = re.search(r"University of Wisconsin-Stout\s*[-–|]\s*Degree Audit\s*[-–|_]\s*([A-Za-z\s\-\.]+?)(?:\s*[-–|_]|$)", text, re.I)
    if m:
        return m.group(1).strip()
    # Fallback: look for "FirstName LastName" before "University"
    m = re.search(r"([A-Z][a-z]+\s+[A-Z][a-z]+)\s+University of Wisconsin-Stout", text)
    if m:
        return m.group(1).strip()
    return "Unknown"


def _extract_catalog_term(text: str) -> Optional[str]:
    """Extract catalog term (e.g., Fall 2024)."""
    m = re.search(r"Catalog\s+Term\s*[:=]?\s*(\w+\s+\d{4})", text, re.I)
    if m:
        return m.group(1).strip()
    m = re.search(r"Catalog\s*:\s*(\w+\s+\d{4})", text, re.I)
    if m:
        return m.group(1).strip()
    return None


def _extract_total_credits_earned(text: str, parsed: Dict) -> Optional[float]:
    """Extract total credits earned from audit."""
    m = re.search(r"Total\s+Credits\s+Earned\s*[:=]?\s*(\d+(?:\.\d+)?)", text, re.I)
    if m:
        return float(m.group(1))
    m = re.search(r"Credits\s+Earned\s*[:=]?\s*(\d+(?:\.\d+)?)", text, re.I)
    if m:
        return float(m.group(1))
    return parsed.get("total_credits_earned")


def _extract_placeholders(raw_text: str, existing: List) -> List[ParsedPlaceholder]:
    """Extract placeholders with term/year, including Stout Core categories."""
    placeholders = list(existing) if existing else []
    seen = {(p.course_code or "", p.planned_term or "", p.planned_year or ""): 1 for p in placeholders}

    # Patterns for Stellic placeholders: "Placeholder: ENGL-102 ... Spring '29" or "PLANNED FOR SPRING 2029"
    patterns = [
        re.compile(r"Placeholder\s*:\s*([A-Z\-]+\d+[A-Z]?)\s+[^\n]*(?:PLANNED\s+FOR\s+)?(Fall|Spring|Summer|Winterm)\s*['\"]?(\d{2,4})['\"]?", re.I),
        re.compile(r"([A-Z\-]+\d+[A-Z]?)\s+[^\n]*(?:planned|planned for)\s+(Fall|Spring|Summer|Winterm)\s*['\"]?(\d{2,4})['\"]?", re.I),
        re.compile(r"Natural\s+Science\s+(?:with\s+)?Lab\s+[^\n]*(Fall|Spring|Summer)\s*['\"]?(\d{2,4})['\"]?", re.I),
        re.compile(r"SRER\s+[^\n]*(Fall|Spring|Summer)\s*['\"]?(\d{2,4})['\"]?", re.I),
        re.compile(r"(ARHU|SBSC|ARHUM)\s+[^\n]*(Fall|Spring|Summer)\s*['\"]?(\d{2,4})['\"]?", re.I),
    ]

    for pat in patterns:
        for m in pat.finditer(raw_text):
            code = None
            term = None
            year = None
            if pat == patterns[0] or pat == patterns[1]:
                code = normalize_course_code(m.group(1))
                term = m.group(2)
                year = m.group(3) if len(m.groups()) >= 3 else None
            elif pat == patterns[2]:
                code = "NSLAB"
                term = m.group(1)
                year = m.group(2)
            elif pat == patterns[3]:
                code = "SRER"
                term = m.group(1)
                year = m.group(2)
            elif pat == patterns[4]:
                code = m.group(1)
                term = m.group(2)
                year = m.group(3) if len(m.groups()) >= 3 else None

            if code and (code, term, year) not in seen:
                placeholders.append(ParsedPlaceholder(course_code=code, planned_term=term, planned_year=year))
                seen[(code, term, year)] = 1

    return placeholders


def _extract_res_glp(text: str, parsed: Dict) -> Dict[str, int]:
    """Extract RES and GLP counts from audit."""
    from .parser import _count_attributes
    attrs = parsed.get("attributes_seen", {})
    res = attrs.get("RES", 0)
    glp = attrs.get("GLP", 0)
    # Look for "RES: X of 2" type patterns
    m = re.search(r"RES\s*[:=]?\s*(\d+)\s*(?:of\s*2)?", text, re.I)
    if m:
        res = max(res, int(m.group(1)))
    m = re.search(r"GLP\s*[:=]?\s*(\d+)\s*(?:of\s*2)?", text, re.I)
    if m:
        glp = max(glp, int(m.group(1)))
    return {"RES": res, "GLP": glp}


def _extract_major_planned(text: str) -> List[str]:
    """Extract major/CTET planned courses."""
    # Look for CTE-xxx, EDUC-xxx in planned sections
    pat = re.compile(r"(CTE[- ]?\d{3}|EDUC[- ]?\d{3}|TRHRD[- ]?\d{3})\s+(?:planned|planned for|Fall|Spring|Summer)?\s*(\d{4})?", re.I)
    found = []
    for m in pat.finditer(text):
        code = normalize_course_code(m.group(1))
        if code not in found:
            found.append(code)
    return found


def _extract_internship_status(text: str) -> Optional[str]:
    """Extract internship (TRHRD 389) status."""
    if re.search(r"TRHRD\s*389|Internship", text, re.I):
        if re.search(r"completed|satisfied|done", text, re.I):
            return "Completed"
        if re.search(r"planned|in progress", text, re.I):
            return "Planned/In Progress"
        return "Required"
    return None


def _extract_capstone_status(text: str) -> Optional[str]:
    """Extract capstone (CTE 408) status."""
    if re.search(r"CTE\s*408|Capstone", text, re.I):
        if re.search(r"completed|satisfied|done", text, re.I):
            return "Completed"
        if re.search(r"planned|in progress", text, re.I):
            return "Planned/In Progress"
        return "Required"
    return None


def _extract_unmet_stout_core(text: str, placeholders: List) -> List[str]:
    """Identify unmet Stout Core categories from placeholders and text."""
    unmet = []
    ph_codes = {p.course_code for p in placeholders}
    if "ENGL-102" in ph_codes or re.search(r"ENGL\s*102|ENGL-102", text):
        if re.search(r"placeholder|unmet|not satisfied", text, re.I):
            unmet.append("ENGL-102 (COMSK)")
    if "NSLAB" in ph_codes or re.search(r"Natural\s+Science.*Lab|NSLAB", text, re.I):
        if re.search(r"placeholder|unmet|not satisfied", text, re.I):
            unmet.append("Natural Science with Lab (ARNS)")
    if "SRER" in ph_codes or re.search(r"SRER|Sustainability", text, re.I):
        if re.search(r"placeholder|unmet|not satisfied", text, re.I):
            unmet.append("SRER")
    return unmet
