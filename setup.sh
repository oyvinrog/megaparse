#!/bin/bash
# Setup script for Web Table Parser

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

echo ""
echo "Setup complete! You can now run the application with:"
echo "source venv/bin/activate  # If not already activated"
echo "python main.py"
echo ""
echo "To deactivate the virtual environment when done, type:"
echo "deactivate" 