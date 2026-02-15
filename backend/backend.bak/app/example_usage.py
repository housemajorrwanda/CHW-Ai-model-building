"""
Example usage of the Math Grader model.

This demonstrates how to use the grading system for various mathematical problems.
"""

from math_grader import MathGrader, Step, create_grader_from_rubric


def example_quadratic_equation():
    """Example: Solving a quadratic equation"""
    print("=" * 60)
    print("Example 1: Solving Quadratic Equation")
    print("=" * 60)
    
    # Define gold standard solution
    gold_steps = [
        Step("x^2 - 5x + 6 = 0", points=1.0, required=True),
        Step("(x - 2)(x - 3) = 0", points=1.0, required=True),
        Step("x - 2 = 0 or x - 3 = 0", points=1.0, required=True),
        Step("x = 2 or x = 3", points=2.0, required=True),  # Final answer worth more
    ]
    
    grader = MathGrader(gold_steps)
    
    # Test Case 1: Perfect solution
    print("\n--- Test Case 1: Perfect Solution ---")
    student_solution_1 = [
        "x^2 - 5x + 6 = 0",
        "(x - 2)(x - 3) = 0",
        "x - 2 = 0 or x - 3 = 0",
        "x = 2 or x = 3"
    ]
    result_1 = grader.grade(student_solution_1)
    print_result(result_1, student_solution_1)
    
    # Test Case 2: Correct but different format
    print("\n--- Test Case 2: Mathematically Equivalent ---")
    student_solution_2 = [
        "x^2 - 5x + 6 = 0",
        "x^2 - 5*x + 6 = 0",  # Different notation
        "x = 2 or x = 3"  # Skipped intermediate step
    ]
    result_2 = grader.grade(student_solution_2)
    print_result(result_2, student_solution_2)
    
    # Test Case 3: Partial solution (only first step)
    print("\n--- Test Case 3: Partial Solution (1 step) ---")
    student_solution_3 = [
        "x^2 - 5x + 6 = 0"
    ]
    result_3 = grader.grade(student_solution_3)
    print_result(result_3, student_solution_3)
    
    # Test Case 4: Incorrect solution
    print("\n--- Test Case 4: Incorrect Solution ---")
    student_solution_4 = [
        "x^2 - 5x + 6 = 0",
        "(x - 1)(x - 6) = 0",  # Wrong factorization
        "x = 1 or x = 6"
    ]
    result_4 = grader.grade(student_solution_4)
    print_result(result_4, student_solution_4)


def example_linear_equation():
    """Example: Solving a linear equation"""
    print("\n\n" + "=" * 60)
    print("Example 2: Solving Linear Equation")
    print("=" * 60)
    
    # Using helper function for convenience
    grader = create_grader_from_rubric([
        ("2x + 3 = 11", 1.0, True),
        ("2x = 11 - 3", 1.0, True),
        ("2x = 8", 1.0, True),
        ("x = 4", 2.0, True),  # Final answer
    ])
    
    print("\n--- Student Solution ---")
    student_solution = [
        "2x + 3 = 11",
        "2x = 8",  # Skipped one step
        "x = 4"
    ]
    result = grader.grade(student_solution)
    print_result(result, student_solution)


def example_calculus():
    """Example: Calculus problem"""
    print("\n\n" + "=" * 60)
    print("Example 3: Derivative Problem")
    print("=" * 60)
    
    gold_steps = [
        Step("f(x) = x^2 + 3x", points=1.0, required=True),
        Step("f'(x) = 2x + 3", points=2.0, required=True),
        Step("f'(2) = 2(2) + 3", points=1.0, required=True),
        Step("f'(2) = 7", points=1.0, required=True),
    ]
    
    grader = MathGrader(gold_steps)
    
    print("\n--- Student Solution ---")
    student_solution = [
        "f(x) = x^2 + 3x",
        "f'(x) = 2x + 3",
        "f'(2) = 7"  # Skipped substitution step
    ]
    result = grader.grade(student_solution)
    print_result(result, student_solution)


def print_result(result, student_steps):
    """Pretty print grading results"""
    print(f"\nStudent Solution ({len(student_steps)} steps):")
    for i, step in enumerate(student_steps, 1):
        print(f"  Step {i}: {step}")
    
    print(f"\nGrading Results:")
    print(f"  Total Score: {result['total_score']:.1f} / {result['max_score']:.1f}")
    print(f"  Percentage: {result['percentage']:.1f}%")
    
    print(f"\nStep-by-Step Evaluation:")
    for i, eval_obj in enumerate(result['evaluations'], 1):
        print(f"  Step {i}:")
        print(f"    Status: {eval_obj.status.value}")
        print(f"    Points: {eval_obj.points_earned:.1f}")
        print(f"    Feedback: {eval_obj.feedback}")
        if eval_obj.matched_gold_step is not None:
            print(f"    Matched Gold Step: {eval_obj.matched_gold_step + 1}")


def interactive_grading():
    """Interactive mode for grading custom solutions"""
    print("\n\n" + "=" * 60)
    print("Interactive Grading Mode")
    print("=" * 60)
    
    print("\nEnter gold standard steps (one per line, empty line to finish):")
    gold_steps = []
    step_num = 1
    while True:
        content = input(f"Gold Step {step_num} (or press Enter to finish): ").strip()
        if not content:
            break
        
        points = float(input(f"  Points for step {step_num} (default 1.0): ") or "1.0")
        required = input(f"  Required? (y/n, default y): ").strip().lower() != 'n'
        
        gold_steps.append(Step(content, points, required))
        step_num += 1
    
    if not gold_steps:
        print("No gold steps provided. Exiting.")
        return
    
    grader = MathGrader(gold_steps)
    
    print("\nEnter student solution steps (one per line, empty line to finish):")
    student_steps = []
    while True:
        step = input(f"Student Step {len(student_steps) + 1} (or press Enter to finish): ").strip()
        if not step:
            break
        student_steps.append(step)
    
    if not student_steps:
        print("No student steps provided. Exiting.")
        return
    
    result = grader.grade(student_steps)
    print_result(result, student_steps)


if __name__ == "__main__":
    # Run examples
    example_quadratic_equation()
    example_linear_equation()
    example_calculus()
    
    # Uncomment to run interactive mode
    # interactive_grading()

