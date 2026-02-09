# MathGrade - Math Exam Grading System

A web platform for grading handwritten math exam solutions with step-by-step analysis.

## Project Structure

```
grading-website/
├── backend/                 # Python FastAPI backend
│   ├── api.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── math_grader.py
│   ├── requirements.txt
│   ├── ocr/                 # OCR processing modules
│   ├── grading/             # Grading engine
│   └── ml_models/           # ML models
├── frontend/                # React TypeScript frontend
│   ├── src/
│   └── package.json
├── start.sh
└── stop.sh
```

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Tesseract OCR (optional)

### Installation

1. Navigate to the project directory:
   ```bash
   cd "grading website"
   ```

2. Start everything:
   ```bash
   ./start.sh
   ```
   This starts the backend on http://localhost:8000 and frontend on http://localhost:8080

3. Stop everything:
   ```bash
   ./stop.sh
   ```

### Manual Setup

**Backend:**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## Default Credentials

**Professor:**
- Email: `professor@university.edu`
- Password: `password`

**Student:**
- Email: `student@university.edu`
- Password: `password`

## Features

**For Professors:**
- Create and manage courses
- Design exams with step-by-step solutions
- Upload gold solutions for automated grading
- Review student submissions
- View analytics

**For Students:**
- Browse and enroll in courses
- Submit handwritten solutions (photo/PDF)
- Get automated grading with feedback
- Track progress and grades

**OCR & Grading:**
- Tesseract + EasyOCR (currently active)
- TrOCR models available
- Step-by-step mathematical analysis
- Symbolic math validation with SymPy
- Partial credit assignment

## Tech Stack

**Backend:**
- FastAPI (Python)
- SQLAlchemy + SQLite/PostgreSQL
- OCR: Tesseract, EasyOCR, TrOCR
- Math Engine: SymPy
- Image Processing: OpenCV, Pillow

**Frontend:**
- React 18 + TypeScript
- Vite
- Tailwind CSS
- React Router

## API Documentation

Once running, visit http://localhost:8000/docs for interactive API docs.

## Development

**Backend:**
```bash
cd backend
source venv/bin/activate
python -m uvicorn api:app --reload
```

**Frontend:**
```bash
cd frontend
npm run dev
```

## OCR Models

Currently using Tesseract + EasyOCR. TrOCR and math-specialized models are available in the codebase but not active by default. To switch, modify the import in `backend/api.py`.

## Troubleshooting

- Database locked: Stop running instances with `./stop.sh`
- Port conflicts: Change ports in `start.sh` or config files
- Missing Tesseract: Install via `brew install tesseract` (macOS) or `apt-get install tesseract-ocr` (Linux)
- CORS errors: Make sure backend is running and CORS is configured
- Poor OCR: Use clear, well-lit, high-resolution images

## License

MIT License
