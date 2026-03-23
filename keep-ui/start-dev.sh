#!/bin/bash
# Frontend development server startup script

cd "$(dirname "$0")"

echo "Starting Keep UI development server..."
echo "Frontend will be available at: http://localhost:3000"
echo ""

npm run dev:webpack
