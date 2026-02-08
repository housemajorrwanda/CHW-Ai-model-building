"""
Script to delete test exams created for testing
Run this script to clean up test exams from the database
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from database import SessionLocal
import models

def delete_test_exams():
    """Delete test exams from the database"""
    db = SessionLocal()
    
    try:
        # Find all test exams (exams with "Test:" in title)
        test_exams = db.query(models.Exam).filter(
            models.Exam.title.like("%Test:%")
        ).all()
        
        if not test_exams:
            print("✅ No test exams found to delete.")
            return
        
        exam_count = len(test_exams)
        exam_titles = [exam.title for exam in test_exams]
        
        # Delete test exams (cascade will delete questions and steps)
        for exam in test_exams:
            db.delete(exam)
        
        db.commit()
        
        print(f"✅ Successfully deleted {exam_count} test exam(s):")
        for title in exam_titles:
            print(f"   - {title}")
        
        # Optionally delete the test course if it has no other exams
        test_course = db.query(models.Course).filter(
            models.Course.name.like("%Test Course%")
        ).first()
        
        if test_course:
            remaining_exams = db.query(models.Exam).filter(
                models.Exam.course_id == test_course.id
            ).count()
            
            if remaining_exams == 0:
                db.delete(test_course)
                db.commit()
                print(f"\n✅ Also deleted test course: {test_course.name}")
            else:
                print(f"\n📚 Test course '{test_course.name}' still has {remaining_exams} exam(s), keeping it.")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error deleting test exams: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    delete_test_exams()

