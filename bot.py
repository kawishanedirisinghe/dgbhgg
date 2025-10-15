import logging
import os
import subprocess
import yaml
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Bot configuration
BOT_TOKEN = os.getenv('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
ADMIN_IDS = [int(x) for x in os.getenv('ADMIN_IDS', '123456789').split(',')]

# User data file
USER_FILE = '/app/users.yaml'

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def load_users():
    if os.path.exists(USER_FILE):
        with open(USER_FILE, 'r') as f:
            return yaml.safe_load(f) or {}
    return {}

def save_users(users):
    with open(USER_FILE, 'w') as f:
        yaml.dump(users, f)

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
    users = load_users()
    
    if username in users:
        await update.message.reply_text(f"❌ User {username} already exists.")
        return
    
    # Generate random password
    import random
    import string
    password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    
    # Create system user
    try:
        subprocess.run(['/usr/local/bin/create_user.sh', username, password], check=True)
        
        # Store user info
        users[username] = {'password': password, 'created_by': user_id}
        save_users(users)
        
        # Get server IP (Render provides this via environment)
        server_ip = os.getenv('RENDER_EXTERNAL_HOSTNAME', 'your-server.render.com')
        
        message = (
            f"✅ User created successfully!\n\n"
            f"👤 Username: {username}\n"
            f"🔑 Password: {password}\n"
            f"🌐 Server: {server_ip}\n"
            f"🔌 Port: 443\n\n"
            f"📱 Connection command:\n"
            f"`ssh {username}@{server_ip} -p 443`\n\n"
            f"⚠️ Save this information securely!"
        )
        
        await update.message.reply_text(message)
        
    except subprocess.CalledProcessError as e:
        await update.message.reply_text(f"❌ Error creating user: {str(e)}")

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
        message += f"👤 {username}\n"
    
    await update.message.reply_text(message)

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
        subprocess.run(['userdel', '-r', username], check=True)
        del users[username]
        save_users(users)
        await update.message.reply_text(f"✅ User {username} deleted successfully.")
    except subprocess.CalledProcessError as e:
        await update.message.reply_text(f"❌ Error deleting user: {str(e)}")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Authorization failed.")
        return
    
    try:
        # Get system info
        result = subprocess.run(['uptime'], capture_output=True, text=True)
        uptime = result.stdout.strip()
        
        users = load_users()
        server_ip = os.getenv('RENDER_EXTERNAL_HOSTNAME', 'your-server.render.com')
        
        message = (
            f"🖥️ Server Status\n\n"
            f"🌐 Server: {server_ip}\n"
            f"🔌 SSH Port: 443\n"
            f"👥 Total Users: {len(users)}\n"
            f"⏰ Uptime: {uptime}\n"
            f"📊 Memory: ..."
        )
        
        await update.message.reply_text(message)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error getting status: {str(e)}")

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("create", create_user))
    application.add_handler(CommandHandler("list", list_users))
    application.add_handler(CommandHandler("delete", delete_user))
    application.add_handler(CommandHandler("status", status))
    
    # Start bot
    application.run_polling()

if __name__ == '__main__':
    main()
