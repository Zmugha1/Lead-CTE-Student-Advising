"""
Student Dashboard — Progress, status visuals, risk flags.
"""
import streamlit as st
from advising_engine.rules import check_stout_core_status, STOUT_CORE_TOTAL, RES_REQUIRED, GLP_REQUIRED

st.set_page_config(page_title="Student Dashboard", page_icon="📊", layout="wide")
st.title("Student Dashboard")
st.caption("Status, progress, and risk flags by requirement area")

students = st.session_state.get("students", [])
if not students:
    st.warning("No students. Go to Student Intake to add students.")
    st.stop()

options = {f"{s.get('name') or 'Student'} ({s.get('id', '')})": s for s in students}
sel_label = st.selectbox("Select student", list(options.keys()))
student = options.get(sel_label)
if not student:
    st.stop()

sid = student.get("id")
st.session_state.selected_student_id = sid

# Get parsed report if available
parsed = st.session_state.get("parsed_reports", {}).get(sid)
if not parsed:
    # Build minimal parsed from student record
    parsed = {
        "courses": [],
        "placeholders": [],
        "attributes_seen": {"RES": 0, "GLP": 0},
        "total_credits_earned": student.get("credits_earned", 0),
        "total_credits_in_progress": student.get("credits_in_progress", 0),
        "total_credits_planned": student.get("credits_planned", 0),
    }

# Profile summary
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Credits Earned", parsed.get("total_credits_earned", 0))
with col2:
    st.metric("In Progress", parsed.get("total_credits_in_progress", 0))
with col3:
    st.metric("Plan Year", student.get("plan_year", "—"))
with col4:
    st.metric("Pacing", student.get("pacing", "full"))

st.markdown("---")

# Stout Core status
core_status = check_stout_core_status(parsed, student.get("plan_year", "2023"))

st.subheader("Stout Core Progress")
cols = st.columns(6)
cats = [
    ("COMSK", core_status.get("comsk_credits", 0), 9, core_status.get("comsk_complete")),
    ("ARNS", core_status.get("arns_credits", 0), 10, core_status.get("arns_complete")),
    ("ARHUM", core_status.get("arhum_credits", 0), 6, None),
    ("SBSC", core_status.get("sbsc_credits", 0), 6, None),
    ("SRER", core_status.get("srer_credits", 0), 3, None),
    ("RES/GLP", f"{core_status.get('res_count',0)}/{core_status.get('glp_count',0)}", f"{RES_REQUIRED}/{GLP_REQUIRED}", core_status.get("res_complete") and core_status.get("glp_complete")),
]
for i, (label, val, target, complete) in enumerate(cats):
    with cols[i]:
        if isinstance(val, (int, float)):
            pct = min(100, int(100 * val / target)) if target else 0
            st.progress(pct / 100)
            st.caption(f"{label}: {val}/{target}")
        else:
            st.caption(f"{label}: {val}")

st.markdown("---")
st.subheader("Remaining Credits by Category")
try:
    import pandas as pd
    remaining = [
        {"Category": "Stout Core", "Remaining": core_status.get("remaining_credits", STOUT_CORE_TOTAL)},
        {"Category": "RES courses", "Remaining": max(0, RES_REQUIRED - core_status.get("res_count", 0))},
        {"Category": "GLP courses", "Remaining": max(0, GLP_REQUIRED - core_status.get("glp_count", 0))},
    ]
    df = pd.DataFrame(remaining)
    st.bar_chart(df.set_index("Category"))
except Exception:
    st.write(f"Stout Core remaining: {core_status.get('remaining_credits', 0)} credits")

st.markdown("---")
st.subheader("Risk Flags")
risk_flags = core_status.get("risk_flags", [])
if not risk_flags:
    st.success("No major risk flags detected.")
else:
    for flag in risk_flags:
        st.error(flag)

# Accelerated pathway note
if student.get("accelerated_pathway"):
    st.info("**Accelerated pathway declared.** Shared courses (502/550/605/642) may apply; substitutions only if pathway officially declared.")
