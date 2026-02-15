#!/bin/bash
cd "$(dirname "$0")/app"
uvicorn api:app --reload --port 8000
