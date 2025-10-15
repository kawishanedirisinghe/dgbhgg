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
    
    server_ip = os.getenv('RENDER_EXTERNAL_HOSTNAME', 'catseek.onrender.com')
    
    await update.message.reply_text(
        f"🤖 SSH VPN Bot\n\n"
        f"🌐 Server: `{server_ip}`\n"
        f"🔌 Port: `443`\n\n"
        "Available commands:\n"
        "/create <username> - Create new user\n"
        "/list - List all users\n"
        "/delete <username> - Delete user\n"
        "/status - Check server status\n"
        "/test - Test SSH connection",
        parse_mode='Markdown'
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
    if not username.isalnum() or len(username) < 3:
        await update.message.reply_text("❌ Username should contain only letters and numbers (min 3 characters).")
        return
    
    users = load_users()
    
    if username in users:
        await update.message.reply_text(f"❌ User `{username}` already exists.", parse_mode='Markdown')
        return
    
    # Generate random password
    password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
    
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
        server_ip = os.getenv('RENDER_EXTERNAL_HOSTNAME', 'catseek.onrender.com')
        
        # Reload SSH configuration
        subprocess.run(['pkill', '-HUP', 'sshd'])
        
        message = (
            f"✅ User created successfully!\n\n"
            f"👤 Username: `{username}`\n"
            f"🔑 Password: `{password}`\n"
            f"🌐 Server: `{server_ip}`\n"
            f"🔌 Port: `443`\n\n"
            f"📱 Connection command:\n"
            f"```bash\nssh {username}@{server_ip} -p 443\n```\n\n"
            f"🔍 Test connection:\n"
            f"```bash\nssh {username}@{server_ip} -p 443 -o ConnectTimeout=10\n```\n\n"
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
        await update.message.reply_text(f"❌ User `{username}` not found.", parse_mode='Markdown')
        return
    
    # Delete system user
    try:
        result = subprocess.run(['userdel', '-r', username], 
                              capture_output=True, text=True, check=True)
        del users[username]
        save_users(users)
        
        # Update SSH configuration
        subprocess.run(['sed', '-i', f'/AllowUsers.*{username}/d', '/etc/ssh/sshd_config'])
        subprocess.run(['pkill', '-HUP', 'sshd'])
        
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
        
        # Check SSH service
        ssh_status = subprocess.run(['pgrep', 'sshd'], capture_output=True, text=True)
        ssh_running = "✅ Running" if ssh_status.returncode == 0 else "❌ Stopped"
        
        # Check port listening
        port_check = subprocess.run(['netstat', '-tln'], capture_output=True, text=True)
        port_listening = "✅ Yes" if ':443' in port_check.stdout else "❌ No"
        
        users = load_users()
        server_ip = os.getenv('RENDER_EXTERNAL_HOSTNAME', 'catseek.onrender.com')
        
        message = (
            f"🖥️ Server Status\n\n"
            f"🌐 Server: `{server_ip}`\n"
            f"🔌 SSH Port: `443`\n"
            f"👥 Total Users: `{len(users)}`\n"
            f"🟢 SSH Service: {ssh_running}\n"
            f"📡 Port Listening: {port_listening}\n"
            f"⏰ Uptime: `{uptime}`"
        )
        
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error getting status: {str(e)}")

async def test_connection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Authorization failed.")
        return
    
    try:
        # Test SSH configuration
        config_test = subprocess.run(['sshd', '-t'], capture_output=True, text=True)
        config_ok = "✅ Valid" if config_test.returncode == 0 else f"❌ Error: {config_test.stderr}"
        
        # Test if SSH is listening
        listening_test = subprocess.run(['netstat', '-tln'], capture_output=True, text=True)
        listening = "✅ Yes" if ':443' in listening_test.stdout else "❌ No"
        
        server_ip = os.getenv('RENDER_EXTERNAL_HOSTNAME', 'catseek.onrender.com')
        
        message = (
            f"🔍 SSH Connection Test\n\n"
            f"🌐 Server: `{server_ip}`\n"
            f"🔌 Port: `443`\n"
            f"⚙️ SSH Config: {config_ok}\n"
            f"📡 Port Listening: {listening}\n\n"
            f"💡 Connection command:\n"
            f"```bash\nssh username@{server_ip} -p 443 -o ConnectTimeout=10\n```"
        )
        
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error testing connection: {str(e)}")

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
    application.add_handler(CommandHandler("test", test_connection))
    
    logging.info("Bot started successfully!")
    
    # Start bot
    application.run_polling()

if __name__ == '__main__':
    main()
