"""
Script to create test math exams for testing the grading model
Run this script to populate the database with test exams
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from database import SessionLocal, engine
from database import Base
import models
from datetime import datetime, timedelta

def create_test_exams():
    """Create test exams in the database"""
    db = SessionLocal()
    
    try:
        # Get or create a test course
        # First, get the demo professor
        professor = db.query(models.User).filter(
            models.User.role == models.UserRole.PROFESSOR
        ).first()
        
        if not professor:
            print("❌ No professor found. Please create a course first.")
            return
        
        # Get or create a test course
        test_course = db.query(models.Course).filter(
            models.Course.professor_id == professor.id,
            models.Course.name.like("%Test%")
        ).first()
        
        if not test_course:
            test_course = models.Course(
                name="Test Course for Grading Model",
                code="TEST101",
                description="Temporary test course for testing the grading system",
                level=models.CourseLevel.INTERMEDIATE,
                professor_id=professor.id
            )
            db.add(test_course)
            db.flush()
            print(f"✅ Created test course: {test_course.name}")
        else:
            print(f"✅ Using existing test course: {test_course.name}")
        
        # Delete existing test exams to avoid duplicates
        existing_exams = db.query(models.Exam).filter(
            models.Exam.course_id == test_course.id,
            models.Exam.title.like("%Test%")
        ).all()
        
        for exam in existing_exams:
            db.delete(exam)
        db.commit()
        print(f"🗑️  Deleted {len(existing_exams)} existing test exams")
        
        # Exam 1: Algebra Fundamentals
        exam1 = models.Exam(
            course_id=test_course.id,
            title="Test: Algebra Fundamentals",
            description="Basic algebra and linear equations - TEST EXAM",
            total_points=35,
            due_date=datetime.utcnow() + timedelta(days=7)
        )
        db.add(exam1)
        db.flush()
        
        # Question 1.1
        q1_1 = models.Question(
            exam_id=exam1.id,
            number=1,
            text="Solve for x: 3x + 7 = 22",
            points=10,
            final_answer="x = 5",
            final_answer_latex="x = 5"
        )
        db.add(q1_1)
        db.flush()
        
        steps1_1 = [
            models.GoldSolutionStep(question_id=q1_1.id, step_number=1, description="Subtract 7 from both sides", expression="3x + 7 - 7 = 22 - 7", latex="3x + 7 - 7 = 22 - 7", points=3, required=True),
            models.GoldSolutionStep(question_id=q1_1.id, step_number=2, description="Simplify", expression="3x = 15", latex="3x = 15", points=2, required=True),
            models.GoldSolutionStep(question_id=q1_1.id, step_number=3, description="Divide both sides by 3", expression="x = 15/3", latex="x = \\frac{15}{3}", points=3, required=True),
            models.GoldSolutionStep(question_id=q1_1.id, step_number=4, description="Final answer", expression="x = 5", latex="x = 5", points=2, required=True),
        ]
        db.add_all(steps1_1)
        
        # Question 1.2
        q1_2 = models.Question(
            exam_id=exam1.id,
            number=2,
            text="Solve the quadratic equation: x² - 5x + 6 = 0",
            points=15,
            final_answer="x = 2 or x = 3",
            final_answer_latex="x = 2 \\text{ or } x = 3"
        )
        db.add(q1_2)
        db.flush()
        
        steps1_2 = [
            models.GoldSolutionStep(question_id=q1_2.id, step_number=1, description="Factor the quadratic", expression="(x - 2)(x - 3) = 0", latex="(x - 2)(x - 3) = 0", points=5, required=True),
            models.GoldSolutionStep(question_id=q1_2.id, step_number=2, description="Set each factor equal to zero", expression="x - 2 = 0 or x - 3 = 0", latex="x - 2 = 0 \\text{ or } x - 3 = 0", points=5, required=True),
            models.GoldSolutionStep(question_id=q1_2.id, step_number=3, description="Solve for x", expression="x = 2 or x = 3", latex="x = 2 \\text{ or } x = 3", points=5, required=True),
        ]
        db.add_all(steps1_2)
        
        # Question 1.3
        q1_3 = models.Question(
            exam_id=exam1.id,
            number=3,
            text="Simplify: (2x + 3)(x - 4)",
            points=10,
            final_answer="2x² - 5x - 12",
            final_answer_latex="2x^2 - 5x - 12"
        )
        db.add(q1_3)
        db.flush()
        
        steps1_3 = [
            models.GoldSolutionStep(question_id=q1_3.id, step_number=1, description="Apply FOIL method", expression="2x(x) + 2x(-4) + 3(x) + 3(-4)", latex="2x \\cdot x + 2x \\cdot (-4) + 3 \\cdot x + 3 \\cdot (-4)", points=4, required=True),
            models.GoldSolutionStep(question_id=q1_3.id, step_number=2, description="Multiply terms", expression="2x² - 8x + 3x - 12", latex="2x^2 - 8x + 3x - 12", points=3, required=True),
            models.GoldSolutionStep(question_id=q1_3.id, step_number=3, description="Combine like terms", expression="2x² - 5x - 12", latex="2x^2 - 5x - 12", points=3, required=True),
        ]
        db.add_all(steps1_3)
        
        # Exam 2: Calculus Basics
        exam2 = models.Exam(
            course_id=test_course.id,
            title="Test: Calculus Basics - Derivatives",
            description="Basic derivative problems - TEST EXAM",
            total_points=35,
            due_date=datetime.utcnow() + timedelta(days=7)
        )
        db.add(exam2)
        db.flush()
        
        # Question 2.1
        q2_1 = models.Question(
            exam_id=exam2.id,
            number=1,
            text="Find the derivative of f(x) = 3x² + 5x - 2",
            points=15,
            final_answer="f'(x) = 6x + 5",
            final_answer_latex="f'(x) = 6x + 5"
        )
        db.add(q2_1)
        db.flush()
        
        steps2_1 = [
            models.GoldSolutionStep(question_id=q2_1.id, step_number=1, description="Apply power rule to each term", expression="f'(x) = d/dx(3x²) + d/dx(5x) - d/dx(2)", latex="f'(x) = \\frac{d}{dx}(3x^2) + \\frac{d}{dx}(5x) - \\frac{d}{dx}(2)", points=5, required=True),
            models.GoldSolutionStep(question_id=q2_1.id, step_number=2, description="Derivative of 3x²", expression="d/dx(3x²) = 6x", latex="\\frac{d}{dx}(3x^2) = 6x", points=3, required=True),
            models.GoldSolutionStep(question_id=q2_1.id, step_number=3, description="Derivative of 5x", expression="d/dx(5x) = 5", latex="\\frac{d}{dx}(5x) = 5", points=3, required=True),
            models.GoldSolutionStep(question_id=q2_1.id, step_number=4, description="Derivative of constant is zero", expression="d/dx(2) = 0", latex="\\frac{d}{dx}(2) = 0", points=2, required=True),
            models.GoldSolutionStep(question_id=q2_1.id, step_number=5, description="Final answer", expression="f'(x) = 6x + 5", latex="f'(x) = 6x + 5", points=2, required=True),
        ]
        db.add_all(steps2_1)
        
        # Question 2.2
        q2_2 = models.Question(
            exam_id=exam2.id,
            number=2,
            text="Find the derivative of f(x) = x³ · e^x using product rule",
            points=20,
            final_answer="f'(x) = x²e^x(3 + x)",
            final_answer_latex="f'(x) = x^2 e^x (3 + x)"
        )
        db.add(q2_2)
        db.flush()
        
        steps2_2 = [
            models.GoldSolutionStep(question_id=q2_2.id, step_number=1, description="Identify u and v", expression="u = x³, v = e^x", latex="u = x^3, \\quad v = e^x", points=3, required=True),
            models.GoldSolutionStep(question_id=q2_2.id, step_number=2, description="Find u' and v'", expression="u' = 3x², v' = e^x", latex="u' = 3x^2, \\quad v' = e^x", points=5, required=True),
            models.GoldSolutionStep(question_id=q2_2.id, step_number=3, description="Apply product rule: (uv)' = u'v + uv'", expression="f'(x) = (3x²)(e^x) + (x³)(e^x)", latex="f'(x) = (3x^2)(e^x) + (x^3)(e^x)", points=6, required=True),
            models.GoldSolutionStep(question_id=q2_2.id, step_number=4, description="Factor out e^x", expression="f'(x) = e^x(3x² + x³)", latex="f'(x) = e^x(3x^2 + x^3)", points=3, required=False),
            models.GoldSolutionStep(question_id=q2_2.id, step_number=5, description="Factor out x²", expression="f'(x) = x²e^x(3 + x)", latex="f'(x) = x^2 e^x (3 + x)", points=3, required=False),
        ]
        db.add_all(steps2_2)
        
        # Exam 3: Systems of Equations
        exam3 = models.Exam(
            course_id=test_course.id,
            title="Test: Systems of Linear Equations",
            description="Solving systems using substitution and elimination - TEST EXAM",
            total_points=20,
            due_date=datetime.utcnow() + timedelta(days=7)
        )
        db.add(exam3)
        db.flush()
        
        # Question 3.1
        q3_1 = models.Question(
            exam_id=exam3.id,
            number=1,
            text="Solve the system: 2x + y = 7 and x - y = 2",
            points=20,
            final_answer="x = 3, y = 1",
            final_answer_latex="x = 3, \\quad y = 1"
        )
        db.add(q3_1)
        db.flush()
        
        steps3_1 = [
            models.GoldSolutionStep(question_id=q3_1.id, step_number=1, description="Add the two equations to eliminate y", expression="(2x + y) + (x - y) = 7 + 2", latex="(2x + y) + (x - y) = 7 + 2", points=5, required=True),
            models.GoldSolutionStep(question_id=q3_1.id, step_number=2, description="Simplify", expression="3x = 9", latex="3x = 9", points=3, required=True),
            models.GoldSolutionStep(question_id=q3_1.id, step_number=3, description="Solve for x", expression="x = 3", latex="x = 3", points=4, required=True),
            models.GoldSolutionStep(question_id=q3_1.id, step_number=4, description="Substitute x = 3 into first equation", expression="2(3) + y = 7", latex="2(3) + y = 7", points=4, required=True),
            models.GoldSolutionStep(question_id=q3_1.id, step_number=5, description="Solve for y", expression="6 + y = 7, so y = 1", latex="6 + y = 7, \\text{ so } y = 1", points=4, required=True),
        ]
        db.add_all(steps3_1)
        
        db.commit()
        
        print("\n✅ Successfully created test exams:")
        print(f"   1. {exam1.title} ({exam1.total_points} points)")
        print(f"   2. {exam2.title} ({exam2.total_points} points)")
        print(f"   3. {exam3.title} ({exam3.total_points} points)")
        print(f"\n📚 Course: {test_course.name} (ID: {test_course.id})")
        print("\n💡 You can now test the grading system with these exams!")
        print("   To delete them later, run: python delete_test_exams.py")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error creating test exams: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    create_test_exams()

