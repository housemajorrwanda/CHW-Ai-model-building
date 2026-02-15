"""
Step data structure for math grading
Represents a single step in a solution
"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class StepStatus(Enum):
    """Status of a graded step"""
    CORRECT = "Correct"
    PARTIALLY_CORRECT = "Partially Correct"
    INCORRECT = "Incorrect"
    NOT_ATTEMPTED = "Not Attempted"


@dataclass
class Step:
    """
    Represents a single step in a math solution.
    
    Attributes:
        text: The mathematical expression or explanation
        points: Points awarded for this step
        required: If True, missing this step penalizes later steps
        step_number: Order in the solution (1, 2, 3...)
        category: Optional category (e.g., "simplification", "factoring")
    """
    text: str
    points: int
    required: bool = False
    step_number: int = 0
    category: Optional[str] = None
    
    def __post_init__(self):
        """Validate step data"""
        if self.points < 0:
            raise ValueError("Points must be non-negative")
        if not self.text or not self.text.strip():
            raise ValueError("Step text cannot be empty")
    
    def to_dict(self):
        """Convert to dictionary for serialization"""
        return {
            'text': self.text,
            'points': self.points,
            'required': self.required,
            'step_number': self.step_number,
            'category': self.category
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create Step from dictionary"""
        return cls(
            text=data['text'],
            points=data['points'],
            required=data.get('required', False),
            step_number=data.get('step_number', 0),
            category=data.get('category')
        )


@dataclass
class GradedStep:
    """
    Result of grading a student's step.
    
    Attributes:
        student_text: What the student wrote
        matched_gold_step: The gold step it matched (if any)
        status: Correct/Partially Correct/Incorrect
        points_earned: Actual points received
        points_possible: Maximum points for this step
        match_score: Confidence of match (0.0 to 1.0)
        feedback: Explanation of grading
        penalty_applied: Whether penalty was applied
    """
    student_text: str
    matched_gold_step: Optional[Step] = None
    status: StepStatus = StepStatus.INCORRECT
    points_earned: float = 0.0
    points_possible: int = 0
    match_score: float = 0.0
    feedback: str = ""
    penalty_applied: bool = False
    
    def to_dict(self):
        """Convert to dictionary for serialization"""
        return {
            'student_text': self.student_text,
            'matched_gold_step': self.matched_gold_step.to_dict() if self.matched_gold_step else None,
            'status': self.status.value,
            'points_earned': self.points_earned,
            'points_possible': self.points_possible,
            'match_score': self.match_score,
            'feedback': self.feedback,
            'penalty_applied': self.penalty_applied
        }

