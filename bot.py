import logging
import os
import subprocess
import yaml
import random
import string
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Bot configuration
BOT_TOKEN = os.getenv('BOT_TOKEN', '5995557080:AAHrli8ZJYwV_mXSNkWB3SPpnpsWzqFt8_c')
ADMIN_IDS = [int(x) for x in os.getenv('ADMIN_IDS', '1819367957').split(',')]

# User data file
USER_FILE = '/app/users.yaml'

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def load_users():
    try:
        if os.path.exists(USER_FILE):
            with open(USER_FILE, 'r') as f:
                return yaml.safe_load(f) or {}
        return {}
    except Exception as e:
        logging.error(f"Error loading users: {e}")
        return {}

def save_users(users):
    try:
        with open(USER_FILE, 'w') as f:
            yaml.dump(users, f)
    except Exception as e:
        logging.error(f"Error saving users: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ You are not authorized to use this bot.")
        return
    
    await update.message.reply_text(
        "🤖 SSH VPN Bot\n\n"
        "Available commands:\n"
        "/create <username> - Create new user\n"
        "/list - List all users\n"
        "/delete <username> - Delete user\n"
        "/status - Check server status"
    )

async def create_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Authorization failed.")
        return
    
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /create <username>")
        return
    
    username = context.args[0]
    
    # Username validation
    if not username.isalnum():
        await update.message.reply_text("❌ Username should contain only letters and numbers.")
        return
    
    users = load_users()
    
    if username in users:
        await update.message.reply_text(f"❌ User {username} already exists.")
        return
    
    # Generate random password
    password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    
    # Create system user
    try:
        result = subprocess.run(['/usr/local/bin/create_user.sh', username, password], 
                              capture_output=True, text=True, check=True)
        
        # Store user info
        users[username] = {
            'password': password, 
            'created_by': user_id,
            'created_at': str(update.message.date)
        }
        save_users(users)
        
        # Get server IP
        server_ip = os.getenv('RENDER_EXTERNAL_HOSTNAME', 'your-server.render.com')
        
        message = (
            f"✅ User created successfully!\n\n"
            f"👤 Username: `{username}`\n"
            f"🔑 Password: `{password}`\n"
            f"🌐 Server: `{server_ip}`\n"
            f"🔌 Port: `443`\n\n"
            f"📱 Connection command:\n"
            f"```bash\nssh {username}@{server_ip} -p 443\n```\n\n"
            f"⚠️ Save this information securely!"
        )
        
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except subprocess.CalledProcessError as e:
        error_msg = f"❌ Error creating user: {e.stderr if e.stderr else str(e)}"
        await update.message.reply_text(error_msg)

async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Authorization failed.")
        return
    
    users = load_users()
    
    if not users:
        await update.message.reply_text("No users found.")
        return
    
    message = "📋 User List:\n\n"
    for username, info in users.items():
        message += f"👤 `{username}`\n"
        message += f"   Created: {info.get('created_at', 'Unknown')}\n\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def delete_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Authorization failed.")
        return
    
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /delete <username>")
        return
    
    username = context.args[0]
    users = load_users()
    
    if username not in users:
        await update.message.reply_text(f"❌ User {username} not found.")
        return
    
    # Delete system user
    try:
        result = subprocess.run(['userdel', '-r', username], 
                              capture_output=True, text=True, check=True)
        del users[username]
        save_users(users)
        await update.message.reply_text(f"✅ User `{username}` deleted successfully.", parse_mode='Markdown')
    except subprocess.CalledProcessError as e:
        error_msg = f"❌ Error deleting user: {e.stderr if e.stderr else str(e)}"
        await update.message.reply_text(error_msg)

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Authorization failed.")
        return
    
    try:
        # Get system info
        uptime_result = subprocess.run(['uptime'], capture_output=True, text=True)
        uptime = uptime_result.stdout.strip() if uptime_result.returncode == 0 else "Unknown"
        
        users = load_users()
        server_ip = os.getenv('RENDER_EXTERNAL_HOSTNAME', 'your-server.render.com')
        
        message = (
            f"🖥️ Server Status\n\n"
            f"🌐 Server: `{server_ip}`\n"
            f"🔌 SSH Port: `443`\n"
            f"👥 Total Users: `{len(users)}`\n"
            f"⏰ Uptime: `{uptime}`\n"
            f"✅ Service: Running"
        )
        
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error getting status: {str(e)}")

def main():
    # Check required environment variables
    if not BOT_TOKEN or BOT_TOKEN == 'YOUR_BOT_TOKEN_HERE':
        logging.error("BOT_TOKEN environment variable is not set!")
        return
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("create", create_user))
    application.add_handler(CommandHandler("list", list_users))
    application.add_handler(CommandHandler("delete", delete_user))
    application.add_handler(CommandHandler("status", status))
    
    logging.info("Bot started successfully!")
    
    # Start bot
    application.run_polling()

if __name__ == '__main__':
    main()
