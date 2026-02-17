import re
from typing import List, Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class ExamParser:
    def __init__(self):
        self.question_patterns = [
            r'(?:question|q)\s*[:\.]?\s*(\d+)',
            r'^\s*(\d+)\s*[\.\)]\s*',
            r'problem\s*(\d+)'
        ]
        
        self.gold_solution_markers = [
            'gold solution:', 'model answer:', 'solution:', 
            'expected answer:', 'correct answer:', 'answer key:'
        ]
        
        self.step_markers = [
            'step', 'solution step', 'working'
        ]
    
    def parse_exam(self, text: str) -> Dict:
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        title = self._extract_title(lines)
        description = self._extract_description(lines)
        questions = self._extract_questions(lines)
        
        total_points = sum(q['points'] for q in questions)
        
        return {
            'title': title,
            'description': description,
            'questions': questions,
            'total_points': total_points
        }
    
    def _extract_title(self, lines: List[str]) -> str:
        for line in lines[:5]:
            if any(word in line.lower() for word in ['exam', 'test', 'quiz', 'assessment']):
                return line
        return lines[0] if lines else "Imported Exam"
    
    def _extract_description(self, lines: List[str]) -> str:
        desc_lines = []
        in_desc = False
        
        for line in lines:
            lower = line.lower()
            if 'description:' in lower or 'instructions:' in lower:
                in_desc = True
                desc_lines.append(line.split(':', 1)[1].strip() if ':' in line else '')
            elif in_desc and self._is_question_header(line):
                break
            elif in_desc:
                desc_lines.append(line)
        
        return ' '.join(desc_lines).strip() or "Imported exam"
    
    def _is_question_header(self, line: str) -> bool:
        lower = line.lower()
        for pattern in self.question_patterns:
            if re.search(pattern, lower, re.IGNORECASE):
                return True
        return False
    
    def _extract_questions(self, lines: List[str]) -> List[Dict]:
        questions = []
        current_question = None
        current_section = 'text'
        current_steps = []
        
        i = 0
        while i < len(lines):
            line = lines[i]
            lower = line.lower()
            
            question_match = self._find_question_number(line)
            if question_match:
                if current_question:
                    if current_steps:
                        current_question['gold_solution_steps'] = current_steps
                    questions.append(current_question)
                
                current_question = {
                    'number': question_match,
                    'text': '',
                    'points': 1,
                    'gold_solution_steps': []
                }
                current_section = 'text'
                current_steps = []
                
                text_part = re.sub(r'(?:question|q)\s*[:\.]?\s*\d+', '', line, flags=re.IGNORECASE).strip()
                text_part = re.sub(r'^\s*\d+\s*[\.\)]\s*', '', text_part).strip()
                text_part = re.sub(r'^[:\s]+', '', text_part).strip()
                
                points_match = re.search(r'\[(\d+)\s*(?:points?|pts?|marks?)\]', text_part, re.IGNORECASE)
                if points_match:
                    current_question['points'] = int(points_match.group(1))
                    text_part = re.sub(r'\[\d+\s*(?:points?|pts?|marks?)\]', '', text_part, flags=re.IGNORECASE).strip()
                
                if text_part:
                    current_question['text'] = text_part
            
            elif current_question:
                if any(marker in lower for marker in self.gold_solution_markers):
                    current_section = 'solution'
                    gold_text = re.split('|'.join(self.gold_solution_markers), line, flags=re.IGNORECASE)[-1].strip()
                    if gold_text:
                        step = self._parse_step(gold_text, len(current_steps) + 1)
                        current_steps.append(step)
                
                elif current_section == 'solution':
                    if self._is_step_line(line):
                        step = self._parse_step(line, len(current_steps) + 1)
                        current_steps.append(step)
                    elif line and not self._is_question_header(line):
                        if current_steps:
                            current_steps[-1]['expression'] += ' ' + line
                        else:
                            step = self._parse_step(line, 1)
                            current_steps.append(step)
                
                elif current_section == 'text':
                    points_match = re.search(r'\[(\d+)\s*(?:points?|pts?|marks?)\]', lower)
                    if points_match:
                        current_question['points'] = int(points_match.group(1))
                        line = re.sub(r'\[\d+\s*(?:points?|pts?|marks?)\]', '', line, flags=re.IGNORECASE).strip()
                    
                    if line:
                        current_question['text'] += ' ' + line
            
            i += 1
        
        if current_question:
            if current_steps:
                current_question['gold_solution_steps'] = current_steps
            questions.append(current_question)
        
        for q in questions:
            q['text'] = q['text'].strip()
            if not q['gold_solution_steps']:
                q['gold_solution_steps'] = [{
                    'step_number': 1,
                    'description': 'Solution',
                    'expression': '',
                    'points': q['points'],
                    'required': True
                }]
            else:
                total_step_points = sum(step['points'] for step in q['gold_solution_steps'])
                if total_step_points > q['points']:
                    q['points'] = total_step_points
                elif total_step_points < q['points']:
                    points_per_step = q['points'] // len(q['gold_solution_steps'])
                    remainder = q['points'] % len(q['gold_solution_steps'])
                    for i, step in enumerate(q['gold_solution_steps']):
                        step['points'] = points_per_step + (1 if i < remainder else 0)
        
        return questions
    
    def _find_question_number(self, line: str) -> Optional[int]:
        for pattern in self.question_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                return int(match.group(1))
        return None
    
    def _is_step_line(self, line: str) -> bool:
        lower = line.lower()
        return any(marker in lower for marker in self.step_markers) or \
               re.match(r'^\s*\d+[\.\)]\s*', line) or \
               line.startswith('=')
    
    def _parse_step(self, line: str, step_number: int) -> Dict:
        clean_line = re.sub(r'^(?:step\s*\d*[:\.]?\s*)', '', line, flags=re.IGNORECASE).strip()
        clean_line = re.sub(r'^\s*\d+[\.\)]\s*', '', clean_line).strip()
        
        points = 1
        points_match = re.search(r'\[(\d+)\s*(?:points?|pts?)\]', clean_line, re.IGNORECASE)
        if points_match:
            points = int(points_match.group(1))
            clean_line = re.sub(r'\[\d+\s*(?:points?|pts?)\]', '', clean_line, flags=re.IGNORECASE).strip()
        
        return {
            'step_number': step_number,
            'description': f'Step {step_number}',
            'expression': clean_line,
            'points': points,
            'required': step_number <= 3
        }
