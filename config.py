"""
Configuration file for Telegram Bot
Replace these values with your actual credentials
"""

# Bot Configuration
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # Get from @BotFather
BOT_URL = "https://yourdomain.com/"  # Your domain URL with trailing slash
DB_CHANNEL = -1001234567890  # Your private channel ID for storing files
BOT_ENABLED = True  # Set to False to disable bot

# Database Configuration
DATABASE_PATH = "bot_database.db"  # SQLite database file path
TABLE_PREFIX = "tg_"  # Prefix for database tables

# Admin Configuration
ADMIN_IDS = [123456789, 987654321]  # List of admin user IDs

# Feature Flags
DISABLE_FORWARDING = True  # Protect content from forwarding

# Razorpay Configuration (if using payment gateway)
RAZORPAY_KEY_ID = "YOUR_RAZORPAY_KEY_ID"
RAZORPAY_KEY_SECRET = "YOUR_RAZORPAY_KEY_SECRET"
