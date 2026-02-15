#!/usr/bin/env python3
"""
Script to create test courses and exams from the grading dataset
"""
import pandas as pd
import requests
import json
import sys
from pathlib import Path

# Configuration
API_BASE_URL = "http://localhost:8000/api"
PROFESSOR_EMAIL = "professor@university.edu"
PROFESSOR_PASSWORD = "password"

# Level mapping: dataset level -> API level
LEVEL_MAPPING = {
    "O-Level": "beginner",
    "S1": "beginner",
    "S2": "intermediate",
    "S3": "intermediate",
    "S4": "advanced",
    "S5": "advanced",
    "S6": "advanced"
}

# Course configurations
COURSE_CONFIGS = [
    {"subject": "Biology", "level": "O-Level", "api_level": "beginner", "code": "BIO-O", "name": "Biology O-Level"},
    {"subject": "Biology", "level": "S1", "api_level": "beginner", "code": "BIO-S1", "name": "Biology S1"},
    {"subject": "Biology", "level": "S2", "api_level": "intermediate", "code": "BIO-S2", "name": "Biology S2"},
    {"subject": "Chemistry", "level": "O-Level", "api_level": "beginner", "code": "CHEM-O", "name": "Chemistry O-Level"},
    {"subject": "Chemistry", "level": "S1", "api_level": "beginner", "code": "CHEM-S1", "name": "Chemistry S1"},
    {"subject": "Chemistry", "level": "S2", "api_level": "intermediate", "code": "CHEM-S2", "name": "Chemistry S2"},
    {"subject": "Maths", "level": "O-Level", "api_level": "beginner", "code": "MATH-O", "name": "Mathematics O-Level"},
    {"subject": "Maths", "level": "S1", "api_level": "beginner", "code": "MATH-S1", "name": "Mathematics S1"},
    {"subject": "Maths", "level": "S2", "api_level": "intermediate", "code": "MATH-S2", "name": "Mathematics S2"},
    {"subject": "Physics", "level": "O-Level", "api_level": "beginner", "code": "PHY-O", "name": "Physics O-Level"},
    {"subject": "Physics", "level": "S1", "api_level": "beginner", "code": "PHY-S1", "name": "Physics S1"},
    {"subject": "Physics", "level": "S2", "api_level": "intermediate", "code": "PHY-S2", "name": "Physics S2"},
]

EXAM_TYPES = [
    {"name": "Midterm Exam", "duration": 90},
    {"name": "Final Exam", "duration": 120},
    {"name": "Quiz", "duration": 45},
]

def login():
    """Login and get auth token"""
    response = requests.post(
        f"{API_BASE_URL}/auth/login",
        json={
            "email": PROFESSOR_EMAIL,
            "password": PROFESSOR_PASSWORD,
            "role": "professor"
        }
    )
    if response.status_code != 200:
        print(f"Login failed: {response.text}")
        sys.exit(1)
    return response.json()["access_token"]

def create_course(token, config):
    """Create a course"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(
        f"{API_BASE_URL}/courses",
        json={
            "name": config["name"],
            "code": config["code"],
            "description": f"Comprehensive {config['subject']} course for {config['level']} level students",
            "level": config["api_level"],
            "topics": []
        },
        headers=headers
    )
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to create course {config['code']}: {response.text}")
        return None

def create_question_from_row(row, question_num):
    """Convert dataset row to exam question format"""
    import math
    
    question_text = str(row.get('question', '')).strip()
    answer_text = str(row.get('answer', '')).strip()
    
    # Handle marks - convert to int, default to 10 if NaN or invalid
    try:
        marks_raw = row.get('marks', 10)
        if pd.isna(marks_raw):
            marks = 10
        else:
            marks = max(1, int(float(marks_raw)))  # Ensure at least 1 point
    except (ValueError, TypeError):
        marks = 10
    
    difficulty = row.get('estimated_difficulty', 'Medium')
    
    # Determine question type
    q_type = row.get('question_type', 'standard')
    if q_type in ['true_false', 'recall', 'explanation']:
        question_type = 'standard'
    elif q_type == 'matching':
        question_type = 'matching'
    else:
        question_type = 'standard'
    
    # Create gold solution steps
    gold_steps = []
    if answer_text and answer_text not in ['', 'nan', 'None']:
        # Split answer into steps if it's complex
        if len(answer_text) > 100:
            parts = [p.strip() for p in answer_text.split('. ') if p.strip()]
            num_parts = min(len(parts), 3)  # Max 3 steps
            if num_parts > 0:
                points_per_step = max(1, marks // num_parts)  # Integer division
                remainder = marks % num_parts
                
                for idx, part in enumerate(parts[:num_parts], 1):
                    step_points = points_per_step + (1 if idx <= remainder else 0)
                    gold_steps.append({
                        "stepNumber": idx,
                        "description": part[:500],  # Limit length
                        "expression": "",
                        "latex": "",
                        "points": step_points,
                        "required": True
                    })
        else:
            gold_steps.append({
                "stepNumber": 1,
                "description": answer_text[:500],
                "expression": "",
                "latex": "",
                "points": marks,
                "required": True
            })
    
    if not gold_steps:
        gold_steps.append({
            "stepNumber": 1,
            "description": "Provide a complete answer",
            "expression": "",
            "latex": "",
            "points": marks,
            "required": True
        })
    
    return {
        "number": question_num,
        "text": question_text[:1000] if question_text else "Question text",  # Limit length
        "richContent": None,
        "questionType": question_type,
        "points": marks,
        "subQuestions": [],
        "attachments": [],
        "embeddedContent": [],
        "theories": [],
        "goldSolutionSteps": gold_steps,
        "finalAnswer": answer_text[:200] if answer_text and answer_text != 'nan' else "",
        "finalAnswerLatex": "",
        "outlineLevel": 1,
        "parentQuestionId": None
    }

def create_exam(token, course_id, exam_config, questions_data, exam_num):
    """Create an exam with questions"""
    headers = {"Authorization": f"Bearer {token}"}
    
    # Select questions for this exam (mix of difficulties)
    exam_questions = []
    total_points = 0
    
    # Get questions of different difficulties
    easy_q = questions_data[questions_data['estimated_difficulty'] == 'Easy'].head(3)
    medium_q = questions_data[questions_data['estimated_difficulty'] == 'Medium'].head(4)
    hard_q = questions_data[questions_data['estimated_difficulty'] == 'Hard'].head(3)
    
    selected_questions = pd.concat([easy_q, medium_q, hard_q]).head(10)
    
    for idx, (_, row) in enumerate(selected_questions.iterrows(), 1):
        question = create_question_from_row(row, idx)
        exam_questions.append(question)
        total_points += question["points"]
    
    exam_data = {
        "title": f"{exam_config['name']} - {exam_num}",
        "description": f"Comprehensive {exam_config['name'].lower()} covering key topics",
        "courseId": course_id,
        "duration": exam_config["duration"],
        "questions": exam_questions
    }
    
    response = requests.post(
        f"{API_BASE_URL}/exams",
        json=exam_data,
        headers=headers
    )
    
    if response.status_code == 200:
        exam = response.json()
        print(f"  ✓ Created exam: {exam_data['title']} ({len(exam_questions)} questions, {total_points} points)")
        return exam
    else:
        print(f"  ✗ Failed to create exam: {response.text}")
        return None

def main():
    print("Loading dataset...")
    dataset_path = Path(__file__).parent.parent / "grading_dataset_enhanced.csv"
    if not dataset_path.exists():
        print(f"Dataset not found at {dataset_path}")
        sys.exit(1)
    
    df = pd.read_csv(dataset_path)
    print(f"Loaded {len(df)} questions from dataset\n")
    
    print("Logging in as professor...")
    token = login()
    print("✓ Login successful\n")
    
    created_courses = []
    
    for course_config in COURSE_CONFIGS:
        print(f"Creating course: {course_config['name']} ({course_config['code']})")
        
        # Filter questions for this subject and level
        course_questions = df[
            (df['subject'] == course_config['subject']) &
            (df['level'] == course_config['level'])
        ]
        
        if len(course_questions) == 0:
            print(f"  ⚠ No questions found for {course_config['subject']} {course_config['level']}, skipping...")
            continue
        
        # Create course
        course = create_course(token, course_config)
        if not course:
            continue
        
        created_courses.append(course)
        print(f"  ✓ Created course: {course['name']} (ID: {course['id']})")
        
        # Create 3 exams for this course
        print(f"  Creating exams...")
        for exam_type in EXAM_TYPES:
            exam = create_exam(token, course['id'], exam_type, course_questions, 
                             EXAM_TYPES.index(exam_type) + 1)
        
        print()
    
    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f"  Courses created: {len(created_courses)}")
    print(f"  Exams created: {len(created_courses) * 3}")
    print(f"{'='*60}\n")
    
    print("Test data creation complete!")
    print("\nYou can now:")
    print("  1. Log in as professor to view created courses and exams")
    print("  2. Log in as student to browse and enroll in courses")
    print("  3. Take exams and test the grading system")

if __name__ == "__main__":
    main()
