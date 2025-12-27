#!/bin/bash
cd "$(dirname "$0")"

echo "🚀 Starting Avvo Scraper..."
echo ""

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed."
    echo "   Please install Python 3 from https://www.python.org/"
    read -p "Press Enter to close..."
    exit 1
fi

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "❌ Error: pip3 is not installed."
    echo "   Please install pip3"
    read -p "Press Enter to close..."
    exit 1
fi

# Check and install dependencies
echo "📦 Checking dependencies..."
if ! python3 -c "import undetected_chromedriver" 2>/dev/null; then
    echo "📥 Installing required packages (this may take a minute)..."
    pip3 install -q -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "❌ Error: Failed to install dependencies."
        echo "   Try running: pip3 install -r requirements.txt"
        read -p "Press Enter to close..."
        exit 1
    fi
    echo "✅ Dependencies installed!"
else
    echo "✅ All dependencies are installed"
fi

echo ""
echo "▶️  Running scraper..."
echo ""

# Run the scraper
python3 avvo_scraper_direct_to_csv.py

echo ""
read -p "Press Enter to close..."

