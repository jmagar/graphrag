#!/bin/bash
# Kill processes on ports 3000, 3001, and 8000

echo "🔍 Checking for processes on ports 3000, 3001, 8000..."

for port in 3000 3001 8000; do
    pid=$(lsof -ti :$port 2>/dev/null)
    if [ -n "$pid" ]; then
        echo "  ⚠️  Port $port in use by PID $pid - killing..."
        kill -9 $pid 2>/dev/null
        echo "  ✅ Port $port freed"
    else
        echo "  ✓  Port $port is free"
    fi
done

echo ""
echo "✅ All ports cleared! You can now run: npm run dev"
