"""
Admin Settings — Edit matrix rules, year logic, override course availability.
"""
import streamlit as st
from pathlib import Path
import yaml

st.set_page_config(page_title="Admin Settings", page_icon="⚙️", layout="wide")
st.title("Admin Settings")
st.caption("Edit course matrix, year logic, and override availability")

data_dir = Path(__file__).parent.parent / "data"
course_matrix_path = data_dir / "course_matrix.yaml"

if not course_matrix_path.exists():
    st.error("course_matrix.yaml not found.")
    st.stop()

with open(course_matrix_path, "r", encoding="utf-8") as f:
    current_yaml = f.read()

st.subheader("Course Matrix (course_matrix.yaml)")
st.caption("CTE 360/560: AY 2026-2027 Fall+Summer; AY 2027-2028+ Spring+Summer")

edited = st.text_area("Edit YAML", value=current_yaml, height=400)
if st.button("Save changes"):
    try:
        yaml.safe_load(edited)
        with open(course_matrix_path, "w", encoding="utf-8") as f:
            f.write(edited)
        st.success("Saved.")
    except yaml.YAMLError as e:
        st.error(f"Invalid YAML: {e}")

st.markdown("---")
st.subheader("CTE 360/560 Year-Based Rule (Reference)")
st.markdown("""
| Academic Year | Fall | Spring | Summer |
|---------------|------|--------|--------|
| 2026-2027     | ✓    | —      | ✓      |
| 2027-2028+    | —    | ✓      | ✓      |
""")
st.caption("Ensure academic_year_logic in YAML matches this table.")
