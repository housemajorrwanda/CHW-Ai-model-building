#!/usr/bin/env python3
import streamlit as st
import sys
import os
from pathlib import Path
import pandas as pd

import ssl
import urllib3
ssl._create_default_https_context = ssl._create_unverified_context
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    import certifi
    cert_path = certifi.where()
    os.environ['SSL_CERT_FILE'] = cert_path
    os.environ['REQUESTS_CA_BUNDLE'] = cert_path
    os.environ['CURL_CA_BUNDLE'] = cert_path
except ImportError:
    pass

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from grading import (
    Step, StepStatus, MatchingEngine, ScoringEngine,
    FeedbackGenerator, GoldSolutionManager
)
from ocr.math_ocr_processor import MathOCR
from ocr.latex_converter import LaTeXConverter
from ocr.step_parser import StepParser

st.set_page_config(
    page_title="Math Grading System",
    page_icon="📐",
    layout="wide"
)

st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .step-box {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 5px;
        margin: 0.5rem 0;
    }
    .correct { color: #28a745; }
    .partial { color: #ffc107; }
    .incorrect { color: #dc3545; }
</style>
""", unsafe_allow_html=True)

if 'gold_solution' not in st.session_state:
    st.session_state.gold_solution = []
if 'student_steps' not in st.session_state:
    st.session_state.student_steps = []
if 'grading_results' not in st.session_state:
    st.session_state.grading_results = None

@st.cache_resource
def get_managers():
    return {
        'gold_manager': GoldSolutionManager(),
        'matching_engine': MatchingEngine(),
        'scoring_engine': ScoringEngine(),
        'feedback_generator': FeedbackGenerator()
    }

@st.cache_resource
def load_math_ocr(_cache_version="v2"):
    try:
        return MathOCR()
    except Exception as e:
        error_msg = str(e)
        if "SSL" in error_msg or "CERTIFICATE" in error_msg.upper():
            st.warning("⚠️ SSL Certificate Issue - Using workaround")
            st.info("💡 **Tip:** You can use the 'Type Manually' option to enter student answers directly without OCR.")
        else:
            st.warning(f"Math OCR not available: {error_msg}")
        return None

managers = get_managers()

st.markdown('<h1 class="main-header">📐 Step-by-Step Math Grading System</h1>', unsafe_allow_html=True)
st.markdown("---")

with st.sidebar:
    st.header("📚 Navigation")
    mode = st.radio("Select Mode:", [
        "Create Gold Solution",
        "Grade Student Exam",
        "Manage Solutions"
    ])
    
    st.markdown("---")
    st.header("ℹ️ About")
    st.markdown("""
    This system grades math problems based on:
    - **Step-by-step process**
    - **Mathematical equivalence**
    - **Required step dependencies**
    - **Partial credit**
    """)

if mode == "Create Gold Solution":
    st.header("📝 Create Gold Solution (Answer Key)")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        solution_name = st.text_input(
            "Solution Name",
            placeholder="e.g., midterm_problem_1",
            help="Unique name for this gold solution"
        )
    
    with col2:
        exam_name = st.text_input("Exam Name (optional)", placeholder="e.g., Midterm Exam")
    
    st.markdown("### Steps:")
    
    # Add step form
    with st.expander("➕ Add New Step", expanded=True):
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            step_text = st.text_input("Step Expression/Text", key="new_step_text")
        with col2:
            step_points = st.number_input("Points", min_value=1, value=5, key="new_step_points")
        with col3:
            step_required = st.checkbox("Required?", value=False, key="new_step_required")
        
        if st.button("Add Step"):
            if step_text:
                new_step = Step(
                    text=step_text,
                    points=step_points,
                    required=step_required,
                    step_number=len(st.session_state.gold_solution) + 1
                )
                st.session_state.gold_solution.append(new_step)
                st.success(f"Added step {new_step.step_number}")
                st.rerun()
    
    # Display current steps
    if st.session_state.gold_solution:
        st.markdown("### Current Steps:")
        
        for i, step in enumerate(st.session_state.gold_solution):
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            
            with col1:
                st.markdown(f"**Step {step.step_number}:** {step.text}")
            with col2:
                st.markdown(f"{step.points} pts")
            with col3:
                st.markdown("✓ Required" if step.required else "")
            with col4:
                if st.button("🗑️", key=f"delete_{i}"):
                    st.session_state.gold_solution.pop(i)
                    # Renumber steps
                    for j, s in enumerate(st.session_state.gold_solution, 1):
                        s.step_number = j
                    st.rerun()
        
        total_points = sum(step.points for step in st.session_state.gold_solution)
        st.info(f"**Total Points:** {total_points}")
        
        # Save solution
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("💾 Save Gold Solution", type="primary", use_container_width=True):
                if solution_name:
                    try:
                        metadata = {'exam': exam_name} if exam_name else {}
                        filepath = managers['gold_manager'].save_solution(
                            solution_name,
                            st.session_state.gold_solution,
                            metadata
                        )
                        st.success(f"✅ Saved: {filepath}")
                    except Exception as e:
                        st.error(f"Error saving: {e}")
                else:
                    st.error("Please enter a solution name")
        
        with col2:
            if st.button("🗑️ Clear All Steps", use_container_width=True):
                st.session_state.gold_solution = []
                st.rerun()
    else:
        st.info("👆 Add steps above to create your gold solution")
        
        # Load example
        if st.button("📚 Load Example Solution"):
            try:
                managers['gold_manager'].create_example_solution()
                steps, metadata = managers['gold_manager'].load_solution("example_quadratic")
                st.session_state.gold_solution = steps
                st.success("Loaded example solution!")
                st.rerun()
            except Exception as e:
                st.error(f"Error loading example: {e}")

elif mode == "Grade Student Exam":
    st.header("📊 Grade Student Submission")
    
    # Step 1: Select gold solution
    st.subheader("Step 1: Select Gold Solution")
    
    solutions = managers['gold_manager'].list_solutions()
    
    if not solutions:
        st.warning("⚠️ No gold solutions found. Create one first!")
    else:
        solution_options = {s['name']: s['filename'] for s in solutions}
        selected_solution = st.selectbox(
            "Gold Solution",
            options=list(solution_options.keys()),
            format_func=lambda x: f"{x} ({[s for s in solutions if s['name']==x][0]['total_points']} pts)"
        )
        
        if selected_solution:
            try:
                gold_steps, metadata = managers['gold_manager'].load_solution(
                    solution_options[selected_solution]
                )
                
                # Display gold solution
                with st.expander("👁️ View Gold Solution"):
                    for step in gold_steps:
                        st.markdown(f"**Step {step.step_number}:** {step.text} ({step.points} pts) {'🔒 Required' if step.required else ''}")
                
                st.markdown("---")
                
                # Step 2: Get student submission
                st.subheader("Step 2: Student Submission")
                
                uploaded_file = st.file_uploader(
                    "📤 Upload Student Exam Image",
                    type=['jpg', 'jpeg', 'png'],
                    help="Upload a photo of the student's handwritten exam"
                )
                
                student_steps = []
                ocr_result = None
                
                if uploaded_file:
                    # Display uploaded image
                    from PIL import Image
                    image = Image.open(uploaded_file)
                    st.image(image, caption="Uploaded Exam Image", use_container_width=True)
                    
                    if st.button("🔍 Extract & Process with OCR", type="primary", use_container_width=True):
                        # Clear cache to ensure we get latest version
                        load_math_ocr.clear()
                        math_ocr = load_math_ocr()
                        if math_ocr:
                            with st.spinner("🔄 Processing image with Math OCR..."):
                                # Save temp file
                                temp_path = "temp_student_exam.jpg"
                                with open(temp_path, 'wb') as f:
                                    f.write(uploaded_file.getvalue())
                                
                                try:
                                    # Process with automatic LaTeX conversion and step parsing
                                    ocr_result = math_ocr.process_image(
                                        temp_path,
                                        return_latex=True,
                                        convert_latex=True,
                                        parse_steps=True
                                    )
                                    
                                    # Handle different return types
                                    if isinstance(ocr_result, dict):
                                        # Got structured result
                                        student_steps = ocr_result.get('steps', [])
                                        original_latex = ocr_result.get('original_latex', '')
                                        converted_math = ocr_result.get('converted_math', '')
                                        
                                        # Display processing info
                                        col1, col2 = st.columns(2)
                                        with col1:
                                            st.success(f"✅ Extracted {len(student_steps)} step(s)")
                                        with col2:
                                            st.info(f"📊 Step count: {len(student_steps)}")
                                        
                                        # Show original LaTeX if different
                                        if original_latex and original_latex != converted_math:
                                            with st.expander("🔍 View Processing Details"):
                                                st.markdown("**Original LaTeX:**")
                                                st.code(original_latex, language='latex')
                                                st.markdown("**Converted to Math:**")
                                                st.code(converted_math)
                                        
                                    elif isinstance(ocr_result, list):
                                        # Got list of steps
                                        student_steps = ocr_result
                                        st.success(f"✅ Extracted {len(student_steps)} step(s)")
                                    
                                    else:
                                        # Got single string - parse it
                                        parser = StepParser()
                                        converter = LaTeXConverter()
                                        
                                        # Convert LaTeX if needed
                                        if converter.is_latex(str(ocr_result)):
                                            converted = converter.convert(str(ocr_result))
                                        else:
                                            converted = str(ocr_result)
                                        
                                        # Parse into steps
                                        student_steps = parser.parse(converted)
                                        st.success(f"✅ Extracted {len(student_steps)} step(s)")
                                    
                                    # Store in session state
                                    st.session_state.student_steps = student_steps
                                    
                                except Exception as e:
                                    st.error(f"❌ OCR Processing failed: {str(e)}")
                                    st.info("💡 Try improving image quality or check if image contains math content")
                                
                                finally:
                                    # Clean up
                                    if os.path.exists(temp_path):
                                        os.remove(temp_path)
                        else:
                            st.error("⚠️ Math OCR not available. Please check SSL certificates or network connection.")
                            st.info("💡 You can still manually type student answers below")
                
                # Display extracted steps
                if st.session_state.get('student_steps'):
                    student_steps = st.session_state.student_steps
                
                if student_steps:
                    st.markdown("### 📝 Extracted Steps (Auto-processed):")
                    
                    # Display steps in a nice format
                    for i, step in enumerate(student_steps, 1):
                        col1, col2 = st.columns([10, 1])
                        with col1:
                            st.markdown(f"**Step {i}:** `{step}`")
                        with col2:
                            if st.button("✏️", key=f"edit_{i}", help="Edit this step"):
                                # TODO: Add edit functionality
                                pass
                    
                    # Allow manual editing if needed
                    with st.expander("✏️ Edit Steps (if needed)"):
                        edited_text = st.text_area(
                            "Edit steps (one per line)",
                            value='\n'.join(student_steps),
                            height=150,
                            help="Modify steps if OCR made mistakes"
                        )
                        if st.button("Update Steps"):
                            parser = StepParser()
                            student_steps = parser.parse(edited_text)
                            st.session_state.student_steps = student_steps
                            st.success("Steps updated!")
                            st.rerun()
                else:
                    st.info("👆 Upload an exam image and click 'Extract & Process with OCR' to begin")
                
                # Use extracted steps or parse from text
                if not student_steps and 'student_steps' in st.session_state:
                    student_steps = st.session_state.student_steps
                
                # Grade button
                if student_steps:
                    st.info(f"📝 Ready to grade {len(student_steps)} student step(s)")
                    
                    if st.button("🚀 Grade Submission", type="primary", use_container_width=True):
                        with st.spinner("Grading..."):
                            # Grade the submission
                            graded_steps, summary = managers['scoring_engine'].grade_submission(
                                student_steps,
                                gold_steps
                            )
                            
                            st.session_state.grading_results = {
                                'graded_steps': graded_steps,
                                'summary': summary,
                                'gold_steps': gold_steps
                            }
                        
                        st.success("✅ Grading Complete!")
                        st.rerun()
                
                # Display results
                if st.session_state.grading_results:
                    st.markdown("---")
                    st.subheader("📊 Grading Results")
                    
                    results = st.session_state.grading_results
                    summary = results['summary']
                    
                    # Score display
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Total Score", f"{summary['total_points_earned']}/{summary['total_points_possible']}")
                    with col2:
                        st.metric("Percentage", f"{summary['percentage']:.1f}%")
                    with col3:
                        st.metric("✓ Correct", summary['correct_steps'])
                    with col4:
                        st.metric("✗ Incorrect", summary['incorrect_steps'])
                    
                    # Detailed breakdown
                    st.markdown("### Step-by-Step Breakdown")
                    
                    for i, graded_step in enumerate(results['graded_steps'], 1):
                        status_class = ""
                        if graded_step.status == StepStatus.CORRECT:
                            status_class = "correct"
                            status_icon = "✓"
                        elif graded_step.status == StepStatus.PARTIALLY_CORRECT:
                            status_class = "partial"
                            status_icon = "~"
                        else:
                            status_class = "incorrect"
                            status_icon = "✗"
                        
                        with st.container():
                            col1, col2 = st.columns([3, 1])
                            with col1:
                                st.markdown(f"**Step {i}:** {graded_step.student_text}")
                                if graded_step.matched_gold_step:
                                    st.caption(f"Expected: {graded_step.matched_gold_step.text}")
                                st.caption(graded_step.feedback)
                            with col2:
                                st.markdown(f'<p class="{status_class}">{status_icon} {graded_step.points_earned:.1f}/{graded_step.points_possible} pts</p>', unsafe_allow_html=True)
                            
                            st.markdown("---")
                    
                    # Feedback
                    with st.expander("📋 Detailed Feedback"):
                        feedback = managers['feedback_generator'].generate_feedback(
                            results['graded_steps'],
                            results['summary'],
                            results['gold_steps']
                        )
                        st.text(feedback)
                    
                    # Export
                    if st.button("💾 Export Results", use_container_width=True):
                        # Create export data
                        export_data = {
                            'summary': summary,
                            'steps': [step.to_dict() for step in results['graded_steps']]
                        }
                        
                        import json
                        json_str = json.dumps(export_data, indent=2)
                        st.download_button(
                            "Download JSON",
                            json_str,
                            "grading_results.json",
                            "application/json"
                        )
                
            except Exception as e:
                st.error(f"Error: {e}")

elif mode == "Manage Solutions":
    st.header("📚 Manage Gold Solutions")
    
    solutions = managers['gold_manager'].list_solutions()
    
    if not solutions:
        st.info("No gold solutions found. Create one first!")
    else:
        st.subheader(f"Found {len(solutions)} solution(s)")
        
        for solution in solutions:
            with st.expander(f"📄 {solution['name']}"):
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.markdown(f"**File:** {solution['filename']}")
                    st.markdown(f"**Total Points:** {solution['total_points']}")
                    st.markdown(f"**Steps:** {solution['step_count']}")
                
                with col2:
                    if st.button("👁️ View", key=f"view_{solution['filename']}"):
                        try:
                            steps, metadata = managers['gold_manager'].load_solution(solution['filename'])
                            st.session_state.gold_solution = steps
                            st.success("Loaded! Go to 'Create Gold Solution' to view/edit")
                        except Exception as e:
                            st.error(f"Error: {e}")
                
                with col3:
                    if st.button("🗑️ Delete", key=f"delete_{solution['filename']}"):
                        if managers['gold_manager'].delete_solution(solution['filename']):
                            st.success("Deleted!")
                            st.rerun()
                        else:
                            st.error("Failed to delete")

# Footer
st.markdown("---")
st.markdown(
    '<div style="text-align: center; color: #666;">'
    'Math Grading System | Powered by SymPy & TrOCR'
    '</div>',
    unsafe_allow_html=True
)

