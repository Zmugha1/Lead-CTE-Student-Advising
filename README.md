# Lead CTE Student Advising Dashboard

UW-Stout B.S. Career, Technical Education & Training (BS CTET) **Student Management & Advising Dashboard** — a Streamlit app for ingesting Stellic audit reports and generating advising notes, semester plans, and substitution/waiver guidance.

## Features

- **Student Intake**: Paste Stellic audit text or upload PDF; create/update student records
- **Student Dashboard**: Progress by Stout Core category, RES/GLP status, risk flags
- **Advising Output**: Notes, semester-by-semester plan, substitutions/waivers packet, exports
- **Admin Settings**: Edit course matrix, CTE 360/560 year-based rules

## CTE 360/560 Rotation (Implemented)

| Academic Year | Fall | Spring | Summer |
|---------------|------|--------|--------|
| 2026-2027     | ✓    | —      | ✓      |
| 2027-2028+    | —    | ✓      | ✓      |

## Setup

```bash
cd Lead-CTE-Student-Advising
pip install -r requirements.txt
streamlit run app.py
```

## Usage

1. **Student Intake**: Paste Stellic audit text (from printable report) or upload PDF. Create student record.
2. **Student Dashboard**: Select student; view progress and risk flags.
3. **Advising Output**: Generate notes, semester plan, and export as .txt, .csv, .md.
4. **Admin**: Adjust `data/course_matrix.yaml` for course availability overrides.

## Privacy & Security

- **Local by default**: Data is not sent externally unless you explicitly export.
- **Do not paste SSNs** or other sensitive identifiers.
- Student data lives in `data/students_data.json` (local).

## Assumptions

- Course availability follows `data/course_matrix.yaml`
- Stout Core rules from `data/stout_core_rules.yaml`
- Substitutions/waivers: Stellic for 2023+ plan; BPLogix form for pre-2023
- Capstone (CTE 408): No substitution without program director approval

## Project Structure

```
Lead-CTE-Student-Advising/
├── app.py                 # Main entry
├── pages/
│   ├── 1_Student_Intake.py
│   ├── 2_Student_Dashboard.py
│   ├── 3_Advising_Output.py
│   └── 4_Admin_Settings.py
├── advising_engine/
│   ├── parser.py          # Stellic report parsing
│   ├── rules.py           # Stout Core + CTET rules
│   ├── planner.py         # Semester planning
│   └── exceptions.py      # Substitution/waiver packets
├── data/
│   ├── course_matrix.yaml # CTE 360/560 year logic
│   ├── stout_core_rules.yaml
│   └── sample_students.json
└── utils/
    ├── io.py
    └── term.py
```

## Push to GitHub

```bash
cd Lead-CTE-Student-Advising
git init
git add .
git commit -m "Initial CTET advising dashboard"
git remote add origin https://github.com/Zmugha1/Lead-CTE-Student-Advising.git
git branch -M main
git push -u origin main
```
