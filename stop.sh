#!/bin/bash

# MathGrade - Stop Script (Reorganized Structure)
echo "🛑 Stopping MathGrade System..."
echo ""

# Check if PID files exist
if [ ! -f ".backend.pid" ] && [ ! -f ".frontend.pid" ]; then
    echo "⚠️  No running instances found"
    echo "   (PID files not found)"
    exit 0
fi

# Stop backend
if [ -f ".backend.pid" ]; then
    BACKEND_PID=$(cat .backend.pid)
    if ps -p $BACKEND_PID > /dev/null 2>&1; then
        kill $BACKEND_PID
        echo "✅ Backend stopped (PID: $BACKEND_PID)"
    else
        echo "⚠️  Backend process not found"
    fi
    rm .backend.pid
fi

# Stop frontend
if [ -f ".frontend.pid" ]; then
    FRONTEND_PID=$(cat .frontend.pid)
    if ps -p $FRONTEND_PID > /dev/null 2>&1; then
        kill $FRONTEND_PID
        echo "✅ Frontend stopped (PID: $FRONTEND_PID)"
    else
        echo "⚠️  Frontend process not found"
    fi
    rm .frontend.pid
fi

echo ""
echo "✅ MathGrade stopped successfully"
