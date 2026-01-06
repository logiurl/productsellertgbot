#!/usr/bin/env python3
"""
Telegram Bot API - Python Version
Converted from PHP to Python for improved UI and faster response
"""

import os
import sys
import json
import time
import sqlite3
import requests
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from flask import Flask, request, jsonify
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__)

# ==================== CONFIGURATION ====================
# These should be loaded from a config file or environment variables
# Create a config.py file with these constants

try:
    from config import (
        BOT_TOKEN,
        BOT_URL,
        DB_CHANNEL,
        TABLE_PREFIX,
        ADMIN_IDS,
        BOT_ENABLED,
        DISABLE_FORWARDING,
        DATABASE_PATH
    )
except ImportError:
    logger.error("Config file not found. Please create config.py with required constants.")
    sys.exit(1)

# ==================== CONSTANTS ====================
HIDDEN_FILE = 'hidden_products.json'
SPONSORED_TEXT = "\n\nSponsored by [tnur.io](https://tnur.io)"
MAINTENANCE_FILE = 'maintenance.lock'
STATE_DIR = tempfile.gettempdir()

# Set timezone to IST
os.environ['TZ'] = 'Asia/Kolkata'
time.tzset()


# ==================== DATABASE HELPERS ====================
class Database:
    """Database connection and operations handler"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database tables if they don't exist"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS {TABLE_PREFIX}users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                is_blocked INTEGER DEFAULT 0,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS {TABLE_PREFIX}products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                price REAL NOT NULL,
                type TEXT NOT NULL,
                file_ids TEXT,
                stock INTEGER DEFAULT -1,
                header_message TEXT,
                footer_message TEXT,
                discount_price REAL,
                discount_until TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS {TABLE_PREFIX}purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                status TEXT DEFAULT 'pending',
                access_granted INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES {TABLE_PREFIX}users(user_id),
                FOREIGN KEY (product_id) REFERENCES {TABLE_PREFIX}products(id)
            )
        ''')
        
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS {TABLE_PREFIX}messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                is_admin INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path, check_same_thread=False)
    
    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute a query and return cursor"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        conn.close()
        return cursor
    
    def fetchone(self, query: str, params: tuple = ()) -> Optional[tuple]:
        """Execute query and fetch one result"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        result = cursor.fetchone()
        conn.close()
        return result
    
    def fetchall(self, query: str, params: tuple = ()) -> List[tuple]:
        """Execute query and fetch all results"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        return results
    
    def fetchval(self, query: str, params: tuple = ()) -> Any:
        """Execute query and fetch single value"""
        result = self.fetchone(query, params)
        return result[0] if result else None


# Initialize database
db = Database(DATABASE_PATH)


# ==================== STATE MANAGEMENT ====================
class StateManager:
    """Manage user states for multi-step operations"""
    
    @staticmethod
    def get_state(user_id: int) -> Dict:
        """Get user state from file"""
        file_path = Path(STATE_DIR) / f'tg_bot_state_{user_id}.json'
        if file_path.exists():
            try:
                with open(file_path, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return {}
        return {}
    
    @staticmethod
    def set_state(user_id: int, data: Dict):
        """Save user state to file"""
        file_path = Path(STATE_DIR) / f'tg_bot_state_{user_id}.json'
        if not data:
            if file_path.exists():
                file_path.unlink()
        else:
            with open(file_path, 'w') as f:
                json.dump(data, f)
    
    @staticmethod
    def clear_state(user_id: int):
        """Clear user state"""
        StateManager.set_state(user_id, {})


# ==================== HIDDEN PRODUCTS HELPERS ====================
class HiddenProducts:
    """Manage hidden products using JSON file"""
    
    @staticmethod
    def get_hidden() -> List[int]:
        """Get list of hidden product IDs"""
        if Path(HIDDEN_FILE).exists():
            try:
                with open(HIDDEN_FILE, 'r') as f:
                    data = json.load(f)
                    return data if isinstance(data, list) else []
            except json.JSONDecodeError:
                return []
        return []
    
    @staticmethod
    def toggle_visibility(product_id: int) -> bool:
        """Toggle product visibility. Returns True if now hidden, False if visible"""
        hidden = HiddenProducts.get_hidden()
        
        if product_id in hidden:
            # Unhide
            hidden.remove(product_id)
            status = False
        else:
            # Hide
            hidden.append(product_id)
            status = True
        
        with open(HIDDEN_FILE, 'w') as f:
            json.dump(hidden, f)
        
        return status
    
    @staticmethod
    def is_hidden(product_id: int) -> bool:
        """Check if product is hidden"""
        return product_id in HiddenProducts.get_hidden()


# ==================== HELPER FUNCTIONS ====================
def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    return user_id in ADMIN_IDS


def is_maintenance_mode() -> bool:
    """Check if maintenance mode is active"""
    return Path(MAINTENANCE_FILE).exists()


def toggle_maintenance():
    """Toggle maintenance mode"""
    file_path = Path(MAINTENANCE_FILE)
    if file_path.exists():
        file_path.unlink()
    else:
        file_path.write_text('LOCKED')


def is_user_blocked(user_id: int) -> bool:
    """Check if user is blocked"""
    result = db.fetchone(
        f"SELECT is_blocked FROM {TABLE_PREFIX}users WHERE user_id = ?",
        (user_id,)
    )
    return bool(result and result[0])


def save_user(user_id: int, username: str, first_name: str):
    """Save or update user in database"""
    db.execute(
        f"""INSERT INTO {TABLE_PREFIX}users (user_id, username, first_name) 
            VALUES (?, ?, ?) 
            ON CONFLICT(user_id) DO UPDATE SET 
            username = excluded.username, 
            first_name = excluded.first_name""",
        (user_id, username, first_name)
    )


def save_user_message(user_id: int, message: str):
    """Save user message to database"""
    db.execute(
        f"INSERT INTO {TABLE_PREFIX}messages (user_id, message, is_admin) VALUES (?, ?, 0)",
        (user_id, message)
    )


def block_user(user_id: int):
    """Block a user"""
    db.execute(
        f"UPDATE {TABLE_PREFIX}users SET is_blocked = 1 WHERE user_id = ?",
        (user_id,)
    )


def unblock_user(user_id: int):
    """Unblock a user"""
    db.execute(
        f"UPDATE {TABLE_PREFIX}users SET is_blocked = 0 WHERE user_id = ?",
        (user_id,)
    )


def get_product(product_id: int) -> Optional[Dict]:
    """Get product by ID"""
    result = db.fetchone(
        f"SELECT * FROM {TABLE_PREFIX}products WHERE id = ?",
        (product_id,)
    )
    
    if result:
        columns = ['id', 'title', 'description', 'price', 'type', 'file_ids', 
                   'stock', 'header_message', 'footer_message', 'discount_price', 
                   'discount_until', 'created_at']
        return dict(zip(columns, result))
    return None


def get_current_price(product: Dict) -> float:
    """Get current price considering active discounts"""
    now = datetime.now()
    if product.get('discount_until') and product.get('discount_price'):
        try:
            discount_end = datetime.strptime(product['discount_until'], '%Y-%m-%d %H:%M')
            if discount_end > now:
                return float(product['discount_price'])
        except (ValueError, TypeError):
            pass
    return float(product['price'])


def has_active_discount(product: Dict) -> bool:
    """Check if product has active discount"""
    now = datetime.now()
    if product.get('discount_until') and product.get('discount_price'):
        try:
            discount_end = datetime.strptime(product['discount_until'], '%Y-%m-%d %H:%M')
            return discount_end > now
        except (ValueError, TypeError):
            pass
    return False


def delete_product(product_id: int):
    """Delete a product"""
    db.execute(
        f"DELETE FROM {TABLE_PREFIX}products WHERE id = ?",
        (product_id,)
    )


def revoke_access(purchase_id: int):
    """Revoke access to a purchase"""
    db.execute(
        f"UPDATE {TABLE_PREFIX}purchases SET access_granted = 0 WHERE id = ?",
        (purchase_id,)
    )


def save_product(data: Dict):
    """Save new product to database"""
    file_ids = json.dumps(data.get('file_ids', [])) if data.get('file_ids') else None
    
    db.execute(
        f"""INSERT INTO {TABLE_PREFIX}products 
            (title, description, price, type, file_ids, stock, header_message, footer_message) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            data['title'],
            data['description'],
            data['price'],
            data['type'],
            file_ids,
            data['stock'],
            data.get('header', ''),
            data.get('footer', '')
        )
    )


# ==================== TELEGRAM API HELPERS ====================
class TelegramAPI:
    """Telegram Bot API wrapper"""
    
    @staticmethod
    def api_request(method: str, data: Dict) -> Dict:
        """Make API request to Telegram"""
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
        try:
            response = requests.post(url, json=data, timeout=30)
            return response.json()
        except requests.RequestException as e:
            logger.error(f"API request failed: {e}")
            return {'ok': False, 'error': str(e)}
    
    @staticmethod
    def send_message(chat_id: int, text: str, reply_markup: Optional[Dict] = None) -> Dict:
        """Send a message"""
        # Add sponsored text for non-admins
        if not is_admin(chat_id):
            text += SPONSORED_TEXT
        
        data = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'Markdown'
        }
        
        if DISABLE_FORWARDING:
            data['protect_content'] = True
        
        if reply_markup:
            data['reply_markup'] = reply_markup
        
        return TelegramAPI.api_request('sendMessage', data)
    
    @staticmethod
    def edit_message(chat_id: int, message_id: int, text: str, reply_markup: Optional[Dict] = None) -> Dict:
        """Edit a message"""
        # Add sponsored text for non-admins
        if not is_admin(chat_id):
            text += SPONSORED_TEXT
        
        data = {
            'chat_id': chat_id,
            'message_id': message_id,
            'text': text,
            'parse_mode': 'Markdown'
        }
        
        if reply_markup:
            data['reply_markup'] = reply_markup
        
        return TelegramAPI.api_request('editMessageText', data)
    
    @staticmethod
    def delete_message(chat_id: int, message_id: int) -> Dict:
        """Delete a message"""
        return TelegramAPI.api_request('deleteMessage', {
            'chat_id': chat_id,
            'message_id': message_id
        })
    
    @staticmethod
    def answer_callback(callback_id: str, text: Optional[str] = None, show_alert: bool = False) -> Dict:
        """Answer callback query"""
        data = {'callback_query_id': callback_id}
        if text:
            data['text'] = text
            data['show_alert'] = show_alert
        return TelegramAPI.api_request('answerCallbackQuery', data)
    
    @staticmethod
    def forward_message(chat_id: int, from_chat_id: int, message_id: int) -> Dict:
        """Forward a message"""
        return TelegramAPI.api_request('forwardMessage', {
            'chat_id': chat_id,
            'from_chat_id': from_chat_id,
            'message_id': message_id
        })
    
    @staticmethod
    def copy_message(chat_id: int, from_chat_id: int, message_id: int) -> Dict:
        """Copy a message"""
        return TelegramAPI.api_request('copyMessage', {
            'chat_id': chat_id,
            'from_chat_id': from_chat_id,
            'message_id': message_id,
            'protect_content': True
        })
    
    @staticmethod
    def send_document(chat_id: int, document: str, caption: str = "") -> Dict:
        """Send a document"""
        return TelegramAPI.api_request('sendDocument', {
            'chat_id': chat_id,
            'document': document,
            'caption': caption,
            'parse_mode': 'Markdown'
        })


# ==================== INVOICE GENERATION ====================
def send_invoice(user_id: int, purchase_id: int):
    """Generate and send invoice to user"""
    # Get purchase data
    result = db.fetchone(
        f"""SELECT p.*, pr.title as product_title, u.first_name, u.username 
            FROM {TABLE_PREFIX}purchases p 
            JOIN {TABLE_PREFIX}products pr ON p.product_id = pr.id 
            JOIN {TABLE_PREFIX}users u ON p.user_id = u.user_id
            WHERE p.id = ?""",
        (purchase_id,)
    )
    
    if not result:
        TelegramAPI.send_message(user_id, "⚠️ Error: Could not fetch order details for invoice.")
        return
    
    # Map result to dictionary
    columns = ['id', 'user_id', 'product_id', 'amount', 'status', 'access_granted', 
               'created_at', 'product_title', 'first_name', 'username']
    data = dict(zip(columns, result))
    
    customer_name = data['first_name'] or (f"@{data['username']}" if data['username'] else "Customer")
    
    # Prepare invoice payload
    payload = {
        "type": "invoice",
        "title": "TAX INVOICE",
        "invoice_number": f"INV-{str(data['id']).zfill(6)}",
        "invoice_date": datetime.now().strftime('%Y-%m-%d'),
        "brand_name": "ATDB.SHOP",
        "logo": "https://atdb.uno/logo.png",
        "primary_color": "#90D5FF",
        "watermark": "",
        "watermark_image": "https://atdb.uno/fio/uploads/atdb-uno_20251126_140212_yu.jpg",
        "customer_name": customer_name,
        "customer_email": "N/A",
        "customer_address": f"Telegram User ID: {user_id}",
        "products": [
            {
                "description": data['product_title'],
                "quantity": 1,
                "price": float(data['amount'])
            }
        ],
        "currency": "Rs",
        "tax": 0,
        "discount": 0,
        "total": float(data['amount']),
        "notes": "Paid by Razorpay",
        "footer_text": "Powered by atdb.uno"
    }
    
    # Call invoice API
    try:
        response = requests.post(
            "https://atdb.uno/pdf/api.php",
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success') and result.get('data', {}).get('download_url'):
                pdf_url = result['data']['download_url']
                time.sleep(5)  # Wait for PDF to be ready
                
                # Send PDF
                caption = f"🧾 *Invoice #INV-{str(data['id']).zfill(6)}*\n\nPaid via Razorpay"
                res = TelegramAPI.send_document(user_id, pdf_url, caption)
                
                if not res.get('ok'):
                    TelegramAPI.send_message(
                        user_id, 
                        f"🧾 *Invoice Generated*\n\nUnable to upload PDF directly. Please download here:\n[Download Invoice]({pdf_url})"
                    )
            else:
                TelegramAPI.send_message(user_id, "⚠️ Invoice generation failed (API Error).")
        else:
            TelegramAPI.send_message(user_id, f"⚠️ Invoice generation failed (Server Error: {response.status_code}).")
    
    except requests.RequestException as e:
        logger.error(f"Invoice generation failed: {e}")
        TelegramAPI.send_message(user_id, "⚠️ Invoice generation failed (Network Error).")


def grant_subscription_access(purchase_id: int, message: str):
    """Grant subscription access and send invoice"""
    db.execute(
        f"UPDATE {TABLE_PREFIX}purchases SET access_granted = 1 WHERE id = ?",
        (purchase_id,)
    )
    
    user_id = db.fetchval(
        f"SELECT user_id FROM {TABLE_PREFIX}purchases WHERE id = ?",
        (purchase_id,)
    )
    
    # Send access message
    TelegramAPI.send_message(user_id, f"🎉 *Access Granted!*\n\n{message}")
    
    # Generate and send invoice
    send_invoice(user_id, purchase_id)


# ==================== DISPLAY FUNCTIONS ====================
def show_admin_panel(chat_id: int, message_id: int = 0):
    """Show admin panel"""
    web_app_url = f"{BOT_URL}admin.php"
    maint_status = '🔴 ON' if is_maintenance_mode() else '🟢 OFF'
    
    keyboard = {
        'inline_keyboard': [
            [{'text': '🚀 Open Web Dashboard', 'web_app': {'url': web_app_url}}],
            [
                {'text': '📦 Manage Products', 'callback_data': 'admin_products'},
                {'text': '📊 Statistics', 'callback_data': 'admin_stats'}
            ],
            [
                {'text': '👥 Users List', 'callback_data': 'admin_users'},
                {'text': '🔍 Search User', 'callback_data': 'admin_search_user_start'}
            ],
            [
                {'text': '📢 Broadcast', 'callback_data': 'admin_broadcast'},
                {'text': '💬 Messages', 'callback_data': 'admin_messages'}
            ],
            [{'text': f'🛠 Maintenance: {maint_status}', 'callback_data': 'toggle_maintenance'}]
        ]
    }
    
    text = "🔐 *Admin Panel*\n\nChoose an option:"
    
    if message_id:
        TelegramAPI.edit_message(chat_id, message_id, text, keyboard)
    else:
        TelegramAPI.send_message(chat_id, text, keyboard)


def show_admin_products(chat_id: int, message_id: int):
    """Show admin products list"""
    products = db.fetchall(
        f"SELECT * FROM {TABLE_PREFIX}products ORDER BY id DESC"
    )
    
    keyboard = {'inline_keyboard': [[{'text': '➕ Add Product', 'callback_data': 'admin_add_product'}]]}
    hidden = HiddenProducts.get_hidden()
    
    for product in products:
        product_id, title, _, price, _, _, stock = product[:7]
        current_price = price  # Simplified, should check discount
        stock_text = '∞' if stock == -1 else str(stock)
        status_icon = '🚫' if product_id in hidden else '✅'
        
        keyboard['inline_keyboard'].append([{
            'text': f"{status_icon} {title} - ₹{current_price} (Stock: {stock_text})",
            'callback_data': f"admin_edit_product:{product_id}"
        }])
    
    keyboard['inline_keyboard'].append([{'text': '« Back', 'callback_data': 'back_admin'}])
    
    text = "📦 *Product Management*\n\n🚫 = Hidden from users\n✅ = Visible"
    
    if message_id:
        TelegramAPI.edit_message(chat_id, message_id, text, keyboard)
    else:
        TelegramAPI.send_message(chat_id, text, keyboard)


def show_edit_product(chat_id: int, message_id: int, product_id: int):
    """Show product edit options"""
    product = get_product(product_id)
    if not product:
        return
    
    price = get_current_price(product)
    stock = 'Unlimited' if product['stock'] == -1 else product['stock']
    is_hidden = HiddenProducts.is_hidden(product_id)
    
    visibility_text = "🚫 Hidden" if is_hidden else "✅ Visible"
    visibility_btn = "👁 Unhide Product" if is_hidden else "🚫 Hide Product"
    
    message = f"✏️ *Edit Product*\n\nTitle: {product['title']}\nPrice: ₹{price}\nStock: {stock}\nType: {product['type'].title()}\nVisibility: {visibility_text}"
    
    keyboard = {
        'inline_keyboard': [
            [
                {'text': '💰 Update Price', 'callback_data': f"admin_update_price:{product_id}"},
                {'text': '📊 Update Stock', 'callback_data': f"admin_update_stock:{product_id}"}
            ],
            [{'text': '🎉 Set Discount', 'callback_data': f"admin_set_discount:{product_id}"}],
            [{'text': visibility_btn, 'callback_data': f"admin_toggle_hide:{product_id}"}],
            [{'text': '🗑 Delete Product', 'callback_data': f"admin_delete_product:{product_id}"}],
            [{'text': '« Back', 'callback_data': 'admin_products'}]
        ]
    }
    
    TelegramAPI.edit_message(chat_id, message_id, message, keyboard)


def show_product_list(chat_id: int):
    """Show product list to users"""
    view_app_url = f"{BOT_URL}view.php"
    
    products = db.fetchall(
        f"SELECT * FROM {TABLE_PREFIX}products WHERE stock != 0 ORDER BY id DESC"
    )
    
    hidden = HiddenProducts.get_hidden()
    
    if not products:
        TelegramAPI.send_message(chat_id, "🛍️ No products available right now.")
        return
    
    keyboard = {
        'inline_keyboard': [
            [{'text': '🚀 Open Store App', 'web_app': {'url': view_app_url}}]
        ]
    }
    
    for product in products:
        product_id, title, _, price = product[:4]
        
        # Skip hidden products
        if product_id in hidden:
            continue
        
        product_dict = get_product(product_id)
        current_price = get_current_price(product_dict)
        has_discount = has_active_discount(product_dict)
        
        price_text = f"~~₹{price}~~ ₹{current_price}" if has_discount else f"₹{current_price}"
        
        keyboard['inline_keyboard'].append([{
            'text': f"{title} - {price_text}",
            'callback_data': f"product:{product_id}"
        }])
    
    keyboard['inline_keyboard'].extend([
        [{'text': '📜 My Purchases', 'callback_data': 'my_purchases'}],
        [{'text': '✉️ Contact Admin', 'callback_data': 'contact_admin'}]
    ])
    
    TelegramAPI.send_message(chat_id, "🛍️ *Welcome to our Store!*\n\nChoose a product:", keyboard)


def show_product(chat_id: int, message_id: int, product_id: int):
    """Show product details"""
    product = get_product(product_id)
    if not product:
        return
    
    price = get_current_price(product)
    has_discount = has_active_discount(product)
    
    message = f"{product.get('header_message', '')}\n\n🏷️ *{product['title']}*\n\n{product['description']}\n\n"
    
    if has_discount:
        discount_until = datetime.strptime(product['discount_until'], '%Y-%m-%d %H:%M').strftime('%d %b %Y %H:%M')
        message += f"💰 ~~₹{product['price']}~~ *₹{price}*\n🎉 Discount until: {discount_until}\n\n"
    else:
        message += f"💰 Price: *₹{price}*\n\n"
    
    message += f"📦 Type: {product['type'].title()}\n"
    if product['stock'] != -1:
        message += f"📊 Stock: {product['stock']} left\n"
    
    message += f"\n{product.get('footer_message', '')}"
    
    keyboard = {
        'inline_keyboard': [
            [{'text': '💳 Buy Now', 'callback_data': f"buy:{product_id}"}],
            [{'text': '« Back', 'callback_data': 'back_products'}]
        ]
    }
    
    TelegramAPI.edit_message(chat_id, message_id, message, keyboard)


def start_purchase(chat_id: int, user_id: int, product_id: int):
    """Start purchase process"""
    product = get_product(product_id)
    if not product or product['stock'] == 0:
        TelegramAPI.send_message(chat_id, "❌ Product not available!")
        return
    
    price = get_current_price(product)
    web_app_url = f"{BOT_URL}pay.php?user_id={user_id}&product_id={product_id}&price={price}"
    
    keyboard = {
        'inline_keyboard': [
            [{'text': f'💳 Pay ₹{price}', 'web_app': {'url': web_app_url}}]
        ]
    }
    
    TelegramAPI.send_message(chat_id, "💳 Click the button below to proceed with payment:", keyboard)


def show_my_purchases(chat_id: int, message_id: int, user_id: int):
    """Show user's purchases"""
    purchases = db.fetchall(
        f"""SELECT p.*, pr.title, pr.type FROM {TABLE_PREFIX}purchases p 
            JOIN {TABLE_PREFIX}products pr ON p.product_id = pr.id 
            WHERE p.user_id = ? AND p.status = 'completed' 
            ORDER BY p.created_at DESC""",
        (user_id,)
    )
    
    if not purchases:
        keyboard = {'inline_keyboard': [[{'text': '« Back', 'callback_data': 'back_products'}]]}
        TelegramAPI.edit_message(chat_id, message_id, "📜 You haven't made any purchases yet.", keyboard)
        return
    
    message = "📜 *Your Purchases*\n\n"
    keyboard = {'inline_keyboard': []}
    
    for purchase in purchases:
        purchase_id, _, _, amount, _, access_granted, created_at, title, ptype = purchase
        date = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S').strftime('%d %b %Y')
        message += f"• {title} - ₹{amount} ({date})\n"
        
        row = []
        if ptype == 'digital' and access_granted:
            row.append({'text': '📥 Download', 'callback_data': f"download:{purchase_id}"})
        row.append({'text': '🧾 Invoice', 'callback_data': f"get_invoice:{purchase_id}"})
        
        keyboard['inline_keyboard'].append(row)
    
    keyboard['inline_keyboard'].append([{'text': '« Back', 'callback_data': 'back_products'}])
    TelegramAPI.edit_message(chat_id, message_id, message, keyboard)


def show_users_list(chat_id: int, message_id: int, offset: int):
    """Show users list for admin"""
    limit = 10
    users = db.fetchall(
        f"SELECT * FROM {TABLE_PREFIX}users ORDER BY joined_at DESC LIMIT {limit} OFFSET {offset}"
    )
    
    total_users = db.fetchval(f"SELECT COUNT(*) FROM {TABLE_PREFIX}users")
    
    keyboard = {'inline_keyboard': []}
    
    for user in users:
        user_id, username, first_name, is_blocked = user[:4]
        status = '🚫' if is_blocked else '✅'
        name = first_name[:15] if first_name else 'Unknown'
        
        keyboard['inline_keyboard'].append([{
            'text': f"{status} {name} (@{username or 'none'})",
            'callback_data': f"admin_user_detail:{user_id}"
        }])
    
    # Navigation buttons
    nav_buttons = []
    if offset > 0:
        prev_offset = max(0, offset - limit)
        nav_buttons.append({'text': '⬅️ Prev', 'callback_data': f"admin_users_page:{prev_offset}"})
    if offset + limit < total_users:
        next_offset = offset + limit
        nav_buttons.append({'text': 'Next ➡️', 'callback_data': f"admin_users_page:{next_offset}"})
    
    if nav_buttons:
        keyboard['inline_keyboard'].append(nav_buttons)
    
    keyboard['inline_keyboard'].append([{'text': '« Back', 'callback_data': 'back_admin'}])
    
    text = f"👥 *Users List* (Total: {total_users})"
    
    if message_id:
        TelegramAPI.edit_message(chat_id, message_id, text, keyboard)
    else:
        TelegramAPI.send_message(chat_id, text, keyboard)


def show_user_detail(chat_id: int, message_id: int, target_user_id: int):
    """Show user details for admin"""
    user = db.fetchone(
        f"SELECT * FROM {TABLE_PREFIX}users WHERE user_id = ?",
        (target_user_id,)
    )
    
    purchase_count = db.fetchval(
        f"SELECT COUNT(*) FROM {TABLE_PREFIX}purchases WHERE user_id = ? AND status = 'completed'",
        (target_user_id,)
    )
    
    user_id, username, first_name, is_blocked, joined_at = user
    joined_date = datetime.strptime(joined_at, '%Y-%m-%d %H:%M:%S').strftime('%d %b %Y')
    
    message = f"👤 *User Details*\n\nID: {user_id}\nUsername: @{username or 'none'}\nName: {first_name}\nStatus: {'🚫 Blocked' if is_blocked else '✅ Active'}\nPurchases: {purchase_count}\nJoined: {joined_date}"
    
    keyboard = {'inline_keyboard': []}
    
    if is_blocked:
        keyboard['inline_keyboard'].append([{'text': '✅ Unblock User', 'callback_data': f"admin_unblock_user:{target_user_id}"}])
    else:
        keyboard['inline_keyboard'].append([{'text': '🚫 Block User', 'callback_data': f"admin_block_user:{target_user_id}"}])
    
    keyboard['inline_keyboard'].extend([
        [{'text': '💬 Send Message', 'callback_data': f"admin_reply:{target_user_id}"}],
        [{'text': '« Back', 'callback_data': 'admin_users'}]
    ])
    
    if message_id:
        TelegramAPI.edit_message(chat_id, message_id, message, keyboard)
    else:
        TelegramAPI.send_message(chat_id, message, keyboard)


def show_stats(chat_id: int, message_id: int):
    """Show bot statistics"""
    total_users = db.fetchval(f"SELECT COUNT(*) FROM {TABLE_PREFIX}users")
    total_products = db.fetchval(f"SELECT COUNT(*) FROM {TABLE_PREFIX}products")
    total_purchases = db.fetchval(f"SELECT COUNT(*) FROM {TABLE_PREFIX}purchases WHERE status='completed'")
    total_revenue = db.fetchval(f"SELECT SUM(amount) FROM {TABLE_PREFIX}purchases WHERE status='completed'") or 0
    
    message = f"📊 *Bot Statistics*\n\n👥 Total Users: {total_users}\n📦 Total Products: {total_products}\n💳 Total Purchases: {total_purchases}\n💰 Total Revenue: ₹{total_revenue:,.2f}"
    
    keyboard = {'inline_keyboard': [[{'text': '« Back', 'callback_data': 'back_admin'}]]}
    
    if message_id:
        TelegramAPI.edit_message(chat_id, message_id, message, keyboard)
    else:
        TelegramAPI.send_message(chat_id, message, keyboard)


def show_pending_messages(chat_id: int, message_id: int):
    """Show pending messages for admin"""
    user_ids = db.fetchall(
        f"SELECT DISTINCT user_id FROM {TABLE_PREFIX}messages WHERE is_admin = 0 ORDER BY created_at DESC LIMIT 10"
    )
    
    if not user_ids:
        keyboard = {'inline_keyboard': [[{'text': '« Back', 'callback_data': 'back_admin'}]]}
        TelegramAPI.edit_message(chat_id, message_id, "💬 No pending messages", keyboard)
        return
    
    keyboard = {'inline_keyboard': []}
    
    for (user_id,) in user_ids:
        username = db.fetchval(
            f"SELECT username FROM {TABLE_PREFIX}users WHERE user_id = ?",
            (user_id,)
        )
        keyboard['inline_keyboard'].append([{
            'text': f"💬 @{username or 'none'}",
            'callback_data': f"admin_reply:{user_id}"
        }])
    
    keyboard['inline_keyboard'].append([{'text': '« Back', 'callback_data': 'back_admin'}])
    TelegramAPI.edit_message(chat_id, message_id, "💬 *Pending Messages*", keyboard)


def send_digital_product(chat_id: int, purchase_id: int):
    """Send digital product files to user"""
    result = db.fetchone(
        f"""SELECT p.*, pr.file_ids, pr.title FROM {TABLE_PREFIX}purchases p 
            JOIN {TABLE_PREFIX}products pr ON p.product_id = pr.id 
            WHERE p.id = ? AND p.access_granted = 1""",
        (purchase_id,)
    )
    
    if not result or not result[7]:  # file_ids at index 7
        TelegramAPI.send_message(chat_id, "❌ Files not found!")
        return
    
    title = result[8]  # title at index 8
    TelegramAPI.send_message(chat_id, f"📥 *{title}*\n\nSending your files...")
    
    file_ids = json.loads(result[7])
    for file_id in file_ids:
        TelegramAPI.copy_message(chat_id, DB_CHANNEL, file_id)
        time.sleep(0.5)


def search_user(chat_id: int, query: str):
    """Search for a user"""
    query = query.strip()
    
    if query.startswith('@'):
        username = query[1:]
        result = db.fetchone(
            f"SELECT * FROM {TABLE_PREFIX}users WHERE username LIKE ?",
            (f"%{username}%",)
        )
    else:
        result = db.fetchone(
            f"SELECT * FROM {TABLE_PREFIX}users WHERE user_id = ? OR first_name LIKE ?",
            (query, f"%{query}%")
        )
    
    if result:
        show_user_detail(chat_id, 0, result[0])
    else:
        TelegramAPI.send_message(chat_id, "❌ User not found.")
        show_admin_panel(chat_id, 0)


# ==================== WIZARD HANDLERS ====================
def start_add_product(chat_id: int, user_id: int):
    """Start add product wizard"""
    StateManager.set_state(user_id, {'action': 'add_product', 'step': 1})
    TelegramAPI.send_message(chat_id, "➕ *Add New Product*\n\n📝 Send product title:\n/cancel to stop")


def handle_product_addition(message: Dict, state: Dict):
    """Handle product addition wizard steps"""
    chat_id = message['chat']['id']
    user_id = message['from']['id']
    text = message.get('text', '')
    
    step = state.get('step', 1)
    
    if step == 1:
        state['title'] = text
        state['step'] = 2
        StateManager.set_state(user_id, state)
        TelegramAPI.send_message(chat_id, "📝 Send product description:")
    
    elif step == 2:
        state['description'] = text
        StateManager.set_state(user_id, state)
        keyboard = {
            'inline_keyboard': [
                [{'text': '📥 Digital Download', 'callback_data': 'product_type:digital'}],
                [{'text': '🔄 Subscription', 'callback_data': 'product_type:subscription'}]
            ]
        }
        TelegramAPI.send_message(chat_id, "📦 Select product type:", keyboard)
    
    elif step == 3:
        try:
            state['price'] = float(text)
            state['step'] = 4
            StateManager.set_state(user_id, state)
            TelegramAPI.send_message(chat_id, "📊 Send stock amount (-1 for unlimited):")
        except ValueError:
            TelegramAPI.send_message(chat_id, "❌ Please enter a valid number for price.")
    
    elif step == 4:
        state['stock'] = int(text)
        state['step'] = 5
        StateManager.set_state(user_id, state)
        TelegramAPI.send_message(chat_id, "📄 Send header message (or send 'skip'):")
    
    elif step == 5:
        state['header'] = '' if text == 'skip' else text
        state['step'] = 6
        StateManager.set_state(user_id, state)
        TelegramAPI.send_message(chat_id, "📄 Send footer message (or send 'skip'):")
    
    elif step == 6:
        state['footer'] = '' if text == 'skip' else text
        
        if state['type'] == 'digital':
            state['action'] = 'upload_files'
            del state['step']
            StateManager.set_state(user_id, state)
            TelegramAPI.send_message(chat_id, "📎 Send files for this product (Send /done when finished):")
        else:
            save_product(state)
            StateManager.clear_state(user_id)
            TelegramAPI.send_message(chat_id, "✅ Product created successfully!")


def handle_file_upload(message: Dict, state: Dict):
    """Handle file upload for digital products"""
    chat_id = message['chat']['id']
    user_id = message['from']['id']
    text = message.get('text', '')
    
    if text == '/done':
        save_product(state)
        StateManager.clear_state(user_id)
        TelegramAPI.send_message(chat_id, "✅ Product created successfully with files!")
        return
    
    file_id = None
    if 'document' in message:
        file_id = message['document']['file_id']
    elif 'photo' in message:
        file_id = message['photo'][-1]['file_id']
    elif 'video' in message:
        file_id = message['video']['file_id']
    
    if file_id:
        result = TelegramAPI.forward_message(DB_CHANNEL, chat_id, message['message_id'])
        if result.get('ok') and result.get('result', {}).get('message_id'):
            db_message_id = result['result']['message_id']
            if 'file_ids' not in state:
                state['file_ids'] = []
            state['file_ids'].append(db_message_id)
            StateManager.set_state(user_id, state)
            TelegramAPI.send_message(chat_id, "✅ File uploaded! Send more or type /done to finish.")
        else:
            TelegramAPI.send_message(chat_id, "❌ Failed to save file. Ensure Bot is Admin in DB Channel.")
    else:
        TelegramAPI.send_message(chat_id, "⚠️ Please send a file or type /done.")


def handle_broadcast(chat_id: int, message: Dict):
    """Handle broadcast message"""
    status_msg = TelegramAPI.send_message(chat_id, "⏳ *Broadcast Started*...")
    status_msg_id = status_msg.get('result', {}).get('message_id')
    
    users = db.fetchall(f"SELECT user_id FROM {TABLE_PREFIX}users WHERE is_blocked = 0")
    
    sent = 0
    failed = 0
    total = len(users)
    
    # Check if text or photo
    is_photo = 'photo' in message
    text_content = message.get('caption' if is_photo else 'text', '')
    
    for index, (user_id,) in enumerate(users):
        if is_photo:
            photo_id = message['photo'][-1]['file_id']
            result = TelegramAPI.api_request('sendPhoto', {
                'chat_id': user_id,
                'photo': photo_id,
                'caption': text_content
            })
        else:
            result = TelegramAPI.send_message(user_id, text_content)
        
        if result.get('ok'):
            sent += 1
        else:
            failed += 1
        
        if index % 20 == 0 and status_msg_id:
            TelegramAPI.edit_message(
                chat_id,
                status_msg_id,
                f"⏳ *Broadcasting...*\n\nProgress: {index}/{total}\n✅ Sent: {sent}\n❌ Failed: {failed}"
            )
        
        time.sleep(0.05)
    
    final_msg = f"📊 *Broadcast Complete*\n\n✅ Sent: {sent}\n❌ Failed: {failed}"
    if status_msg_id:
        TelegramAPI.edit_message(chat_id, status_msg_id, final_msg)
    else:
        TelegramAPI.send_message(chat_id, final_msg)


# ==================== MESSAGE & CALLBACK HANDLERS ====================
def handle_message(message: Dict):
    """Handle incoming messages"""
    chat_id = message['chat']['id']
    user_id = message['from']['id']
    username = message['from'].get('username', '')
    first_name = message['from'].get('first_name', '')
    text = message.get('text', '')
    message_id = message['message_id']
    
    # Save user
    save_user(user_id, username, first_name)
    
    # Blocking check
    if is_user_blocked(user_id) and not is_admin(user_id):
        TelegramAPI.delete_message(chat_id, message_id)
        return
    
    # Maintenance check
    if is_maintenance_mode() and not is_admin(user_id):
        TelegramAPI.send_message(chat_id, "🛠 *System Maintenance*\n\nThe bot is currently being updated. Please try again later.")
        return
    
    # Cancel command
    if text == '/cancel':
        StateManager.clear_state(user_id)
        TelegramAPI.send_message(chat_id, "❌ Action cancelled.")
        if is_admin(user_id):
            show_admin_panel(chat_id, 0)
        else:
            show_product_list(chat_id)
        return
    
    # Check for active states
    state = StateManager.get_state(user_id)
    
    if state:
        action = state.get('action')
        
        if is_admin(user_id):
            if action == 'add_product':
                handle_product_addition(message, state)
                return
            elif action == 'update_stock':
                product_id = state['product_id']
                stock = int(text)
                db.execute(
                    f"UPDATE {TABLE_PREFIX}products SET stock = ? WHERE id = ?",
                    (stock, product_id)
                )
                StateManager.clear_state(user_id)
                TelegramAPI.send_message(chat_id, "✅ Stock updated successfully!")
                return
            elif action == 'update_price':
                product_id = state['product_id']
                price = float(text)
                db.execute(
                    f"UPDATE {TABLE_PREFIX}products SET price = ? WHERE id = ?",
                    (price, product_id)
                )
                StateManager.clear_state(user_id)
                TelegramAPI.send_message(chat_id, "✅ Price updated successfully!")
                return
            elif action == 'set_discount':
                product_id = state['product_id']
                parts = text.split('|')
                if len(parts) == 2:
                    discount_price = float(parts[0])
                    discount_until = parts[1].strip()
                    db.execute(
                        f"UPDATE {TABLE_PREFIX}products SET discount_price = ?, discount_until = ? WHERE id = ?",
                        (discount_price, discount_until, product_id)
                    )
                    TelegramAPI.send_message(chat_id, "✅ Discount set successfully!")
                else:
                    TelegramAPI.send_message(chat_id, "❌ Invalid format! Operation cancelled.")
                StateManager.clear_state(user_id)
                return
            elif action == 'grant_access':
                purchase_id = state['purchase_id']
                grant_subscription_access(purchase_id, text)
                StateManager.clear_state(user_id)
                TelegramAPI.send_message(chat_id, "✅ Access granted and Invoice initiated.")
                return
            elif action == 'reply_user':
                target_user_id = state['target_user_id']
                TelegramAPI.send_message(target_user_id, f"📩 *Admin Reply:*\n\n{text}")
                StateManager.clear_state(user_id)
                TelegramAPI.send_message(chat_id, "✅ Reply sent!")
                return
            elif action == 'broadcast':
                handle_broadcast(chat_id, message)
                StateManager.clear_state(user_id)
                return
            elif action == 'search_user':
                search_user(chat_id, text)
                StateManager.clear_state(user_id)
                return
            elif action == 'upload_files':
                handle_file_upload(message, state)
                return
        
        if action == 'contact_admin':
            save_user_message(user_id, text)
            for admin_id in ADMIN_IDS:
                keyboard = {
                    'inline_keyboard': [[{'text': '💬 Reply', 'callback_data': f"admin_reply:{user_id}"}]]
                }
                TelegramAPI.send_message(
                    admin_id,
                    f"📨 *New Message from User*\n\nUser: @{username} (ID: {user_id})\n\n{text}",
                    keyboard
                )
            TelegramAPI.send_message(chat_id, "✅ Your message has been sent to admin!")
            StateManager.clear_state(user_id)
            return
    
    # Handle commands
    if text == '/start':
        StateManager.clear_state(user_id)
        if is_admin(user_id):
            show_admin_panel(chat_id, 0)
        else:
            show_product_list(chat_id)
    elif text == '/admin' and is_admin(user_id):
        StateManager.clear_state(user_id)
        show_admin_panel(chat_id, 0)


def handle_callback(callback: Dict):
    """Handle callback queries"""
    callback_id = callback['id']
    chat_id = callback['message']['chat']['id']
    message_id = callback['message']['message_id']
    user_id = callback['from']['id']
    data = callback['data']
    
    # Blocking check
    if is_user_blocked(user_id) and not is_admin(user_id):
        TelegramAPI.answer_callback(callback_id, "⛔ You have been blocked from using this bot.", True)
        TelegramAPI.delete_message(chat_id, message_id)
        return
    
    # Maintenance check
    if is_maintenance_mode() and not is_admin(user_id):
        TelegramAPI.answer_callback(callback_id, "🛠 System under maintenance", True)
        return
    
    # Answer callback immediately
    TelegramAPI.answer_callback(callback_id)
    
    parts = data.split(':')
    action = parts[0]
    
    # Clear state except for product_type
    if action != 'product_type':
        StateManager.clear_state(user_id)
    
    # Route actions
    if action == 'admin_products':
        show_admin_products(chat_id, message_id)
    
    elif action == 'admin_add_product':
        start_add_product(chat_id, user_id)
    
    elif action == 'admin_edit_product':
        product_id = int(parts[1])
        show_edit_product(chat_id, message_id, product_id)
    
    elif action == 'admin_delete_product':
        product_id = int(parts[1])
        delete_product(product_id)
        TelegramAPI.answer_callback(callback_id, "Product deleted!")
        show_admin_products(chat_id, message_id)
    
    elif action == 'admin_toggle_hide':
        product_id = int(parts[1])
        is_hidden = HiddenProducts.toggle_visibility(product_id)
        msg = "Product Hidden 🚫" if is_hidden else "Product Visible ✅"
        TelegramAPI.answer_callback(callback_id, msg)
        show_edit_product(chat_id, message_id, product_id)
    
    elif action == 'admin_update_stock':
        product_id = int(parts[1])
        StateManager.set_state(user_id, {'action': 'update_stock', 'product_id': product_id})
        TelegramAPI.send_message(chat_id, "📊 Send new stock amount (or -1 for unlimited):\n/cancel to stop")
    
    elif action == 'admin_update_price':
        product_id = int(parts[1])
        StateManager.set_state(user_id, {'action': 'update_price', 'product_id': product_id})
        TelegramAPI.send_message(chat_id, "💰 Send new price:\n/cancel to stop")
    
    elif action == 'admin_set_discount':
        product_id = int(parts[1])
        StateManager.set_state(user_id, {'action': 'set_discount', 'product_id': product_id})
        TelegramAPI.send_message(chat_id, "🎉 Send discount details in format:\nPrice|YYYY-MM-DD HH:MM\n\nExample: 99|2024-12-31 23:59\n/cancel to stop")
    
    elif action == 'product_type':
        current_state = StateManager.get_state(user_id)
        if current_state.get('action') == 'add_product':
            current_state['type'] = parts[1]
            current_state['step'] = 3
            StateManager.set_state(user_id, current_state)
            TelegramAPI.edit_message(chat_id, message_id, f"✅ Type selected: {parts[1].title()}")
            TelegramAPI.send_message(chat_id, "💰 Send product price:\n/cancel to stop")
        else:
            TelegramAPI.send_message(chat_id, "❌ Session expired. Please start over.")
    
    elif action == 'admin_users':
        show_users_list(chat_id, message_id, 0)
    
    elif action == 'admin_users_page':
        offset = int(parts[1])
        show_users_list(chat_id, message_id, offset)
    
    elif action == 'admin_user_detail':
        target_user_id = int(parts[1])
        show_user_detail(chat_id, message_id, target_user_id)
    
    elif action == 'admin_search_user_start':
        StateManager.set_state(user_id, {'action': 'search_user'})
        TelegramAPI.send_message(chat_id, "🔍 Send Username (with @) or User ID to search:")
    
    elif action == 'admin_block_user':
        target_user_id = int(parts[1])
        block_user(target_user_id)
        show_user_detail(chat_id, message_id, target_user_id)
    
    elif action == 'admin_unblock_user':
        target_user_id = int(parts[1])
        unblock_user(target_user_id)
        show_user_detail(chat_id, message_id, target_user_id)
    
    elif action == 'admin_revoke_access':
        purchase_id = int(parts[1])
        revoke_access(purchase_id)
        TelegramAPI.send_message(chat_id, "✅ Access revoked successfully!")
    
    elif action == 'admin_send_access':
        purchase_id = int(parts[1])
        StateManager.set_state(user_id, {'action': 'grant_access', 'purchase_id': purchase_id})
        TelegramAPI.send_message(chat_id, "📝 Please send the access message instructions:\n/cancel to stop")
    
    elif action == 'admin_broadcast':
        StateManager.set_state(user_id, {'action': 'broadcast'})
        TelegramAPI.send_message(chat_id, "📢 Send the broadcast message (Text or Photo):\n/cancel to stop")
    
    elif action == 'admin_stats':
        show_stats(chat_id, message_id)
    
    elif action == 'admin_messages':
        show_pending_messages(chat_id, message_id)
    
    elif action == 'admin_reply':
        target_user_id = int(parts[1])
        StateManager.set_state(user_id, {'action': 'reply_user', 'target_user_id': target_user_id})
        TelegramAPI.send_message(chat_id, "✍️ Send your reply:\n/cancel to stop")
    
    elif action == 'toggle_maintenance':
        toggle_maintenance()
        show_admin_panel(chat_id, message_id)
    
    # User actions
    elif action == 'product':
        product_id = int(parts[1])
        if HiddenProducts.is_hidden(product_id) and not is_admin(user_id):
            TelegramAPI.answer_callback(callback_id, "⚠️ This product is currently unavailable.", True)
            return
        show_product(chat_id, message_id, product_id)
    
    elif action == 'buy':
        product_id = int(parts[1])
        if HiddenProducts.is_hidden(product_id) and not is_admin(user_id):
            TelegramAPI.answer_callback(callback_id, "⚠️ This product is unavailable.", True)
            return
        start_purchase(chat_id, user_id, product_id)
    
    elif action == 'my_purchases':
        show_my_purchases(chat_id, message_id, user_id)
    
    elif action == 'download':
        purchase_id = int(parts[1])
        send_digital_product(chat_id, purchase_id)
    
    elif action == 'get_invoice':
        purchase_id = int(parts[1])
        TelegramAPI.send_message(chat_id, "⏳ Generating invoice, please wait...")
        send_invoice(user_id, purchase_id)
    
    elif action == 'contact_admin':
        StateManager.set_state(user_id, {'action': 'contact_admin'})
        TelegramAPI.send_message(chat_id, "✉️ Send your message to admin:\n/cancel to stop")
    
    elif action == 'back_products':
        show_product_list(chat_id)
    
    elif action == 'back_admin':
        show_admin_panel(chat_id, message_id)


# ==================== WEBHOOK ENDPOINT ====================
@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming webhook updates"""
    if not BOT_ENABLED:
        return jsonify({'error': 'Bot is currently disabled'}), 403
    
    try:
        update = request.get_json()
        
        if 'message' in update:
            handle_message(update['message'])
        elif 'callback_query' in update:
            handle_callback(update['callback_query'])
        
        return jsonify({'ok': True})
    
    except Exception as e:
        logger.error(f"Error processing update: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'bot_enabled': BOT_ENABLED,
        'maintenance_mode': is_maintenance_mode()
    })


# ==================== MAIN ====================
if __name__ == '__main__':
    logger.info("Starting Telegram Bot API server...")
    app.run(host='0.0.0.0', port=5000, debug=False)
