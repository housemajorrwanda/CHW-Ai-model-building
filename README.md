# 🎓 MathGrade - AI-Powered Math Exam Grading System

A comprehensive web-based platform for automated grading of handwritten mathematical exam solutions with step-by-step analysis.

---

## 📁 Project Structure

```
grading-website/
├── backend/                      # 🐍 Python FastAPI Backend
│   ├── api.py                    # Main FastAPI application
│   ├── database.py               # Database configuration
│   ├── models.py                 # SQLAlchemy models
│   ├── schemas.py                # Pydantic schemas
│   ├── math_grader.py            # Step-by-step grading logic
│   ├── requirements.txt          # Python dependencies
│   ├── Dockerfile                # Backend containerization
│   ├── uploads/                  # Student submission storage
│   ├── easygrade.db              # SQLite database
│   │
│   ├── ocr/                      # OCR Processing Modules
│   │   ├── ocr_pipeline.py       # ✅ Active: Tesseract + EasyOCR
│   │   ├── trocr_processor.py    # Microsoft TrOCR (text)
│   │   ├── math_trocr_processor.py # Math-specialized TrOCR
│   │   ├── hybrid_processor.py   # Auto-switching OCR
│   │   ├── image_preprocessor.py
│   │   └── utils.py
│   │
│   ├── grading/                  # Grading Engine Components
│   │   ├── step.py
│   │   ├── matching_engine.py
│   │   ├── scoring_engine.py
│   │   ├── feedback_generator.py
│   │   └── gold_solution_manager.py
│   │
│   └── ml_models/                # Machine Learning Models
│       └── handwriting_ocr/      # TensorFlow-based OCR models
│           ├── src/              # Model source code
│           ├── models/           # Pre-trained weights
│           ├── notebooks/        # Research notebooks
│           └── README.md
│
├── frontend/                     # ⚛️ React TypeScript Frontend
│   ├── src/
│   │   ├── components/           # Reusable UI components
│   │   ├── pages/                # Application pages
│   │   ├── api/                  # API client
│   │   ├── contexts/             # React contexts
│   │   ├── lib/                  # Utilities
│   │   └── types/                # TypeScript types
│   ├── public/                   # Static assets
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   └── index.html
│
├── start.sh                      # 🚀 Start both services
├── stop.sh                       # 🛑 Stop both services
└── README.md                     # This file
```

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.11+** (for backend)
- **Node.js 18+** (for frontend)
- **Tesseract OCR** (optional, for better OCR)

### Installation

1. **Clone the repository**:
   ```bash
   cd "grading website"
   ```

2. **Start the application**:
   ```bash
   ./start.sh
   ```

   This will:
   - Create virtual environment and install Python dependencies
   - Install frontend dependencies
   - Start backend on http://localhost:8000
   - Start frontend on http://localhost:8080

3. **Stop the application**:
   ```bash
   ./stop.sh
   ```

### Manual Setup

If you prefer to run services separately:

#### Backend
```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend
```bash
cd frontend
npm install
npm run dev
```

---

## 🔑 Default Credentials

**Professor Account:**
- Email: `professor@university.edu`
- Password: `password`

**Student Account:**
- Email: `student@university.edu`
- Password: `password`

---

## 📊 Features

### For Professors
- ✅ Create and manage courses
- ✅ Design exams with step-by-step solutions
- ✅ Upload gold solutions for automated grading
- ✅ Review and grade student submissions
- ✅ Provide detailed feedback
- ✅ View analytics and statistics

### For Students
- ✅ Browse and enroll in courses
- ✅ View available exams
- ✅ Submit handwritten solutions (photo/PDF)
- ✅ Receive instant automated grading
- ✅ View detailed step-by-step feedback
- ✅ Track progress and grades

### OCR & Grading Engine
- ✅ **Tesseract + EasyOCR** (currently active)
- 🔬 **TrOCR models** (available for research)
- 🔬 **Math-specialized OCR** (available for research)
- ✅ Step-by-step mathematical analysis
- ✅ Symbolic math validation (SymPy)
- ✅ Partial credit assignment
- ✅ Detailed feedback generation

---

## 🔧 Technology Stack

### Backend
- **Framework**: FastAPI (Python)
- **Database**: SQLAlchemy + SQLite/PostgreSQL
- **OCR**: Tesseract, EasyOCR, TrOCR (Transformers)
- **Math Engine**: SymPy
- **Image Processing**: OpenCV, Pillow, pdf2image
- **Authentication**: JWT (python-jose)

### Frontend
- **Framework**: React 18 + TypeScript
- **Build Tool**: Vite
- **UI Library**: shadcn/ui + Radix UI
- **Styling**: Tailwind CSS
- **Routing**: React Router v6
- **Forms**: React Hook Form + Zod
- **State**: React Context + TanStack Query

---

## 📚 API Documentation

Once the backend is running, visit:
- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 🧪 Development

### Backend Development
```bash
cd backend
source venv/bin/activate
python -m uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Development
```bash
cd frontend
npm run dev
```

### Running Tests
```bash
# Backend
cd backend
pytest

# Frontend
cd frontend
npm run test
```

---

## 📦 Deployment

### Using Docker

**Backend:**
```bash
cd backend
docker build -t mathgrade-backend .
docker run -p 8000:8000 mathgrade-backend
```

**Frontend:**
```bash
cd frontend
npm run build
# Serve the dist/ folder with your preferred web server
```

### Cloud Platforms
- **Backend**: Railway, Heroku, AWS EC2, Google Cloud Run
- **Frontend**: Vercel, Netlify, AWS S3 + CloudFront

Configuration files included:
- `backend/Procfile` (Heroku/Railway)
- `backend/railway.json` (Railway)
- `backend/nixpacks.toml` (Railway/Nixpacks)
- `frontend/vercel.json` (Vercel)

---

## 🤖 OCR Models

### Currently Active
**Tesseract + EasyOCR** (`backend/ocr/ocr_pipeline.py`)
- Lightweight and fast
- Good for printed and clear handwriting
- Multi-language support

### Available for Research/Integration
1. **TrOCR** (`backend/ocr/trocr_processor.py`)
   - Microsoft's transformer-based OCR
   - Better for complex handwriting

2. **Math TrOCR** (`backend/ocr/math_trocr_processor.py`)
   - Specialized for mathematical notation
   - LaTeX output support

3. **Handwriting OCR Models** (`backend/ml_models/handwriting_ocr/`)
   - TensorFlow-based CNN/RNN models
   - Character segmentation and classification
   - Research-grade implementation

To switch OCR implementations, modify the import in `backend/api.py`.

---

## 🐛 Troubleshooting

### Backend Issues
- **Database locked**: Stop any running instances with `./stop.sh`
- **Port 8000 in use**: Change port in `start.sh` or kill the process
- **Missing Tesseract**: Install via `brew install tesseract` (macOS) or `apt-get install tesseract-ocr` (Linux)

### Frontend Issues
- **Port 8080 in use**: Change port in `frontend/vite.config.ts`
- **CORS errors**: Ensure backend is running and CORS is configured in `backend/api.py`

### OCR Issues
- **Poor recognition**: Ensure images are clear, well-lit, and high-resolution
- **EasyOCR slow**: First run downloads models (~100MB), subsequent runs are faster

---

## 📝 License

MIT License - See individual component licenses for details.

---

## 👥 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

## 📞 Support

For issues and questions:
- Check the API documentation at http://localhost:8000/docs
- Review logs in `backend.log` and `frontend.log`
- Check the GitHub issues page

---

**Built with ❤️ for better education**
