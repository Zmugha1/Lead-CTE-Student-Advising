"""
Advising Output — Notes, semester plan, substitutions/waivers, exports.
"""
import streamlit as st
from advising_engine.parser import parse_stellic_report
from advising_engine.rules import check_stout_core_status, get_double_count_candidates
from advising_engine.planner import build_semester_plan
from advising_engine.exceptions import build_exceptions_packet, format_exceptions_md
from utils.io import export_plan_csv, SSN_WARNING

st.set_page_config(page_title="Advising Output", page_icon="📋", layout="wide")
st.title("Advising Output")
st.caption("Generate advising notes, semester plan, and exceptions packet")

st.warning(SSN_WARNING)

students = st.session_state.get("students", [])
if not students:
    st.warning("No students. Go to Student Intake first.")
    st.stop()

options = {f"{s.get('name')} ({s.get('id')})": s for s in students}
sel_label = st.selectbox("Select student", list(options.keys()))
student = options.get(sel_label)
if not student:
    st.stop()

sid = student.get("id")
parsed = st.session_state.get("parsed_reports", {}).get(sid)

# Allow paste if no parsed report
if not parsed:
    st.info("No Stellic report on file. Paste audit text below to generate advising output.")
    raw = st.text_area("Paste Stellic audit text", height=150)
    if raw.strip():
        parsed = parse_stellic_report(raw)
        st.session_state.parsed_reports[sid] = parsed
        st.success("Report parsed.")
if not parsed:
    parsed = {
        "courses": [],
        "placeholders": [],
        "attributes_seen": {"RES": 0, "GLP": 0},
        "total_credits_earned": student.get("credits_earned", 0),
        "total_credits_in_progress": student.get("credits_in_progress", 0),
    }

if st.button("Generate Advising Output"):
    from advising_engine.parser import evaluate_placeholder_delay
    core_status = check_stout_core_status(parsed, student.get("plan_year", "2023"))
    plan_rows = build_semester_plan(parsed, student)
    
    # Placeholder delay flags
    total_cr = parsed.get("total_credits_earned", 0) + parsed.get("total_credits_in_progress", 0)
    placeholder_risks = []
    for ph in parsed.get("placeholders", []):
        r = evaluate_placeholder_delay(ph, total_cr)
        if r:
            placeholder_risks.append(r)
    
    # Build advising notes
    remaining = core_status.get("remaining_credits", 40)
    res_short = max(0, 2 - core_status.get("res_count", 0))
    glp_short = max(0, 2 - core_status.get("glp_count", 0))
    risk_items = list(core_status.get("risk_flags", [])) + placeholder_risks
    
    notes = f"""# Advising Notes — {student.get('name', 'Student')}

## Progress Summary
- Credits remaining (Stout Core): ~{remaining}
- RES: {core_status.get('res_count', 0)}/2 | GLP: {core_status.get('glp_count', 0)}/2
- ARNS: Math/Stat {'✓' if core_status.get('arns_has_math_stat') else '✗'} | Lab Science {'✓' if core_status.get('arns_has_lab_science') else '✗'}

## Next Term Recommendation
Based on pacing ({student.get('pacing', 'full')}), recommend 3–12 credits. See semester plan below.

## Risk Items
{chr(10).join('- ' + f for f in risk_items) if risk_items else '- None flagged'}

## Capstone Readiness
Ensure CTET core and instructional courses completed before CTE 408. Do not substitute capstone without program director approval.

## Accelerated Pathway
{'Declared — note shared MS CTE courses.' if student.get('accelerated_pathway') else 'Not declared.'}

## CPL Opportunity
Students with significant verified professional experience may consider Credit for Prior Learning for the Technical area.

## Strategic Plan Narrative

**Status snapshot:** {remaining} Stout Core credits remaining; biggest risks: {', '.join(risk_items[:3]) if risk_items else 'none'}.

**Planning goals:**
1. Reduce Stout Core risk early
2. Maximize double-counting (RES/GLP + category)
3. Keep credit load manageable
4. Align with CTET rotation schedule (matrix)

**PATH A — Fast-track Stout Core:** Prioritize high-impact summer courses (ENGL-102, NSLAB, RES/GLP options). See semester plan.

**PATH B — Lighter summer / heavier fall:** Spread core completion across Fall; focus on CTET major courses in Fall when rotation allows.

*Power Move:* When a single course satisfies 2+ high-risk requirements (e.g., GLP + NSLAB + ARNS), prioritize it.

## Next Steps
- Review semester plan and adjust per student preference
- Pull forward high-risk placeholders (ENGL-102, NSLAB, RES/GLP) when feasible
"""

    # Double-count suggestions
    need_res = res_short > 0
    need_glp = glp_short > 0
    unmet = []
    if core_status.get("sbsc_credits", 0) < 6:
        unmet.append("SBSC")
    if core_status.get("arhum_credits", 0) < 6:
        unmet.append("ARHUM")
    double = get_double_count_candidates(need_res, need_glp, unmet)
    if double:
        notes += "\n## Double-Count Options (RES/GLP + category)\n"
        for d in double:
            notes += f"- **{d['course']}** knocks out: {d['knocks_out']}\n"

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
    
    # Exceptions packet placeholder
    st.subheader("Substitutions / Waivers & Actions")
    plan_year = student.get("plan_year", "2023")
    use_stellic = str(plan_year).isdigit() and int(plan_year) >= 2023
    if use_stellic:
        st.info("Stellic: Select three dots next to requirement → Request Exception → Major or Stout Core → Substitution/Waiver. Use measured academic language.")
    else:
        st.info("Use BPLogix substitution/waiver form (pre-2023 plan).")
    
    # Export
    st.markdown("---")
    st.subheader("Export")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.download_button(
            "Download notes (.txt)",
            data=out["notes"],
            file_name=f"advising_notes_{sid}.txt",
            mime="text/plain",
        )
    with col2:
        csv_content = export_plan_csv(out["plan_rows"])
        st.download_button(
            "Download semester plan (.csv)",
            data=csv_content,
            file_name=f"semester_plan_{sid}.csv",
            mime="text/csv",
        )
    with col3:
        exc_packet = build_exceptions_packet(student, [])
        exc_packet["plan_year"] = plan_year
        exc_md = format_exceptions_md(exc_packet)
        st.download_button(
            "Download exceptions packet (.md)",
            data=exc_md,
            file_name=f"exceptions_packet_{sid}.md",
            mime="text/markdown",
        )
else:
    st.info("Click **Generate Advising Output** to create notes, plan, and exports.")
