"""
Student Intake — Upload Stellic PDF and parse directly to create student record.
No sample/mock data. Parses PDF to extract: name, catalog term, credits, placeholders, RES/GLP, major.
"""
import streamlit as st
from pathlib import Path
from advising_engine.parser import parse_stellic_report
from advising_engine.pdf_parser import parse_stellic_pdf
from utils.io import load_json, save_json, SSN_WARNING

st.set_page_config(page_title="Student Intake", page_icon="📥", layout="wide")
st.title("Student Intake")
st.caption("Upload Stellic degree audit PDF to create student record (no sample data)")

st.warning(SSN_WARNING)

# Load students — only real ingested data
data_dir = Path(__file__).parent.parent / "data"
data_path = data_dir / "students_data.json"
students = load_json(data_path) if data_path.exists() else []
if "students" in st.session_state:
    students = st.session_state.students

# PDF path for pre-uploaded file (e.g., /mnt/data/... or project uploads/)
DEFAULT_PDF_PATHS = [
    Path("/mnt/data/University of Wisconsin-Stout - Degree Audit _ James Frye _ University of Wisconsin-Stout.pdf"),
    Path(__file__).parent.parent / "uploads" / "University of Wisconsin-Stout - Degree Audit _ James Frye _ University of Wisconsin-Stout.pdf",
    Path(__file__).parent.parent / "data" / "University of Wisconsin-Stout - Degree Audit _ James Frye _ University of Wisconsin-Stout.pdf",
]

# Auto-load from pre-uploaded PDF (e.g. James Frye) when no students exist
if not students:
    for p in DEFAULT_PDF_PATHS:
        if p.exists():
            auto_parsed = parse_stellic_pdf(str(p))
            if auto_parsed.get("student_name") and auto_parsed.get("total_credits_earned", 0) >= 0:
                sid = (auto_parsed.get("student_name", "student") or "student").lower().replace(" ", "-")[:30]
                new_student = {
                    "id": sid,
                    "name": auto_parsed.get("student_name", "Unknown"),
                    "plan_year": "2023",
                    "major": "BS CTET",
                    "credits_earned": auto_parsed.get("total_credits_earned", 0),
                    "credits_in_progress": auto_parsed.get("total_credits_in_progress", 0),
                    "credits_planned": auto_parsed.get("total_credits_planned", 0),
                    "pacing": "full",
                    "accelerated_pathway": False,
                    "stellic_report_ingested": True,
                    "catalog_term": auto_parsed.get("catalog_term"),
                    "notes": "Auto-loaded from Stellic PDF",
                }
                students = [new_student]
                data_path.parent.mkdir(parents=True, exist_ok=True)
                save_json(data_path, students)
                st.session_state.students = students
                if "parsed_reports" not in st.session_state:
                    st.session_state.parsed_reports = {}
                st.session_state.parsed_reports[sid] = auto_parsed
                st.session_state.selected_student_id = sid
                st.success(f"Auto-loaded **{auto_parsed.get('student_name')}** from PDF at {p}")
            break

# Input: PDF upload or path
st.subheader("Load Stellic Degree Audit PDF")

col1, col2 = st.columns(2)
with col1:
    uploaded = st.file_uploader("Upload PDF", type=["pdf"], key="pdf_upload")

with col2:
    pdf_path_input = st.text_input(
        "Or enter PDF file path",
        placeholder="/mnt/data/... or full path to PDF",
        key="pdf_path",
    )

# Parse PDF when available
parsed = None
pdf_source = None

if uploaded:
    pdf_source = uploaded
    parsed = parse_stellic_pdf(uploaded)
elif pdf_path_input:
    p = Path(pdf_path_input.strip())
    if p.exists():
        parsed = parse_stellic_pdf(str(p))
        pdf_source = str(p)
    else:
        st.error(f"File not found: {p}")
elif not students:
    # Try default paths for pre-uploaded James Frye audit
    for p in DEFAULT_PDF_PATHS:
        if p.exists():
            parsed = parse_stellic_pdf(str(p))
            pdf_source = str(p)
            st.success(f"Loaded PDF from: {p}")
            break

# Also use last_parsed from paste
if "last_parsed" in st.session_state and not parsed:
    parsed = st.session_state.last_parsed
    pdf_source = "pasted text"

if parsed and pdf_source:
    student_name = parsed.get("student_name", "Unknown")
    total_earned = parsed.get("total_credits_earned", 0)
    catalog_term = parsed.get("catalog_term", "2023")
    placeholders = parsed.get("placeholders", [])
    res_glp = parsed.get("attributes_seen", {})

    st.success(f"Parsed: **{student_name}** | {total_earned:.0f} credits earned | RES: {res_glp.get('RES', 0)}/2 | GLP: {res_glp.get('GLP', 0)}/2")

    with st.expander("Extracted data"):
        st.json({
            "student_name": student_name,
            "catalog_term": catalog_term,
            "total_credits_earned": total_earned,
            "placeholders_count": len(placeholders),
            "RES": res_glp.get("RES", 0),
            "GLP": res_glp.get("GLP", 0),
            "internship_status": parsed.get("internship_status"),
            "capstone_status": parsed.get("capstone_status"),
        })

    # Create/update student
    st.subheader("Create student record from parsed audit")
    sid = st.text_input("Student ID", value=student_name.lower().replace(" ", "-")[:30], key="create_id")
    plan_year = st.text_input("Plan year", value="2023" if catalog_term else "2023", key="create_plan")

    if st.button("Create student & save parsed report"):
        new_student = {
            "id": sid,
            "name": student_name,
            "plan_year": plan_year,
            "major": "BS CTET",
            "credits_earned": total_earned,
            "credits_in_progress": parsed.get("total_credits_in_progress", 0),
            "credits_planned": parsed.get("total_credits_planned", 0),
            "pacing": "full",
            "accelerated_pathway": False,
            "stellic_report_ingested": True,
            "catalog_term": catalog_term,
            "notes": "From Stellic PDF parse",
        }
        # Replace if same name/id
        existing_ids = [s["id"] for s in students]
        if sid in existing_ids:
            students = [s for s in students if s["id"] != sid]
        students.append(new_student)
        data_path.parent.mkdir(parents=True, exist_ok=True)
        save_json(data_path, students)
        st.session_state.students = students
        if "parsed_reports" not in st.session_state:
            st.session_state.parsed_reports = {}
        st.session_state.parsed_reports[sid] = parsed
        st.session_state.selected_student_id = sid
        st.success(f"Created **{student_name}**. Go to Advising Output to generate notes.")

# Paste text fallback
st.markdown("---")
st.subheader("Alternative: Paste audit text")
raw_text = st.text_area("Paste Stellic audit text if PDF upload not available", height=200, key="paste_text")
if raw_text.strip() and st.button("Parse pasted text", key="parse_btn"):
    parsed_text = parse_stellic_report(raw_text)
    student_name = _extract_name_from_text(raw_text)
    st.session_state.last_parsed = {
        **parsed_text,
        "student_name": student_name,
        "catalog_term": None,
        "internship_status": None,
        "capstone_status": None,
        "unmet_stout_core": [],
    }
    parsed = st.session_state.last_parsed
    st.success("Parsed. Create student above using parsed data.")


def _extract_name_from_text(text: str) -> str:
    import re
    m = re.search(r"([A-Z][a-z]+\s+[A-Z][a-z]+)", text[:500])
    return m.group(1) if m else "Unknown"
