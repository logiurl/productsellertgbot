# Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Prerequisites
- Python 3.8+ installed
- Telegram Bot Token (from @BotFather)
- A server or local machine

### Step 1: Download and Setup (2 minutes)

```bash
# Clone the repository
git clone <your-repo-url>
cd telegram-bot-python

# Run setup script
chmod +x setup.sh
./setup.sh
```

The setup script will:
- Create a virtual environment
- Install all dependencies
- Guide you through configuration

### Step 2: Get Your Credentials (1 minute)

#### Bot Token
1. Open Telegram, search for `@BotFather`
2. Send `/newbot` and follow instructions
3. Copy the bot token

#### Private Channel
1. Create a new private channel in Telegram
2. Add your bot as administrator
3. Forward a message from the channel to `@userinfobot` to get the channel ID

#### Your User ID
1. Search for `@userinfobot` in Telegram
2. Send any message to get your user ID

### Step 3: Configure (1 minute)

Edit `config.py`:

```python
BOT_TOKEN = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"  # Your bot token
BOT_URL = "https://yourdomain.com/"                  # Your domain
DB_CHANNEL = -1001234567890                          # Channel ID
ADMIN_IDS = [123456789]                              # Your user ID
```

### Step 4: Set Webhook (30 seconds)

```bash
# Replace <YOUR_TOKEN> with your actual bot token
# Replace <YOUR_URL> with your domain

curl -X POST "https://api.telegram.org/bot<YOUR_TOKEN>/setWebhook?url=<YOUR_URL>/webhook"
```

### Step 5: Start the Bot (30 seconds)

#### For Testing (Local)

```bash
# Activate virtual environment
source venv/bin/activate

# Run the bot
python api.py
```

#### For Production

```bash
# Using gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 api:app

# OR using Docker
docker-compose up -d
```

### Step 6: Test It! (30 seconds)

1. Open Telegram
2. Find your bot
3. Send `/start`
4. You should see the product list!

## 🎯 Common Use Cases

### Use Case 1: Selling Digital Products

1. **Add a product**
   - Send `/admin` in bot
   - Click "📦 Manage Products"
   - Click "➕ Add Product"
   - Follow the wizard

2. **Upload files**
   - During product creation
   - Send files when prompted
   - Type `/done` when finished

3. **Set price and stock**
   - Enter price in rupees
   - Enter stock (-1 for unlimited)

4. **Test purchase**
   - Switch to user mode
   - Click on product
   - Click "💳 Buy Now"

### Use Case 2: Subscription Service

1. **Create subscription product**
   - Choose "🔄 Subscription" as type
   - Set monthly/yearly price
   - Add description with benefits

2. **Grant access manually**
   - User purchases subscription
   - Go to admin panel
   - Find purchase
   - Click "Send Access"
   - Enter access instructions

3. **Send invoice**
   - Invoice generated automatically
   - User receives it via bot

### Use Case 3: Limited Time Sale

1. **Set a discount**
   - Edit product in admin panel
   - Click "🎉 Set Discount"
   - Format: `99|2024-12-31 23:59`
   - 99 is discounted price
   - Date is when discount ends

2. **Announce sale**
   - Use broadcast feature
   - Send message to all users
   - Include product link

## 🔧 Quick Fixes

### Bot Not Responding?

```bash
# Check webhook status
curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"

# Reset webhook
curl -X POST "https://api.telegram.org/bot<TOKEN>/deleteWebhook"
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook?url=<URL>/webhook"

# Check if bot is running
ps aux | grep api.py
# OR for systemd
systemctl status telegram-bot
```

### Database Issues?

```bash
# Check database file exists
ls -la bot_database.db

# Fix permissions
chmod 644 bot_database.db

# Recreate database
rm bot_database.db
python3 -c "from api import db"
```

### Can't Upload Files?

1. Check bot is admin in channel
2. Verify channel ID is correct (must be negative)
3. Try forwarding a message to the channel manually

## 📱 Mobile Setup (Using Termux on Android)

```bash
# Install required packages
pkg install python git

# Clone and setup
git clone <repo-url>
cd telegram-bot-python
./setup.sh

# Run the bot
python api.py
```

## 🌐 Using ngrok for Testing

```bash
# Install ngrok
# Download from https://ngrok.com/

# Start ngrok tunnel
ngrok http 5000

# Copy the https URL (e.g., https://abc123.ngrok.io)
# Set webhook
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://abc123.ngrok.io/webhook"

# Start bot
python api.py
```

## 💡 Pro Tips

1. **Keep bot running 24/7**
   - Use systemd service (see `telegram-bot.service`)
   - Or use Docker (see `docker-compose.yml`)
   - Or use screen/tmux

2. **Enable HTTPS**
   - Get free SSL with Let's Encrypt
   - Telegram requires HTTPS for webhooks
   - Use nginx as reverse proxy

3. **Backup regularly**
   - Database: `cp bot_database.db backup.db`
   - Set up automated daily backups
   - Keep at least 7 days of backups

4. **Monitor performance**
   - Check logs: `tail -f /var/log/telegram-bot/error.log`
   - Monitor webhook: Check `/health` endpoint
   - Set up alerts for errors

5. **Test before production**
   - Create a test bot
   - Test all features
   - Then deploy to production bot

## 🆘 Getting Help

- **Error in logs?** Check `/var/log/telegram-bot/error.log`
- **Webhook issues?** Use `getWebhookInfo` API
- **Database locked?** Restart the bot
- **Memory issues?** Increase resource limits in service file

## 📚 Next Steps

- Read full [README.md](README.md) for detailed documentation
- Set up monitoring and alerts
- Configure automated backups
- Set up SSL certificate
- Customize the bot for your needs

## ⚡ Performance Tips

1. Use production server (gunicorn) instead of development server
2. Enable gzip compression in nginx
3. Set up CDN for static files
4. Use connection pooling for database
5. Enable caching where appropriate

Happy bot building! 🤖
