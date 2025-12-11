#!/bin/bash
# Social Media Manager - Desktop GUI Launcher
# This script launches the PyQt6 desktop application

cd "$(dirname "$0")"

# Activate virtual environment
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Set PYTHONPATH to include the src directory
export PYTHONPATH="${PWD}/src:$PYTHONPATH"

# Launch Desktop GUI
echo "🖥️  Launching Social Media Manager Desktop GUI..."
python -m social_media_manager.gui.main "$@"
