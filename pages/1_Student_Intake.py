"""
Student Intake — Upload/paste Stellic report; create student record.
"""
import streamlit as st
from pathlib import Path
from advising_engine.parser import parse_stellic_report
from utils.io import load_json, save_json, SSN_WARNING

st.set_page_config(page_title="Student Intake", page_icon="📥", layout="wide")
st.title("Student Intake")
st.caption("Upload or paste Stellic audit report to create/update student records")

st.warning(SSN_WARNING)

# Load students
data_path = Path(__file__).parent.parent / "data" / "students_data.json"
if not data_path.exists():
    data_path = Path(__file__).parent.parent / "data" / "sample_students.json"
students = load_json(data_path)
if "students" in st.session_state:
    students = st.session_state.students

# Input method
method = st.radio("Input method", ["Paste text", "Upload PDF", "Manual entry"], horizontal=True)

if method == "Paste text":
    raw_text = st.text_area(
        "Paste Stellic audit text (extract from printable report if needed)",
        height=300,
        placeholder="Paste course list, requirements, grades, etc. Include placeholders like 'Placeholder: ENGL-102 PLANNED FOR SPRING '29' if present.",
    )
    if st.button("Parse Report"):
        if raw_text.strip():
            parsed = parse_stellic_report(raw_text)
            st.session_state.last_parsed = parsed
            st.success(f"Parsed {len(parsed.get('courses', []))} courses; "
                      f"{parsed.get('total_credits_earned', 0)} earned, "
                      f"{parsed.get('total_credits_in_progress', 0)} in progress.")
            st.json({
                "courses_count": len(parsed.get("courses", [])),
                "placeholders": len(parsed.get("placeholders", [])),
                "total_credits_earned": parsed.get("total_credits_earned", 0),
                "RES": parsed.get("attributes_seen", {}).get("RES", 0),
                "GLP": parsed.get("attributes_seen", {}).get("GLP", 0),
            })
        else:
            st.error("Please paste some text first.")

elif method == "Upload PDF":
    uploaded = st.file_uploader("Upload Stellic PDF report", type=["pdf"])
    if uploaded:
        st.info("PDF parsing is limited. For best results, copy text from PDF and use 'Paste text' option above.")
        # PDF extraction (pypdf or PyPDF2)
        try:
            try:
                from pypdf import PdfReader
            except ImportError:
                from PyPDF2 import PdfReader
            reader = PdfReader(uploaded)
            text_parts = []
            n = len(reader.pages) if hasattr(reader, "pages") else getattr(reader, "numPages", 10)
            for i in range(min(n, 10)):
                p = reader.pages[i] if hasattr(reader, "pages") else reader.getPage(i)
                t = getattr(p, "extract_text", None) or getattr(p, "extractText", None)
                text_parts.append(t() if t else "")
            raw_text = "\n".join(filter(None, text_parts))
            if raw_text:
                st.text_area("Extracted text (edit if needed)", value=raw_text, height=200, key="pdf_extracted")
        except ImportError:
            st.warning("Install pypdf for PDF extraction: pip install pypdf")
        except Exception as e:
            st.error(f"PDF extraction failed: {e}")

elif method == "Manual entry":
    st.subheader("Manual student record")
    with st.form("manual_student"):
        sid = st.text_input("Student ID", value="manual-001")
        name = st.text_input("Name", value="")
        plan_year = st.text_input("Plan year", value="2023")
        credits_earned = st.number_input("Credits earned", min_value=0.0, value=0.0)
        credits_in_progress = st.number_input("Credits in progress", min_value=0.0, value=0.0)
        pacing = st.selectbox("Pacing", ["full", "part"])
        accelerated = st.checkbox("Accelerated pathway declared", False)
        if st.form_submit_button("Add student"):
            new_student = {
                "id": sid,
                "name": name or "Unknown",
                "plan_year": plan_year,
                "major": "BS CTET",
                "credits_earned": credits_earned,
                "credits_in_progress": credits_in_progress,
                "credits_planned": 0,
                "pacing": pacing,
                "accelerated_pathway": accelerated,
                "stellic_report_ingested": False,
                "notes": "Manual entry",
            }
            students.append(new_student)
            save_path = Path(__file__).parent.parent / "data" / "students_data.json"
            save_json(save_path, students)
            st.session_state.students = students
            st.success(f"Added {name or sid}")

# Create student from parsed report
if "last_parsed" in st.session_state:
    parsed = st.session_state.last_parsed
    st.subheader("Create student from parsed report")
    with st.form("create_from_parsed"):
        cid = st.text_input("Student ID", value="student-" + str(len(students) + 1))
        cname = st.text_input("Name", value="")
        cplan = st.text_input("Plan year", value="2023")
        if st.form_submit_button("Create student & save parsed report"):
            new_student = {
                "id": cid,
                "name": cname or "Unknown",
                "plan_year": cplan,
                "major": "BS CTET",
                "credits_earned": parsed.get("total_credits_earned", 0),
                "credits_in_progress": parsed.get("total_credits_in_progress", 0),
                "credits_planned": parsed.get("total_credits_planned", 0),
                "pacing": "full",
                "accelerated_pathway": False,
                "stellic_report_ingested": True,
                "notes": "From Stellic paste",
            }
            students.append(new_student)
            save_path = Path(__file__).parent.parent / "data" / "students_data.json"
            save_json(save_path, students)
            st.session_state.students = students
            st.session_state.parsed_reports[cid] = parsed
            st.session_state.selected_student_id = cid
            st.success(f"Created {cname or cid}. Parsed report saved.")
