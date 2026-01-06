# Telegram Bot - Python Version

A comprehensive Telegram bot for e-commerce with product management, payments, and admin features. Converted from PHP to Python for improved performance and better UI responsiveness.

## Features

### For Users
- 🛍️ Browse products with web app interface
- 💳 Secure payment integration (Razorpay)
- 📥 Digital product downloads
- 🧾 Automatic invoice generation
- 📜 Purchase history
- ✉️ Contact admin support

### For Admins
- 📦 Product management (add, edit, delete, hide/show)
- 👥 User management (block, unblock, search)
- 📊 Statistics dashboard
- 📢 Broadcast messages
- 💬 Message management
- 🛠️ Maintenance mode
- 💰 Price & discount management
- 📊 Stock management
- 🚀 Web dashboard interface

## Requirements

- Python 3.8+
- SQLite3 (included with Python)
- Telegram Bot Token
- Private Telegram Channel (for file storage)
- Web server (for webhook)

## Installation

### 1. Clone or Download

```bash
git clone <your-repo-url>
cd telegram-bot-python
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure the Bot

Edit `config.py` with your credentials:

```python
# Bot Configuration
BOT_TOKEN = "your_bot_token_from_botfather"
BOT_URL = "https://yourdomain.com/"
DB_CHANNEL = -1001234567890  # Your private channel ID

# Admin IDs
ADMIN_IDS = [123456789]  # Your Telegram user ID

# Database
DATABASE_PATH = "bot_database.db"
```

### 4. Get Your Credentials

#### Bot Token
1. Open Telegram and search for `@BotFather`
2. Send `/newbot` and follow instructions
3. Copy the bot token

#### Private Channel for Files
1. Create a private Telegram channel
2. Add your bot as administrator
3. Get the channel ID (use `@userinfobot` or similar)

#### Your User ID
1. Search for `@userinfobot` in Telegram
2. Start the bot to get your user ID
3. Add it to ADMIN_IDS in config.py

### 5. Set Up Webhook

#### Option A: Using ngrok (for testing)

```bash
# Install ngrok
# Download from https://ngrok.com/

# Start ngrok
ngrok http 5000

# Copy the https URL and set webhook
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook?url=https://your-ngrok-url.ngrok.io/webhook"
```

#### Option B: Production Server

```bash
# Set webhook to your domain
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook?url=https://yourdomain.com/webhook"
```

### 6. Run the Bot

#### Development Mode

```bash
python api.py
```

#### Production Mode (with gunicorn)

```bash
gunicorn -w 4 -b 0.0.0.0:5000 api:app
```

#### Using systemd (recommended for production)

Create `/etc/systemd/system/telegram-bot.service`:

```ini
[Unit]
Description=Telegram Bot Service
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/bot
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/gunicorn -w 4 -b 0.0.0.0:5000 api:app
Restart=always

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl start telegram-bot
sudo systemctl enable telegram-bot
```

## Usage

### User Commands
- `/start` - Start the bot and show product list
- `/cancel` - Cancel current operation

### Admin Commands
- `/start` - Show admin panel
- `/admin` - Access admin panel
- `/cancel` - Cancel current operation

### Admin Features

1. **Product Management**
   - Add new products (digital or subscription)
   - Edit product details (price, stock, description)
   - Set time-limited discounts
   - Hide/show products from users
   - Upload files for digital products

2. **User Management**
   - View all users with pagination
   - Search users by ID or username
   - Block/unblock users
   - Send direct messages to users

3. **Statistics**
   - Total users count
   - Total products
   - Total purchases
   - Total revenue

4. **Broadcasting**
   - Send messages to all active users
   - Support for text and photo messages
   - Progress tracking

5. **Maintenance Mode**
   - Temporarily disable bot for non-admins
   - Useful during updates

## File Structure

```
telegram-bot-python/
├── api.py                 # Main bot application
├── config.py             # Configuration file
├── requirements.txt      # Python dependencies
├── README.md            # This file
├── bot_database.db      # SQLite database (created automatically)
├── hidden_products.json # Hidden products list (created automatically)
└── maintenance.lock     # Maintenance mode flag (created when enabled)
```

## Database Schema

### Tables

1. **tg_users**
   - user_id (PRIMARY KEY)
   - username
   - first_name
   - is_blocked
   - joined_at

2. **tg_products**
   - id (PRIMARY KEY)
   - title
   - description
   - price
   - type (digital/subscription)
   - file_ids (JSON)
   - stock
   - header_message
   - footer_message
   - discount_price
   - discount_until
   - created_at

3. **tg_purchases**
   - id (PRIMARY KEY)
   - user_id
   - product_id
   - amount
   - status
   - access_granted
   - created_at

4. **tg_messages**
   - id (PRIMARY KEY)
   - user_id
   - message
   - is_admin
   - created_at

## Features Comparison (PHP vs Python)

| Feature | PHP Version | Python Version |
|---------|-------------|----------------|
| Performance | Good | **Excellent** |
| Async Support | Limited | **Full** |
| Code Readability | Good | **Excellent** |
| Error Handling | Basic | **Robust** |
| Logging | Basic | **Comprehensive** |
| Type Hints | No | **Yes** |
| State Management | File-based | **File-based** (same) |
| Database | PDO | **SQLite3** |
| Memory Usage | Higher | **Lower** |

## Troubleshooting

### Bot Not Responding
1. Check if webhook is set correctly
2. Verify bot token in config.py
3. Check server logs: `tail -f /var/log/syslog`
4. Ensure bot is running: `systemctl status telegram-bot`

### Database Errors
1. Check file permissions: `chmod 644 bot_database.db`
2. Ensure directory is writable
3. Verify DATABASE_PATH in config.py

### File Upload Issues
1. Verify bot is admin in DB_CHANNEL
2. Check DB_CHANNEL ID is correct (negative number)
3. Ensure channel is private

### Webhook Issues
1. Check webhook status:
   ```bash
   curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"
   ```
2. Delete and reset webhook:
   ```bash
   curl -X POST "https://api.telegram.org/bot<TOKEN>/deleteWebhook"
   curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook?url=<YOUR_URL>/webhook"
   ```

## Security Considerations

1. **Never commit config.py with real credentials**
2. Use environment variables for sensitive data
3. Enable HTTPS for webhook
4. Regularly update dependencies
5. Set proper file permissions (644 for files, 755 for directories)
6. Use firewall to restrict access
7. Enable rate limiting in production

## Production Deployment

### Using Nginx

Create `/etc/nginx/sites-available/telegram-bot`:

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

Enable and restart:

```bash
sudo ln -s /etc/nginx/sites-available/telegram-bot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### SSL Certificate (Let's Encrypt)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

## Monitoring

### Check Bot Status

```bash
# Check if bot is running
systemctl status telegram-bot

# View logs
journalctl -u telegram-bot -f

# Check webhook info
curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"
```

### Health Check

```bash
# Check health endpoint
curl http://localhost:5000/health
```

## Backup

### Database Backup

```bash
# Create backup
cp bot_database.db bot_database_backup_$(date +%Y%m%d).db

# Restore backup
cp bot_database_backup_20240115.db bot_database.db
```

### Automated Backup (cron)

Add to crontab (`crontab -e`):

```bash
# Backup database daily at 2 AM
0 2 * * * cp /path/to/bot_database.db /path/to/backups/bot_database_$(date +\%Y\%m\%d).db

# Delete backups older than 30 days
0 3 * * * find /path/to/backups -name "bot_database_*.db" -mtime +30 -delete
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For issues and questions:
- Create an issue on GitHub
- Contact: your-email@example.com

## Changelog

### Version 2.0.0 (Python)
- Complete rewrite in Python
- Improved performance and response time
- Better error handling
- Comprehensive logging
- Type hints for better code quality
- Async support ready
- Better state management
- Enhanced security

### Version 1.0.0 (PHP)
- Initial release
- Basic product management
- User management
- Payment integration
- Invoice generation

## Credits

- Original PHP version: [Your Name]
- Python conversion: [Your Name]
- Powered by: [Anthropic Claude](https://www.anthropic.com)
