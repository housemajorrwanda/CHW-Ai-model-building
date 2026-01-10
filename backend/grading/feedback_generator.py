"""
Feedback Generator - Creates detailed feedback for students
"""
from typing import List, Dict
from .step import GradedStep, Step
import logging

logger = logging.getLogger(__name__)


class FeedbackGenerator:
    """
    Generates human-readable feedback for graded submissions.
    """
    
    def __init__(self, detailed: bool = True):
        """
        Initialize feedback generator.
        
        Args:
            detailed: Whether to include detailed explanations
        """
        self.detailed = detailed
    
    def generate_feedback(self,
                         graded_steps: List[GradedStep],
                         summary: Dict,
                         gold_solution: List[Step]) -> str:
        """
        Generate comprehensive feedback text.
        
        Args:
            graded_steps: List of graded steps
            summary: Summary dictionary from scoring engine
            gold_solution: Original gold solution
            
        Returns:
            Formatted feedback string
        """
        feedback_lines = []
        
        # Header
        feedback_lines.append("=" * 70)
        feedback_lines.append("GRADING FEEDBACK")
        feedback_lines.append("=" * 70)
        feedback_lines.append("")
        
        # Overall score
        feedback_lines.append(f"📊 OVERALL SCORE: {summary['total_points_earned']}/{summary['total_points_possible']} ({summary['percentage']:.1f}%)")
        feedback_lines.append("")
        
        # Step-by-step breakdown
        feedback_lines.append("📝 STEP-BY-STEP BREAKDOWN:")
        feedback_lines.append("-" * 70)
        
        for i, graded_step in enumerate(graded_steps, 1):
            feedback_lines.append(f"\nStep {i}:")
            feedback_lines.append(f"  Your answer: {graded_step.student_text}")
            
            if graded_step.matched_gold_step:
                feedback_lines.append(f"  Expected: {graded_step.matched_gold_step.text}")
                feedback_lines.append(f"  Points: {graded_step.points_earned}/{graded_step.points_possible}")
            
            feedback_lines.append(f"  {graded_step.feedback}")
        
        feedback_lines.append("")
        feedback_lines.append("-" * 70)
        
        # Statistics
        feedback_lines.append("")
        feedback_lines.append("📈 STATISTICS:")
        feedback_lines.append(f"  ✓ Correct steps: {summary['correct_steps']}")
        feedback_lines.append(f"  ~ Partial steps: {summary['partial_steps']}")
        feedback_lines.append(f"  ✗ Incorrect steps: {summary['incorrect_steps']}")
        
        # Missing required steps
        if summary['missing_required_steps'] > 0:
            feedback_lines.append("")
            feedback_lines.append("⚠️  MISSING REQUIRED STEPS:")
            for idx in summary['missing_step_indices']:
                gold_step = gold_solution[idx]
                feedback_lines.append(f"  • Step {gold_step.step_number}: {gold_step.text}")
        
        # Recommendations
        if self.detailed:
            feedback_lines.append("")
            feedback_lines.append(self._generate_recommendations(graded_steps, summary))
        
        feedback_lines.append("")
        feedback_lines.append("=" * 70)
        
        return "\n".join(feedback_lines)
    
    def _generate_recommendations(self,
                                 graded_steps: List[GradedStep],
                                 summary: Dict) -> str:
        """Generate personalized recommendations"""
        recommendations = ["💡 RECOMMENDATIONS:"]
        
        if summary['percentage'] >= 90:
            recommendations.append("  Excellent work! You demonstrated strong problem-solving skills.")
        elif summary['percentage'] >= 70:
            recommendations.append("  Good job! Review the steps marked as partial or incorrect.")
        else:
            recommendations.append("  Keep practicing! Focus on showing all required steps clearly.")
        
        if summary['missing_required_steps'] > 0:
            recommendations.append("  • Make sure to include all required steps in your solution.")
        
        if summary['partial_steps'] > 0:
            recommendations.append("  • Some steps were partially correct - check for minor errors.")
        
        if summary['incorrect_steps'] > summary['correct_steps']:
            recommendations.append("  • Review the solution method and practice similar problems.")
        
        return "\n".join(recommendations)
    
    def generate_summary_table(self, graded_steps: List[GradedStep]) -> List[Dict]:
        """
        Generate a table-friendly summary of graded steps.
        
        Returns:
            List of dictionaries suitable for display in a table
        """
        table_data = []
        
        for i, step in enumerate(graded_steps, 1):
            row = {
                'Step': i,
                'Student Answer': step.student_text[:50] + '...' if len(step.student_text) > 50 else step.student_text,
                'Expected': step.matched_gold_step.text[:50] + '...' if step.matched_gold_step and len(step.matched_gold_step.text) > 50 else (step.matched_gold_step.text if step.matched_gold_step else 'N/A'),
                'Status': self._status_icon(step.status),
                'Points': f"{step.points_earned}/{step.points_possible}" if step.points_possible > 0 else "N/A"
            }
            table_data.append(row)
        
        return table_data
    
    def _status_icon(self, status) -> str:
        """Get icon for status"""
        from .step import StepStatus
        
        icons = {
            StepStatus.CORRECT: "✓",
            StepStatus.PARTIALLY_CORRECT: "~",
            StepStatus.INCORRECT: "✗",
            StepStatus.NOT_ATTEMPTED: "○"
        }
        return icons.get(status, "?")

