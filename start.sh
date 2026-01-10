#!/bin/bash

# MathGrade - Startup Script (Reorganized Structure)
echo "🎓 Starting MathGrade System..."
echo ""

# Check if we're in the right directory
if [ ! -d "backend" ] || [ ! -d "frontend" ]; then
    echo "❌ Error: Please run this script from the project root directory"
    echo "   Expected directories: backend/ and frontend/"
    exit 1
fi

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check dependencies
echo "📦 Checking dependencies..."

if ! command_exists python3; then
    echo "❌ Python 3 is not installed. Please install Python 3.11 or higher."
    exit 1
fi

if ! command_exists node; then
    echo "❌ Node.js is not installed. Please install Node.js 18 or higher."
    exit 1
fi

echo "✅ Dependencies check passed"
echo ""

# Start backend
echo "🚀 Starting Backend (FastAPI)..."
cd backend

# Check if venv exists, if not suggest creating one
if [ ! -d "venv" ]; then
    echo "⚠️  No virtual environment found. Creating one..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Start backend in background
nohup python -m uvicorn api:app --reload --host 0.0.0.0 --port 8000 > ../backend.log 2>&1 &
BACKEND_PID=$!
echo "✅ Backend started on http://localhost:8000 (PID: $BACKEND_PID)"
echo "   Logs: backend.log"
echo ""

# Go back to root
cd ..

# Start frontend
echo "🚀 Starting Frontend (React + Vite)..."
cd frontend

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "⚠️  Installing frontend dependencies..."
    npm install
fi

# Start frontend in background
nohup npm run dev > ../frontend.log 2>&1 &
FRONTEND_PID=$!
echo "✅ Frontend started on http://localhost:8080 (PID: $FRONTEND_PID)"
echo "   Logs: frontend.log"
echo ""

# Go back to root
cd ..

# Save PIDs for later
echo $BACKEND_PID > .backend.pid
echo $FRONTEND_PID > .frontend.pid

echo "✅ MathGrade is running!"
echo ""
echo "📍 URLs:"
echo "   Frontend: http://localhost:8080"
echo "   Backend API: http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
echo ""
echo "🔑 Demo Login:"
echo "   Professor: professor@university.edu / password"
echo "   Student: student@university.edu / password"
echo ""
echo "📝 Logs:"
echo "   Backend: tail -f backend.log"
echo "   Frontend: tail -f frontend.log"
echo ""
echo "🛑 To stop: ./stop.sh"
echo ""
echo "🎉 Happy grading!"
