#!/usr/bin/env python3
"""
Script to add 4 custom exams (Math, Biology, Chemistry, Physics)
"""
import requests
import json
import sys
from pathlib import Path

# Configuration
API_BASE_URL = "http://localhost:8000/api"
PROFESSOR_EMAIL = "professor@university.edu"
PROFESSOR_PASSWORD = "password"

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

def get_courses(token):
    """Get all courses"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{API_BASE_URL}/courses", headers=headers)
    if response.status_code == 200:
        return response.json()
    return []

def find_course_by_code(courses, code_prefix):
    """Find course by code prefix"""
    for course in courses:
        if course.get("code", "").startswith(code_prefix):
            return course["id"]
    return None

# Exam definitions
EXAMS = {
    "math": {
        "title": "Algebra and Geometry Midterm",
        "description": "Comprehensive exam covering algebraic equations, quadratic functions, and basic geometry",
        "course_code_prefix": "MATH",
        "questions": [
            {
                "number": 1,
                "text": "Solve the quadratic equation: x² - 5x + 6 = 0",
                "points": 10,
                "goldSolutionSteps": [
                    {
                        "stepNumber": 1,
                        "description": "Identify coefficients",
                        "expression": "a = 1, b = -5, c = 6",
                        "latex": "a = 1, b = -5, c = 6",
                        "points": 2,
                        "required": True
                    },
                    {
                        "stepNumber": 2,
                        "description": "Apply quadratic formula",
                        "expression": "x = (-b ± √(b² - 4ac)) / 2a",
                        "latex": "x = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}",
                        "points": 3,
                        "required": True
                    },
                    {
                        "stepNumber": 3,
                        "description": "Calculate discriminant",
                        "expression": "b² - 4ac = (-5)² - 4(1)(6) = 25 - 24 = 1",
                        "latex": "b^2 - 4ac = (-5)^2 - 4(1)(6) = 25 - 24 = 1",
                        "points": 2,
                        "required": True
                    },
                    {
                        "stepNumber": 4,
                        "description": "Find solutions",
                        "expression": "x = (5 ± 1) / 2, so x = 3 or x = 2",
                        "latex": "x = \\frac{5 \\pm 1}{2}, \\text{ so } x = 3 \\text{ or } x = 2",
                        "points": 3,
                        "required": True
                    }
                ],
                "finalAnswer": "x = 2 or x = 3",
                "finalAnswerLatex": "x = 2 \\text{ or } x = 3"
            },
            {
                "number": 2,
                "text": "Find the area of a circle with radius 7 cm. Use π = 3.14",
                "points": 8,
                "goldSolutionSteps": [
                    {
                        "stepNumber": 1,
                        "description": "Write the area formula",
                        "expression": "Area = πr²",
                        "latex": "A = \\pi r^2",
                        "points": 2,
                        "required": True
                    },
                    {
                        "stepNumber": 2,
                        "description": "Substitute values",
                        "expression": "Area = 3.14 × (7)²",
                        "latex": "A = 3.14 \\times 7^2",
                        "points": 2,
                        "required": True
                    },
                    {
                        "stepNumber": 3,
                        "description": "Calculate",
                        "expression": "Area = 3.14 × 49 = 153.86",
                        "latex": "A = 3.14 \\times 49 = 153.86",
                        "points": 2,
                        "required": True
                    },
                    {
                        "stepNumber": 4,
                        "description": "State answer with units",
                        "expression": "Area = 153.86 cm²",
                        "latex": "A = 153.86 \\text{ cm}^2",
                        "points": 2,
                        "required": True
                    }
                ],
                "finalAnswer": "153.86 cm²",
                "finalAnswerLatex": "153.86 \\text{ cm}^2"
            },
            {
                "number": 3,
                "text": "Simplify: (2x + 3)(x - 4)",
                "points": 8,
                "goldSolutionSteps": [
                    {
                        "stepNumber": 1,
                        "description": "Apply FOIL method",
                        "expression": "(2x)(x) + (2x)(-4) + (3)(x) + (3)(-4)",
                        "latex": "(2x)(x) + (2x)(-4) + (3)(x) + (3)(-4)",
                        "points": 3,
                        "required": True
                    },
                    {
                        "stepNumber": 2,
                        "description": "Multiply terms",
                        "expression": "2x² - 8x + 3x - 12",
                        "latex": "2x^2 - 8x + 3x - 12",
                        "points": 2,
                        "required": True
                    },
                    {
                        "stepNumber": 3,
                        "description": "Combine like terms",
                        "expression": "2x² - 5x - 12",
                        "latex": "2x^2 - 5x - 12",
                        "points": 3,
                        "required": True
                    }
                ],
                "finalAnswer": "2x² - 5x - 12",
                "finalAnswerLatex": "2x^2 - 5x - 12"
            },
            {
                "number": 4,
                "text": "Solve for x: 3x + 7 = 22",
                "points": 6,
                "goldSolutionSteps": [
                    {
                        "stepNumber": 1,
                        "description": "Subtract 7 from both sides",
                        "expression": "3x = 22 - 7",
                        "latex": "3x = 22 - 7",
                        "points": 2,
                        "required": True
                    },
                    {
                        "stepNumber": 2,
                        "description": "Simplify",
                        "expression": "3x = 15",
                        "latex": "3x = 15",
                        "points": 2,
                        "required": True
                    },
                    {
                        "stepNumber": 3,
                        "description": "Divide by 3",
                        "expression": "x = 5",
                        "latex": "x = 5",
                        "points": 2,
                        "required": True
                    }
                ],
                "finalAnswer": "x = 5",
                "finalAnswerLatex": "x = 5"
            },
            {
                "number": 5,
                "text": "Calculate the slope of the line passing through points (2, 3) and (5, 11)",
                "points": 8,
                "goldSolutionSteps": [
                    {
                        "stepNumber": 1,
                        "description": "Write slope formula",
                        "expression": "m = (y₂ - y₁) / (x₂ - x₁)",
                        "latex": "m = \\frac{y_2 - y_1}{x_2 - x_1}",
                        "points": 2,
                        "required": True
                    },
                    {
                        "stepNumber": 2,
                        "description": "Substitute coordinates",
                        "expression": "m = (11 - 3) / (5 - 2)",
                        "latex": "m = \\frac{11 - 3}{5 - 2}",
                        "points": 2,
                        "required": True
                    },
                    {
                        "stepNumber": 3,
                        "description": "Calculate",
                        "expression": "m = 8 / 3",
                        "latex": "m = \\frac{8}{3}",
                        "points": 4,
                        "required": True
                    }
                ],
                "finalAnswer": "8/3",
                "finalAnswerLatex": "\\frac{8}{3}"
            }
        ]
    },
    "biology": {
        "title": "Cell Biology and Genetics Quiz",
        "description": "Assessment covering cell structure, DNA replication, and basic genetics",
        "course_code_prefix": "BIO",
        "questions": [
            {
                "number": 1,
                "text": "Describe the structure and function of the cell membrane. What is its primary component?",
                "points": 12,
                "goldSolutionSteps": [
                    {
                        "stepNumber": 1,
                        "description": "Identify primary component",
                        "expression": "The cell membrane is primarily composed of phospholipids",
                        "latex": "",
                        "points": 3,
                        "required": True
                    },
                    {
                        "stepNumber": 2,
                        "description": "Describe structure",
                        "expression": "Phospholipids form a bilayer with hydrophilic heads facing outward and hydrophobic tails facing inward",
                        "latex": "",
                        "points": 4,
                        "required": True
                    },
                    {
                        "stepNumber": 3,
                        "description": "Explain function",
                        "expression": "The membrane controls what enters and exits the cell, maintaining homeostasis",
                        "latex": "",
                        "points": 3,
                        "required": True
                    },
                    {
                        "stepNumber": 4,
                        "description": "Mention additional components",
                        "expression": "It also contains proteins for transport and cholesterol for fluidity",
                        "latex": "",
                        "points": 2,
                        "required": False
                    }
                ],
                "finalAnswer": "The cell membrane is a phospholipid bilayer that regulates material exchange and maintains cell integrity",
                "finalAnswerLatex": ""
            },
            {
                "number": 2,
                "text": "In a genetic cross between two heterozygous parents (Aa × Aa), what is the probability of offspring being homozygous recessive (aa)?",
                "points": 10,
                "goldSolutionSteps": [
                    {
                        "stepNumber": 1,
                        "description": "Set up Punnett square",
                        "expression": "Parent 1 gametes: A, a | Parent 2 gametes: A, a",
                        "latex": "",
                        "points": 3,
                        "required": True
                    },
                    {
                        "stepNumber": 2,
                        "description": "Fill Punnett square",
                        "expression": "Offspring genotypes: AA, Aa, Aa, aa",
                        "latex": "",
                        "points": 3,
                        "required": True
                    },
                    {
                        "stepNumber": 3,
                        "description": "Count homozygous recessive",
                        "expression": "One out of four offspring is aa",
                        "latex": "",
                        "points": 2,
                        "required": True
                    },
                    {
                        "stepNumber": 4,
                        "description": "State probability",
                        "expression": "Probability = 1/4 or 25%",
                        "latex": "P = \\frac{1}{4} = 25\\%",
                        "points": 2,
                        "required": True
                    }
                ],
                "finalAnswer": "1/4 or 25%",
                "finalAnswerLatex": "\\frac{1}{4} = 25\\%"
            },
            {
                "number": 3,
                "text": "What are the three stages of cellular respiration?",
                "points": 9,
                "goldSolutionSteps": [
                    {
                        "stepNumber": 1,
                        "description": "First stage",
                        "expression": "Glycolysis - occurs in cytoplasm, breaks down glucose to pyruvate",
                        "latex": "",
                        "points": 3,
                        "required": True
                    },
                    {
                        "stepNumber": 2,
                        "description": "Second stage",
                        "expression": "Krebs cycle (Citric Acid Cycle) - occurs in mitochondria, produces ATP and electron carriers",
                        "latex": "",
                        "points": 3,
                        "required": True
                    },
                    {
                        "stepNumber": 3,
                        "description": "Third stage",
                        "expression": "Electron Transport Chain - occurs in mitochondria, produces most ATP",
                        "latex": "",
                        "points": 3,
                        "required": True
                    }
                ],
                "finalAnswer": "Glycolysis, Krebs Cycle, Electron Transport Chain",
                "finalAnswerLatex": ""
            },
            {
                "number": 4,
                "text": "Explain the difference between mitosis and meiosis",
                "points": 10,
                "goldSolutionSteps": [
                    {
                        "stepNumber": 1,
                        "description": "Mitosis purpose",
                        "expression": "Mitosis produces two identical diploid cells for growth and repair",
                        "latex": "",
                        "points": 3,
                        "required": True
                    },
                    {
                        "stepNumber": 2,
                        "description": "Meiosis purpose",
                        "expression": "Meiosis produces four genetically different haploid gametes for reproduction",
                        "latex": "",
                        "points": 3,
                        "required": True
                    },
                    {
                        "stepNumber": 3,
                        "description": "Key difference in divisions",
                        "expression": "Mitosis has one division, meiosis has two divisions",
                        "latex": "",
                        "points": 2,
                        "required": True
                    },
                    {
                        "stepNumber": 4,
                        "description": "Genetic variation",
                        "expression": "Meiosis includes crossing over and independent assortment, creating genetic diversity",
                        "latex": "",
                        "points": 2,
                        "required": True
                    }
                ],
                "finalAnswer": "Mitosis produces identical cells for growth; meiosis produces diverse gametes for reproduction",
                "finalAnswerLatex": ""
            },
            {
                "number": 5,
                "text": "What is the function of DNA polymerase in DNA replication?",
                "points": 8,
                "goldSolutionSteps": [
                    {
                        "stepNumber": 1,
                        "description": "Primary function",
                        "expression": "DNA polymerase adds nucleotides to the growing DNA strand",
                        "latex": "",
                        "points": 3,
                        "required": True
                    },
                    {
                        "stepNumber": 2,
                        "description": "Direction",
                        "expression": "It synthesizes DNA in the 5' to 3' direction only",
                        "latex": "",
                        "points": 2,
                        "required": True
                    },
                    {
                        "stepNumber": 3,
                        "description": "Proofreading",
                        "expression": "It has proofreading ability to correct errors during replication",
                        "latex": "",
                        "points": 3,
                        "required": True
                    }
                ],
                "finalAnswer": "DNA polymerase synthesizes new DNA strands by adding nucleotides in the 5' to 3' direction and proofreads for errors",
                "finalAnswerLatex": ""
            }
        ]
    },
    "chemistry": {
        "title": "Stoichiometry and Chemical Reactions",
        "description": "Exam covering mole calculations, balancing equations, and reaction stoichiometry",
        "course_code_prefix": "CHEM",
        "questions": [
            {
                "number": 1,
                "text": "Balance the following chemical equation: Fe + O₂ → Fe₂O₃",
                "points": 10,
                "goldSolutionSteps": [
                    {
                        "stepNumber": 1,
                        "description": "Count atoms on each side",
                        "expression": "Left: Fe=1, O=2 | Right: Fe=2, O=3",
                        "latex": "",
                        "points": 2,
                        "required": True
                    },
                    {
                        "stepNumber": 2,
                        "description": "Balance iron atoms",
                        "expression": "4Fe + O₂ → 2Fe₂O₃ (now Fe=4 on both sides)",
                        "latex": "4\\text{Fe} + \\text{O}_2 \\rightarrow 2\\text{Fe}_2\\text{O}_3",
                        "points": 3,
                        "required": True
                    },
                    {
                        "stepNumber": 3,
                        "description": "Balance oxygen atoms",
                        "expression": "4Fe + 3O₂ → 2Fe₂O₃ (now O=6 on both sides)",
                        "latex": "4\\text{Fe} + 3\\text{O}_2 \\rightarrow 2\\text{Fe}_2\\text{O}_3",
                        "points": 3,
                        "required": True
                    },
                    {
                        "stepNumber": 4,
                        "description": "Verify balance",
                        "expression": "Left: Fe=4, O=6 | Right: Fe=4, O=6 ✓",
                        "latex": "",
                        "points": 2,
                        "required": True
                    }
                ],
                "finalAnswer": "4Fe + 3O₂ → 2Fe₂O₃",
                "finalAnswerLatex": "4\\text{Fe} + 3\\text{O}_2 \\rightarrow 2\\text{Fe}_2\\text{O}_3"
            },
            {
                "number": 2,
                "text": "Calculate the number of moles in 88 grams of CO₂. (Atomic masses: C=12, O=16)",
                "points": 10,
                "goldSolutionSteps": [
                    {
                        "stepNumber": 1,
                        "description": "Calculate molar mass",
                        "expression": "Molar mass of CO₂ = 12 + (16 × 2) = 12 + 32 = 44 g/mol",
                        "latex": "M_{\\text{CO}_2} = 12 + (16 \\times 2) = 44 \\text{ g/mol}",
                        "points": 3,
                        "required": True
                    },
                    {
                        "stepNumber": 2,
                        "description": "Write mole formula",
                        "expression": "Number of moles = mass / molar mass",
                        "latex": "n = \\frac{m}{M}",
                        "points": 2,
                        "required": True
                    },
                    {
                        "stepNumber": 3,
                        "description": "Substitute values",
                        "expression": "n = 88 g / 44 g/mol",
                        "latex": "n = \\frac{88}{44}",
                        "points": 2,
                        "required": True
                    },
                    {
                        "stepNumber": 4,
                        "description": "Calculate",
                        "expression": "n = 2 moles",
                        "latex": "n = 2 \\text{ mol}",
                        "points": 3,
                        "required": True
                    }
                ],
                "finalAnswer": "2 moles",
                "finalAnswerLatex": "2 \\text{ mol}"
            },
            {
                "number": 3,
                "text": "What volume of hydrogen gas (H₂) is produced at STP when 2 moles of zinc react with excess hydrochloric acid? (Zn + 2HCl → ZnCl₂ + H₂)",
                "points": 12,
                "goldSolutionSteps": [
                    {
                        "stepNumber": 1,
                        "description": "Identify mole ratio",
                        "expression": "From equation: 1 mole Zn produces 1 mole H₂",
                        "latex": "",
                        "points": 3,
                        "required": True
                    },
                    {
                        "stepNumber": 2,
                        "description": "Calculate moles of H₂",
                        "expression": "2 moles Zn × (1 mole H₂ / 1 mole Zn) = 2 moles H₂",
                        "latex": "",
                        "points": 3,
                        "required": True
                    },
                    {
                        "stepNumber": 3,
                        "description": "Use molar volume at STP",
                        "expression": "At STP, 1 mole of gas = 22.4 L",
                        "latex": "",
                        "points": 2,
                        "required": True
                    },
                    {
                        "stepNumber": 4,
                        "description": "Calculate volume",
                        "expression": "Volume = 2 moles × 22.4 L/mol = 44.8 L",
                        "latex": "V = 2 \\times 22.4 = 44.8 \\text{ L}",
                        "points": 4,
                        "required": True
                    }
                ],
                "finalAnswer": "44.8 L",
                "finalAnswerLatex": "44.8 \\text{ L}"
            },
            {
                "number": 4,
                "text": "Classify the following reaction: 2H₂ + O₂ → 2H₂O",
                "points": 8,
                "goldSolutionSteps": [
                    {
                        "stepNumber": 1,
                        "description": "Identify reaction type",
                        "expression": "This is a combination (synthesis) reaction",
                        "latex": "",
                        "points": 3,
                        "required": True
                    },
                    {
                        "stepNumber": 2,
                        "description": "Explain characteristics",
                        "expression": "Two or more reactants combine to form a single product",
                        "latex": "",
                        "points": 3,
                        "required": True
                    },
                    {
                        "stepNumber": 3,
                        "description": "Additional classification",
                        "expression": "It is also a combustion reaction (reaction with oxygen)",
                        "latex": "",
                        "points": 2,
                        "required": False
                    }
                ],
                "finalAnswer": "Combination (synthesis) reaction",
                "finalAnswerLatex": ""
            },
            {
                "number": 5,
                "text": "Calculate the percentage composition of carbon in CH₄. (Atomic masses: C=12, H=1)",
                "points": 10,
                "goldSolutionSteps": [
                    {
                        "stepNumber": 1,
                        "description": "Calculate molar mass",
                        "expression": "Molar mass of CH₄ = 12 + (1 × 4) = 16 g/mol",
                        "latex": "M_{\\text{CH}_4} = 12 + 4 = 16 \\text{ g/mol}",
                        "points": 3,
                        "required": True
                    },
                    {
                        "stepNumber": 2,
                        "description": "Find mass of carbon",
                        "expression": "Mass of C in one mole = 12 g",
                        "latex": "",
                        "points": 2,
                        "required": True
                    },
                    {
                        "stepNumber": 3,
                        "description": "Calculate percentage",
                        "expression": "% C = (mass of C / molar mass) × 100 = (12/16) × 100",
                        "latex": "\\% \\text{C} = \\frac{12}{16} \\times 100",
                        "points": 3,
                        "required": True
                    },
                    {
                        "stepNumber": 4,
                        "description": "Final answer",
                        "expression": "% C = 75%",
                        "latex": "75\\%",
                        "points": 2,
                        "required": True
                    }
                ],
                "finalAnswer": "75%",
                "finalAnswerLatex": "75\\%"
            }
        ]
    },
    "physics": {
        "title": "Mechanics and Energy Fundamentals",
        "description": "Assessment covering motion, forces, work, and energy principles",
        "course_code_prefix": "PHY",
        "questions": [
            {
                "number": 1,
                "text": "A car accelerates from rest to 60 m/s in 10 seconds. Calculate its acceleration.",
                "points": 10,
                "goldSolutionSteps": [
                    {
                        "stepNumber": 1,
                        "description": "Identify given values",
                        "expression": "Initial velocity (u) = 0 m/s, Final velocity (v) = 60 m/s, Time (t) = 10 s",
                        "latex": "u = 0 \\text{ m/s}, v = 60 \\text{ m/s}, t = 10 \\text{ s}",
                        "points": 2,
                        "required": True
                    },
                    {
                        "stepNumber": 2,
                        "description": "Write acceleration formula",
                        "expression": "a = (v - u) / t",
                        "latex": "a = \\frac{v - u}{t}",
                        "points": 2,
                        "required": True
                    },
                    {
                        "stepNumber": 3,
                        "description": "Substitute values",
                        "expression": "a = (60 - 0) / 10",
                        "latex": "a = \\frac{60 - 0}{10}",
                        "points": 3,
                        "required": True
                    },
                    {
                        "stepNumber": 4,
                        "description": "Calculate",
                        "expression": "a = 6 m/s²",
                        "latex": "a = 6 \\text{ m/s}^2",
                        "points": 3,
                        "required": True
                    }
                ],
                "finalAnswer": "6 m/s²",
                "finalAnswerLatex": "6 \\text{ m/s}^2"
            },
            {
                "number": 2,
                "text": "Calculate the kinetic energy of a 2 kg object moving at 5 m/s.",
                "points": 10,
                "goldSolutionSteps": [
                    {
                        "stepNumber": 1,
                        "description": "Write kinetic energy formula",
                        "expression": "KE = ½mv²",
                        "latex": "KE = \\frac{1}{2}mv^2",
                        "points": 2,
                        "required": True
                    },
                    {
                        "stepNumber": 2,
                        "description": "Substitute values",
                        "expression": "KE = ½ × 2 × (5)²",
                        "latex": "KE = \\frac{1}{2} \\times 2 \\times 5^2",
                        "points": 3,
                        "required": True
                    },
                    {
                        "stepNumber": 3,
                        "description": "Calculate",
                        "expression": "KE = ½ × 2 × 25 = 25",
                        "latex": "KE = \\frac{1}{2} \\times 2 \\times 25 = 25",
                        "points": 3,
                        "required": True
                    },
                    {
                        "stepNumber": 4,
                        "description": "State answer with units",
                        "expression": "KE = 25 J",
                        "latex": "KE = 25 \\text{ J}",
                        "points": 2,
                        "required": True
                    }
                ],
                "finalAnswer": "25 J",
                "finalAnswerLatex": "25 \\text{ J}"
            },
            {
                "number": 3,
                "text": "A force of 50 N is applied to move an object 8 meters. Calculate the work done.",
                "points": 10,
                "goldSolutionSteps": [
                    {
                        "stepNumber": 1,
                        "description": "Write work formula",
                        "expression": "W = F × d",
                        "latex": "W = F \\times d",
                        "points": 2,
                        "required": True
                    },
                    {
                        "stepNumber": 2,
                        "description": "Substitute values",
                        "expression": "W = 50 N × 8 m",
                        "latex": "W = 50 \\times 8",
                        "points": 3,
                        "required": True
                    },
                    {
                        "stepNumber": 3,
                        "description": "Calculate",
                        "expression": "W = 400",
                        "latex": "W = 400",
                        "points": 3,
                        "required": True
                    },
                    {
                        "stepNumber": 4,
                        "description": "State answer with units",
                        "expression": "W = 400 J",
                        "latex": "W = 400 \\text{ J}",
                        "points": 2,
                        "required": True
                    }
                ],
                "finalAnswer": "400 J",
                "finalAnswerLatex": "400 \\text{ J}"
            },
            {
                "number": 4,
                "text": "An object is dropped from a height of 20 meters. Calculate its velocity just before hitting the ground. (Use g = 10 m/s²)",
                "points": 12,
                "goldSolutionSteps": [
                    {
                        "stepNumber": 1,
                        "description": "Identify given values",
                        "expression": "Initial velocity (u) = 0 m/s, Height (h) = 20 m, g = 10 m/s²",
                        "latex": "u = 0, h = 20 \\text{ m}, g = 10 \\text{ m/s}^2",
                        "points": 2,
                        "required": True
                    },
                    {
                        "stepNumber": 2,
                        "description": "Use kinematic equation",
                        "expression": "v² = u² + 2gh",
                        "latex": "v^2 = u^2 + 2gh",
                        "points": 3,
                        "required": True
                    },
                    {
                        "stepNumber": 3,
                        "description": "Substitute values",
                        "expression": "v² = 0² + 2(10)(20) = 0 + 400",
                        "latex": "v^2 = 0^2 + 2(10)(20) = 400",
                        "points": 3,
                        "required": True
                    },
                    {
                        "stepNumber": 4,
                        "description": "Solve for v",
                        "expression": "v = √400 = 20 m/s",
                        "latex": "v = \\sqrt{400} = 20 \\text{ m/s}",
                        "points": 4,
                        "required": True
                    }
                ],
                "finalAnswer": "20 m/s",
                "finalAnswerLatex": "20 \\text{ m/s}"
            },
            {
                "number": 5,
                "text": "Calculate the potential energy of a 3 kg object raised to a height of 5 meters. (Use g = 10 m/s²)",
                "points": 10,
                "goldSolutionSteps": [
                    {
                        "stepNumber": 1,
                        "description": "Write potential energy formula",
                        "expression": "PE = mgh",
                        "latex": "PE = mgh",
                        "points": 2,
                        "required": True
                    },
                    {
                        "stepNumber": 2,
                        "description": "Substitute values",
                        "expression": "PE = 3 × 10 × 5",
                        "latex": "PE = 3 \\times 10 \\times 5",
                        "points": 3,
                        "required": True
                    },
                    {
                        "stepNumber": 3,
                        "description": "Calculate",
                        "expression": "PE = 150",
                        "latex": "PE = 150",
                        "points": 3,
                        "required": True
                    },
                    {
                        "stepNumber": 4,
                        "description": "State answer with units",
                        "expression": "PE = 150 J",
                        "latex": "PE = 150 \\text{ J}",
                        "points": 2,
                        "required": True
                    }
                ],
                "finalAnswer": "150 J",
                "finalAnswerLatex": "150 \\text{ J}"
            },
            {
                "number": 6,
                "text": "State Newton's First Law of Motion and provide an example.",
                "points": 8,
                "goldSolutionSteps": [
                    {
                        "stepNumber": 1,
                        "description": "State the law",
                        "expression": "An object at rest stays at rest, and an object in motion stays in motion at constant velocity, unless acted upon by an unbalanced force",
                        "latex": "",
                        "points": 4,
                        "required": True
                    },
                    {
                        "stepNumber": 2,
                        "description": "Provide example",
                        "expression": "Example: A book on a table remains at rest until someone pushes it",
                        "latex": "",
                        "points": 2,
                        "required": True
                    },
                    {
                        "stepNumber": 3,
                        "description": "Additional example",
                        "expression": "A hockey puck sliding on ice continues moving until friction stops it",
                        "latex": "",
                        "points": 2,
                        "required": False
                    }
                ],
                "finalAnswer": "Objects maintain their state of motion unless acted upon by an unbalanced force. Example: A ball rolling on a frictionless surface continues rolling indefinitely.",
                "finalAnswerLatex": ""
            }
        ]
    }
}

def create_exam(token, course_id, exam_data):
    """Create an exam"""
    headers = {"Authorization": f"Bearer {token}"}
    
    exam_payload = {
        "title": exam_data["title"],
        "description": exam_data["description"],
        "courseId": course_id,
        "questions": exam_data["questions"]
    }
    
    response = requests.post(
        f"{API_BASE_URL}/exams",
        json=exam_payload,
        headers=headers
    )
    
    if response.status_code == 200:
        exam = response.json()
        total_points = sum(q["points"] for q in exam_data["questions"])
        print(f"  ✓ Created exam: {exam_data['title']} ({len(exam_data['questions'])} questions, {total_points} points)")
        return exam
    else:
        print(f"  ✗ Failed to create exam: {response.text}")
        return None

def main():
    print("Adding custom exams...")
    print("=" * 50)
    
    # Login
    print("Logging in...")
    token = login()
    print("✓ Logged in successfully\n")
    
    # Get courses
    print("Fetching courses...")
    courses = get_courses(token)
    print(f"✓ Found {len(courses)} courses\n")
    
    # Create exams
    created = 0
    failed = 0
    
    for exam_key, exam_data in EXAMS.items():
        print(f"Creating {exam_key.upper()} exam...")
        course_id = find_course_by_code(courses, exam_data["course_code_prefix"])
        
        if not course_id:
            print(f"  ✗ No course found with code prefix '{exam_data['course_code_prefix']}'")
            print(f"    Please create a course with code starting with '{exam_data['course_code_prefix']}' first")
            failed += 1
            continue
        
        exam = create_exam(token, course_id, exam_data)
        if exam:
            created += 1
        else:
            failed += 1
        print()
    
    print("=" * 50)
    print(f"Summary: {created} exams created, {failed} failed")
    
    if failed == 0:
        print("\n✓ All exams created successfully!")
    else:
        print(f"\n⚠ {failed} exam(s) failed. Check the errors above.")

if __name__ == "__main__":
    main()
