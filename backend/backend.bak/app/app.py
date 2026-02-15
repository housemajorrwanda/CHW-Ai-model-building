import streamlit as st

from math_grader import MathGrader, Step
from ocr_pipeline import OCRProcessor


st.set_page_config(page_title="Math Step Grader", layout="wide")
st.title("Step-by-Step Math Grader")

st.markdown(
    "Enter gold steps with optional point and required flags using `expression | points | required`."
    " Leave the extra fields empty to use defaults. Student steps only need the expression per line."
)

DEFAULT_GOLD = """x^2 - 5x + 6 = 0 | 1 | y
(x - 2)(x - 3) = 0 | 1 | y
x - 2 = 0 or x - 3 = 0 | 1 | y
x = 2 or x = 3 | 2 | y"""

DEFAULT_STUDENT = """x^2 - 5x + 6 = 0
(x - 2)(x - 3) = 0
x = 2 or x = 3"""


OCR_PSM_OPTIONS = {
    "Sparse text (psm 11)": 11,
    "Single column (psm 4)": 4,
    "Block of text (psm 6)": 6,
    "Single line (psm 7)": 7,
}


@st.cache_resource
def get_ocr_processor(language: str, psm: int, dpi: int, use_easyocr: bool = True):
    return OCRProcessor(language=language, psm=psm, dpi=dpi, use_easyocr=use_easyocr)


st.session_state.setdefault("gold_steps_input", DEFAULT_GOLD)
st.session_state.setdefault("student_steps_input", DEFAULT_STUDENT)

with st.sidebar:
    st.header("OCR Settings")
    
    # Check if EasyOCR is available
    try:
        import easyocr
        easyocr_available = True
    except ImportError:
        easyocr_available = False
        st.warning("⚠️ EasyOCR not installed. Install with: `pip install easyocr`")
    
    use_easyocr = st.checkbox(
        "Use EasyOCR (better for handwriting)", 
        value=easyocr_available,
        disabled=not easyocr_available
    )
    
    if not easyocr_available and use_easyocr:
        st.info("💡 Installing EasyOCR will improve OCR accuracy for handwriting and rotated images.")
    
    ocr_language = st.text_input("OCR language", value="en")
    psm_choice = st.selectbox(
        "Page segmentation mode (Tesseract only)",
        list(OCR_PSM_OPTIONS.keys()),
        index=2,
    )
    ocr_psm = OCR_PSM_OPTIONS[psm_choice]
    ocr_dpi = st.slider("Render DPI (PDFs)", min_value=200, max_value=500, value=300, step=50)
    show_processed_preview = st.checkbox("Show processed OCR image", value=False)


st.subheader("Upload Student Work (optional)")
uploaded_file = st.file_uploader(
    "Upload PDF or image (JPG, PNG) of student work", type=["pdf", "png", "jpg", "jpeg"]
)

if uploaded_file:
    st.caption(
        f"Loaded {uploaded_file.name} ({uploaded_file.size / 1024:.1f} KB). "
        "Press the button below to extract steps."
    )

    def run_ocr():
        with st.spinner("Running OCR to extract steps..."):
            try:
                ocr_result_local = get_ocr_processor(ocr_language, ocr_psm, ocr_dpi, use_easyocr).extract_steps_from_file(
                    uploaded_file.getvalue(), uploaded_file.name
                )
            except Exception as exc:
                st.session_state["ocr_last_error"] = str(exc)
                return

        if ocr_result_local.steps:
            st.session_state["student_steps_input"] = "\n".join(ocr_result_local.steps)
            st.session_state["ocr_last_text"] = ocr_result_local.combined_text
            st.session_state["ocr_last_summary"] = (
                len(ocr_result_local.steps),
                ocr_result_local.page_count,
            )
        else:
            st.session_state["ocr_last_text"] = ocr_result_local.combined_text
            st.session_state["ocr_last_summary"] = (0, ocr_result_local.page_count)
        previews = getattr(ocr_result_local, "processed_previews", [])
        st.session_state["ocr_last_previews"] = previews

    st.button("Extract steps from uploaded document", on_click=run_ocr)

    if "ocr_last_error" in st.session_state:
        st.error(f"OCR failed: {st.session_state.pop('ocr_last_error')}")
    elif "ocr_last_summary" in st.session_state:
        steps_count, page_count = st.session_state["ocr_last_summary"]
        if steps_count:
            st.success(f"Extracted {steps_count} step(s) from {page_count} page(s).")
        else:
            st.warning("No steps detected. Consider adjusting the scan or typing steps manually.")

        if st.session_state.get("ocr_last_text"):
            with st.expander("Recognized text"):
                st.text(st.session_state["ocr_last_text"] or "(No text recognized)")
        if show_processed_preview:
            previews = st.session_state.get("ocr_last_previews") or []
            if previews:
                st.caption("Preview of the processed image fed into Tesseract")
                for idx, preview_bytes in enumerate(previews, start=1):
                    st.image(
                        preview_bytes,
                        caption=f"Processed page {idx}",
                        use_container_width=True,
                    )


gold_input = st.text_area("Gold steps", height=200, key="gold_steps_input")
student_input = st.text_area("Student steps", height=200, key="student_steps_input")


def parse_gold_steps(raw: str):
    steps = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        parts = [p.strip() for p in line.split("|")]
        content = parts[0]
        points = float(parts[1]) if len(parts) > 1 and parts[1] else 1.0
        required = True
        if len(parts) > 2 and parts[2]:
            required = parts[2].lower() not in {"n", "no", "false", "0"}
        steps.append(Step(content, points=points, required=required))
    return steps


def parse_student_steps(raw: str):
    return [line.strip() for line in raw.splitlines() if line.strip()]


if st.button("Grade"):
    try:
        gold_steps = parse_gold_steps(gold_input)
    except ValueError:
        st.error("Please ensure points are numeric values.")
        gold_steps = []

    student_steps = parse_student_steps(student_input)

    if not gold_steps:
        st.warning("Add at least one gold step.")
    elif not student_steps:
        st.warning("Add at least one student step.")
    else:
        grader = MathGrader(gold_steps)
        results = grader.grade(student_steps)

        st.subheader("Overall Score")
        st.metric(
            "Score",
            f"{results['total_score']:.2f} / {results['max_score']:.2f}",
            f"{results['percentage']:.1f}%"
        )

        st.subheader("Step Evaluations")
        table_rows = []
        for idx, (student_step, evaluation) in enumerate(
            zip(student_steps, results["evaluations"]), start=1
        ):
            table_rows.append(
                {
                    "Step #": idx,
                    "Student Step": student_step,
                    "Status": evaluation.status.value,
                    "Points": f"{evaluation.points_earned:.2f}",
                    "Feedback": evaluation.feedback,
                }
            )
        st.table(table_rows)

