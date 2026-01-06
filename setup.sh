#!/bin/bash

# Telegram Bot Setup Script
# This script helps you set up the bot quickly

echo "=================================="
echo "Telegram Bot Setup Script"
echo "=================================="
echo ""

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "✓ Python $PYTHON_VERSION found"

# Create virtual environment
echo ""
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "✓ Dependencies installed successfully!"

# Check if config.py needs setup
if grep -q "YOUR_BOT_TOKEN_HERE" config.py; then
    echo ""
    echo "=================================="
    echo "Configuration Setup"
    echo "=================================="
    echo ""
    echo "Please provide the following information:"
    echo ""
    
    # Get bot token
    read -p "Enter your Bot Token (from @BotFather): " BOT_TOKEN
    
    # Get bot URL
    read -p "Enter your domain URL (e.g., https://yourdomain.com/): " BOT_URL
    
    # Get DB channel
    read -p "Enter your private channel ID (e.g., -1001234567890): " DB_CHANNEL
    
    # Get admin ID
    read -p "Enter your Telegram user ID: " ADMIN_ID
    
    # Update config.py
    echo ""
    echo "Updating config.py..."
    
    sed -i "s|YOUR_BOT_TOKEN_HERE|$BOT_TOKEN|g" config.py
    sed -i "s|https://yourdomain.com/|$BOT_URL|g" config.py
    sed -i "s|-1001234567890|$DB_CHANNEL|g" config.py
    sed -i "s|123456789|$ADMIN_ID|g" config.py
    
    echo "✓ Configuration updated!"
fi

# Initialize database
echo ""
echo "Initializing database..."
python3 -c "from api import db; print('✓ Database initialized!')"

echo ""
echo "=================================="
echo "Setup Complete!"
echo "=================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Set up webhook:"
echo "   curl -X POST \"https://api.telegram.org/bot<YOUR_TOKEN>/setWebhook?url=$BOT_URL/webhook\""
echo ""
echo "2. Start the bot:"
echo "   For development: python api.py"
echo "   For production: gunicorn -w 4 -b 0.0.0.0:5000 api:app"
echo ""
echo "3. Test your bot by sending /start to it in Telegram"
echo ""
echo "For more information, see README.md"
echo ""
