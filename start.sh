#!/bin/bash

# Database Health Check Application Startup Script

echo "🏥 Starting Database Health Check Application..."
echo "================================================"

# Check if Python is available
if ! command -v python &> /dev/null; then
    echo "❌ Python is not installed or not in PATH"
    exit 1
fi

# Check if required packages are installed
echo "📦 Checking dependencies..."
python -c "import flask, flask_cors, psutil" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "📥 Installing required packages..."
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "❌ Failed to install dependencies"
        exit 1
    fi
fi

# Set default environment variables if not set
export DATABASE_PATH=${DATABASE_PATH:-"/tmp/health_check.db"}
export CHECK_INTERVAL=${CHECK_INTERVAL:-"30"}
export MAX_HISTORY_DAYS=${MAX_HISTORY_DAYS:-"7"}

echo "⚙️  Configuration:"
echo "   Database Path: $DATABASE_PATH"
echo "   Check Interval: ${CHECK_INTERVAL}s"
echo "   History Retention: ${MAX_HISTORY_DAYS} days"
echo ""

# Start the application
echo "🚀 Starting application on http://localhost:8080"
echo "   Press Ctrl+C to stop"
echo ""

python app.py