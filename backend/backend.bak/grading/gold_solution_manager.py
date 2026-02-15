"""
Gold Solution Manager - Save/Load gold solutions (answer keys)
"""
import json
import os
from typing import List, Dict, Optional
from pathlib import Path
from .step import Step
import logging

logger = logging.getLogger(__name__)


class GoldSolutionManager:
    """
    Manages gold solutions (answer keys) - saving, loading, listing.
    """
    
    def __init__(self, solutions_dir: str = "answer_keys"):
        """
        Initialize manager.
        
        Args:
            solutions_dir: Directory to store gold solutions
        """
        self.solutions_dir = Path(solutions_dir)
        self.solutions_dir.mkdir(exist_ok=True, parents=True)
    
    def save_solution(self,
                     name: str,
                     steps: List[Step],
                     metadata: Optional[Dict] = None) -> str:
        """
        Save a gold solution to a JSON file.
        
        Args:
            name: Name for this solution (e.g., "midterm_problem_1")
            steps: List of Step objects
            metadata: Optional metadata (exam name, date, etc.)
            
        Returns:
            Path to saved file
        """
        # Create filename
        filename = f"{self._sanitize_name(name)}.json"
        filepath = self.solutions_dir / filename
        
        # Prepare data
        data = {
            'name': name,
            'total_points': sum(step.points for step in steps),
            'step_count': len(steps),
            'steps': [step.to_dict() for step in steps],
            'metadata': metadata or {}
        }
        
        # Save to file
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved gold solution: {filepath}")
            return str(filepath)
        
        except Exception as e:
            logger.error(f"Failed to save gold solution: {e}")
            raise
    
    def load_solution(self, name: str) -> tuple[List[Step], Dict]:
        """
        Load a gold solution from file.
        
        Args:
            name: Name of the solution (with or without .json extension)
            
        Returns:
            (steps, metadata) tuple
        """
        # Handle name with or without extension
        if not name.endswith('.json'):
            name = f"{name}.json"
        
        filepath = self.solutions_dir / name
        
        if not filepath.exists():
            raise FileNotFoundError(f"Gold solution not found: {filepath}")
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Reconstruct Step objects
            steps = [Step.from_dict(step_data) for step_data in data['steps']]
            metadata = data.get('metadata', {})
            
            logger.info(f"Loaded gold solution: {filepath}")
            return steps, metadata
        
        except Exception as e:
            logger.error(f"Failed to load gold solution: {e}")
            raise
    
    def list_solutions(self) -> List[Dict]:
        """
        List all available gold solutions.
        
        Returns:
            List of dictionaries with solution info
        """
        solutions = []
        
        for filepath in self.solutions_dir.glob("*.json"):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                solutions.append({
                    'filename': filepath.name,
                    'name': data.get('name', filepath.stem),
                    'total_points': data.get('total_points', 0),
                    'step_count': data.get('step_count', 0),
                    'metadata': data.get('metadata', {})
                })
            except Exception as e:
                logger.warning(f"Could not read solution file {filepath}: {e}")
        
        return sorted(solutions, key=lambda x: x['name'])
    
    def delete_solution(self, name: str) -> bool:
        """
        Delete a gold solution.
        
        Args:
            name: Name of the solution
            
        Returns:
            True if deleted successfully
        """
        if not name.endswith('.json'):
            name = f"{name}.json"
        
        filepath = self.solutions_dir / name
        
        if filepath.exists():
            try:
                filepath.unlink()
                logger.info(f"Deleted gold solution: {filepath}")
                return True
            except Exception as e:
                logger.error(f"Failed to delete solution: {e}")
                return False
        
        return False
    
    def _sanitize_name(self, name: str) -> str:
        """Sanitize filename"""
        # Remove invalid characters
        name = "".join(c if c.isalnum() or c in (' ', '_', '-') else '_' for c in name)
        # Replace spaces with underscores
        name = name.replace(' ', '_')
        # Convert to lowercase
        name = name.lower()
        return name
    
    def create_example_solution(self) -> str:
        """Create an example gold solution for testing"""
        example_steps = [
            Step(
                text="x² - 5x + 6 = 0",
                points=5,
                required=True,
                step_number=1,
                category="setup"
            ),
            Step(
                text="(x - 2)(x - 3) = 0",
                points=10,
                required=True,
                step_number=2,
                category="factoring"
            ),
            Step(
                text="x = 2 or x = 3",
                points=5,
                required=False,
                step_number=3,
                category="solution"
            )
        ]
        
        metadata = {
            'exam': 'Example Algebra Problem',
            'topic': 'Quadratic Equations',
            'difficulty': 'Medium'
        }
        
        return self.save_solution("example_quadratic", example_steps, metadata)

