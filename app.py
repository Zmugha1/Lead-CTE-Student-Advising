"""
UW-Stout BS CTET Student Management & Advising Dashboard
Local-first Streamlit app for Stellic audit ingestion and advising output generation.
"""
import streamlit as st

st.set_page_config(
    page_title="CTET Advising Dashboard",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize session state — use only real ingested data (no sample students)
if "students" not in st.session_state:
    from pathlib import Path
    from utils.io import load_json
    data_dir = Path(__file__).parent / "data"
    data_path = data_dir / "students_data.json"
    st.session_state.students = load_json(data_path) if data_path.exists() else []
if "selected_student_id" not in st.session_state:
    st.session_state.selected_student_id = None
if "parsed_reports" not in st.session_state:
    st.session_state.parsed_reports = {}
if "advising_output" not in st.session_state:
    st.session_state.advising_output = {}

st.markdown("# BS CTET Student Advising Dashboard")
st.caption("UW-Stout Career, Technical Education & Training — Lead CTE advising workflow")

# Privacy notice
st.warning(
    "**Privacy:** This app runs locally by default. Do not paste SSNs or other sensitive identifiers. "
    "Data is not sent externally unless you explicitly export or share it."
)

st.markdown("---")
st.markdown("### Navigation")
st.markdown("""
Use the sidebar to navigate:
- **Student Intake** — Upload or paste Stellic audit; create student record
- **Student Dashboard** — View progress, status, and risk flags
- **Advising Output** — Notes, semester plan, substitutions/waivers, exports
- **Admin Settings** — Edit course matrix, year logic, override availability
""")

# Quick student selector in main view
students = st.session_state.students
if students:
    options = [f"{s.get('name', 'Unknown')} ({s.get('id', '')})" for s in students]
    sel = st.selectbox("Quick select student", options=options, key="quick_sel")
    if sel:
        idx = options.index(sel)
        st.session_state.selected_student_id = students[idx].get("id")
        st.info(f"Selected: **{students[idx].get('name')}** — Plan Year {students[idx].get('plan_year')}")
else:
    st.info("No students loaded. Go to **Student Intake** to add students or paste a Stellic report.")

st.markdown("---")
st.markdown("*Assumptions: Course availability follows the matrix. CTE 360/560: Fall in AY 2026-2027; Spring in AY 2027-2028+.*")
