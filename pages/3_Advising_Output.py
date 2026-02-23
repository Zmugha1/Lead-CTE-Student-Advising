"""
Advising Output — Program Lead-style notes, semester plan, exports.
Uses real parsed data only. No sample/mock data.
"""
import streamlit as st
from advising_engine.parser import parse_stellic_report, evaluate_placeholder_delay
from advising_engine.pdf_parser import parse_stellic_pdf
from advising_engine.rules import check_stout_core_status, get_double_count_candidates
from advising_engine.planner import build_semester_plan
from advising_engine.advising_generator import generate_advising_notes
from advising_engine.exceptions import build_exceptions_packet, format_exceptions_md
from utils.io import export_plan_csv, SSN_WARNING

st.set_page_config(page_title="Advising Output", page_icon="📋", layout="wide")
st.title("Advising Output")
st.caption("Generate advising notes from Stellic audit (Program Lead format)")

st.warning(SSN_WARNING)

students = st.session_state.get("students", [])
if not students:
    st.warning("No students in the system. Go to **Student Intake** to upload a Stellic PDF first.")
    st.stop()

options = {f"{s.get('name')} ({s.get('id')})": s for s in students}
sel_label = st.selectbox("Select student", list(options.keys()))
student = options.get(sel_label)
if not student:
    st.stop()

sid = student.get("id")
parsed = st.session_state.get("parsed_reports", {}).get(sid)

# PDF path fallback for James Frye
PDF_PATHS = [
    "/mnt/data/University of Wisconsin-Stout - Degree Audit _ James Frye _ University of Wisconsin-Stout.pdf",
    str(st.session_state.get("_project_root", "")) + "/uploads/University of Wisconsin-Stout - Degree Audit _ James Frye _ University of Wisconsin-Stout.pdf",
]
if not parsed and student.get("name", "").lower().find("frye") >= 0:
    from pathlib import Path
    for p in [
        Path("/mnt/data/University of Wisconsin-Stout - Degree Audit _ James Frye _ University of Wisconsin-Stout.pdf"),
        Path(__file__).parent.parent / "uploads" / "University of Wisconsin-Stout - Degree Audit _ James Frye _ University of Wisconsin-Stout.pdf",
        Path(__file__).parent.parent / "data" / "University of Wisconsin-Stout - Degree Audit _ James Frye _ University of Wisconsin-Stout.pdf",
    ]:
        if p.exists():
            parsed = parse_stellic_pdf(str(p))
            st.session_state.parsed_reports[sid] = parsed
            st.info("Loaded James Frye audit from PDF.")
            break

# Paste or upload if no parsed report
if not parsed:
    st.info("No Stellic report on file. Upload PDF or paste audit text below.")
    uploaded = st.file_uploader("Upload PDF", type=["pdf"], key="adv_pdf")
    if uploaded:
        parsed = parse_stellic_pdf(uploaded)
        st.session_state.parsed_reports[sid] = parsed
        st.success("PDF parsed.")
    else:
        raw = st.text_area("Paste audit text", height=150, key="adv_paste")
        if raw.strip():
            pt = parse_stellic_report(raw)
            parsed = {
                **pt,
                "student_name": student.get("name", "Unknown"),
                "catalog_term": None,
                "internship_status": None,
                "capstone_status": None,
                "unmet_stout_core": [],
            }
            st.session_state.parsed_reports[sid] = parsed
            st.success("Parsed from text.")

if not parsed:
    parsed = {
        "courses": [],
        "placeholders": [],
        "attributes_seen": {"RES": 0, "GLP": 0},
        "student_name": student.get("name", "Unknown"),
        "total_credits_earned": student.get("credits_earned", 0),
        "total_credits_in_progress": student.get("credits_in_progress", 0),
    }

# Generate advising output
if st.button("Generate Advising Output"):
    core_status = check_stout_core_status(parsed, student.get("plan_year", "2023"))
    plan_rows = build_semester_plan(parsed, student)
    notes = generate_advising_notes(parsed, student)

    st.session_state.advising_output[sid] = {
        "notes": notes,
        "plan_rows": plan_rows,
        "core_status": core_status,
    }

# Display output
out = st.session_state.get("advising_output", {}).get(sid)
if out:
    st.subheader("Advising Notes")
    st.markdown(out["notes"])
    
    st.subheader("Semester Plan")
    st.dataframe(out["plan_rows"], use_container_width=True)
    
    st.subheader("Substitutions / Waivers")
    plan_year = student.get("plan_year", "2023")
    use_stellic = str(plan_year).isdigit() and int(plan_year) >= 2023
    if use_stellic:
        st.info("Stellic: Request Exception → Major or Stout Core. Use measured academic language.")
    else:
        st.info("Use BPLogix substitution/waiver form (pre-2023 plan).")
    
    st.markdown("---")
    st.subheader("Export")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.download_button("Download notes (.txt)", data=out["notes"], file_name=f"advising_notes_{sid}.txt", mime="text/plain")
    with col2:
        st.download_button("Download semester plan (.csv)", data=export_plan_csv(out["plan_rows"]), file_name=f"semester_plan_{sid}.csv", mime="text/csv")
    with col3:
        exc_packet = build_exceptions_packet(student, [])
        exc_packet["plan_year"] = plan_year
        st.download_button("Download exceptions packet (.md)", data=format_exceptions_md(exc_packet), file_name=f"exceptions_packet_{sid}.md", mime="text/markdown")
else:
    st.info("Click **Generate Advising Output** to create notes, plan, and exports.")
