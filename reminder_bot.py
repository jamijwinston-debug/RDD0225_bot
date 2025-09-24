import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import asyncio
import random
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot Token from environment variable
BOT_TOKEN = os.getenv('BOT_TOKEN')

if not BOT_TOKEN:
    raise ValueError("Please set BOT_TOKEN environment variable")

# Default reminder messages (5 different messages)
DEFAULT_REMINDER_MESSAGES = [
    "⏰ **Friendly Reminder!** ⏰\n\nDon't forget to take a break and stretch! Your productivity will thank you. 💪",
    
    "🔔 **Reminder Alert!** 🔔\n\nTime to check your tasks and stay hydrated! 🚰 Remember: small consistent actions lead to big results. 🌟",
    
    "📢 **Quick Update Reminder!** 📢\n\nTake a moment to review your progress. Celebrate small wins! 🎉 You're doing great!",
    
    "🌅 **Mindfulness Reminder** 🌅\n\nPause for a minute. Breathe deeply. Reset your focus. You've got this! ✨",
    
    "🚀 **Productivity Boost Reminder!** 🚀\n\nTime to tackle that next task! Remember: progress over perfection. 📈"
]

# Time frames in minutes
TIME_FRAMES = {
    "1m": 1,
    "5m": 5,
    "30m": 30,
    "1h": 60
}

# Store active reminders and user states
active_reminders = {}
user_states = {}  # Store user's temporary data

def get_reminder_keyboard():
    """Create inline keyboard for time frame selection"""
    keyboard = [
        [
            InlineKeyboardButton("1 Minute", callback_data="reminder_1m"),
            InlineKeyboardButton("5 Minutes", callback_data="reminder_5m")
        ],
        [
            InlineKeyboardButton("30 Minutes", callback_data="reminder_30m"),
            InlineKeyboardButton("1 Hour", callback_data="reminder_1h")
        ],
        [
            InlineKeyboardButton("🎲 Random Reminders", callback_data="random_reminders"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_reminder")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_cancel_keyboard():
    """Create cancel keyboard for message input"""
    keyboard = [
        [InlineKeyboardButton("❌ Cancel Setup", callback_data="cancel_setup")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message and reminder menu"""
    welcome_text = """
🤖 **Custom Reminder Bot Activated!** 🤖

I can send you custom reminders at regular intervals. Choose your preferred time frame below:

• **1 Minute** - Quick check-ins
• **5 Minutes** - Regular pauses  
• **30 Minutes** - Task reviews
• **1 Hour** - Progress updates
• **🎲 Random** - Use my default motivational messages

*After selecting a time, I'll ask you what you want to be reminded about!*
    """
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=get_reminder_keyboard(),
        parse_mode='Markdown'
    )

async def handle_reminder_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle time frame selection from inline keyboard"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    
    if query.data == "cancel_reminder":
        # Cancel existing reminder
        if user_id in active_reminders:
            active_reminders[user_id].schedule_removal()
            del active_reminders[user_id]
            await query.edit_message_text("✅ Reminder cancelled!")
        else:
            await query.edit_message_text("❌ No active reminder found!")
        return
    
    if query.data == "cancel_setup":
        # Cancel reminder setup process
        if user_id in user_states:
            del user_states[user_id]
        await query.edit_message_text("❌ Reminder setup cancelled!")
        return
    
    if query.data == "random_reminders":
        # Set up random reminders
        user_states[user_id] = {
            "time_frame": "random",
            "step": "time_selected"
        }
        
        time_keyboard = [
            [
                InlineKeyboardButton("1 Minute", callback_data="random_1m"),
                InlineKeyboardButton("5 Minutes", callback_data="random_5m")
            ],
            [
                InlineKeyboardButton("30 Minutes", callback_data="random_30m"),
                InlineKeyboardButton("1 Hour", callback_data="random_1h")
            ],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel_setup")]
        ]
        
        await query.edit_message_text(
            "🎲 **Random Reminders Selected!**\n\nNow choose how often you want to receive random motivational reminders:",
            reply_markup=InlineKeyboardMarkup(time_keyboard),
            parse_mode='Markdown'
        )
        return
    
    # Handle random time selection
    if query.data.startswith("random_"):
        time_frame = query.data.replace("random_", "")
        await setup_random_reminder(query, user_id, chat_id, time_frame)
        return
    
    # Handle custom reminder time selection
    time_frame = query.data.replace("reminder_", "")
    
    if time_frame in TIME_FRAMES:
        # Store user state for custom message input
        user_states[user_id] = {
            "time_frame": time_frame,
            "step": "awaiting_message"
        }
        
        await query.edit_message_text(
            f"⏰ **{time_frame.upper()} Reminder Selected!** ⏰\n\n"
            "📝 *Now please send me the reminder message you'd like to receive.*\n\n"
            "For example:\n"
            "• \"Drink water\" 💧\n"
            "• \"Check progress on project\" 📊\n"
            "• \"Take a break and stretch\" 🧘\n"
            "• \"Review today's tasks\" ✅",
            reply_markup=get_cancel_keyboard(),
            parse_mode='Markdown'
        )

async def setup_random_reminder(query, user_id, chat_id, time_frame):
    """Setup random reminder with default messages"""
    # Cancel existing reminder if any
    if user_id in active_reminders:
        active_reminders[user_id].schedule_removal()
    
    # Create new reminder job for random messages
    minutes = TIME_FRAMES[time_frame]
    job = query.application.job_queue.run_repeating(
        send_random_reminder,
        interval=minutes * 60,
        first=minutes * 60,
        chat_id=chat_id,
        user_id=user_id,
        data={"time_frame": time_frame, "type": "random"}
    )
    
    active_reminders[user_id] = job
    
    # Clean up user state
    if user_id in user_states:
        del user_states[user_id]
    
    confirmation_text = f"""
🎲 **Random Reminder Set!** 🎲

I'll send you random motivational reminders every **{time_frame}** starting in {minutes} minute{'s' if minutes > 1 else ''}.

Each reminder will be a different inspiring message to keep you motivated! ✨

You can cancel anytime using /cancel.
    """
    
    await query.edit_message_text(
        confirmation_text,
        reply_markup=get_reminder_keyboard(),
        parse_mode='Markdown'
    )

async def handle_message_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle custom reminder message input from user"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Check if user is in message input state
    if user_id not in user_states or user_states[user_id].get("step") != "awaiting_message":
        # Not expecting a message, ignore
        return
    
    user_message = update.message.text.strip()
    time_frame = user_states[user_id]["time_frame"]
    
    if len(user_message) > 200:
        await update.message.reply_text(
            "❌ Message is too long! Please keep it under 200 characters.",
            reply_markup=get_cancel_keyboard()
        )
        return
    
    # Cancel existing reminder if any
    if user_id in active_reminders:
        active_reminders[user_id].schedule_removal()
    
    # Create new reminder job with custom message
    minutes = TIME_FRAMES[time_frame]
    job = context.application.job_queue.run_repeating(
        send_custom_reminder,
        interval=minutes * 60,
        first=minutes * 60,
        chat_id=chat_id,
        user_id=user_id,
        data={
            "time_frame": time_frame,
            "message": user_message,
            "type": "custom"
        }
    )
    
    active_reminders[user_id] = job
    
    # Clean up user state
    del user_states[user_id]
    
    confirmation_text = f"""
✅ **Custom Reminder Set!** ✅

⏰ **Frequency:** Every {time_frame}
📝 **Message:** "{user_message}"

I'll start reminding you in {minutes} minute{'s' if minutes > 1 else ''}.

You can cancel anytime using /cancel.
    """
    
    await update.message.reply_text(
        confirmation_text,
        reply_markup=get_reminder_keyboard(),
        parse_mode='Markdown'
    )

async def send_custom_reminder(context: ContextTypes.DEFAULT_TYPE):
    """Send custom reminder message"""
    job = context.job
    chat_id = job.chat_id
    user_id = job.data["user_id"]
    time_frame = job.data["time_frame"]
    custom_message = job.data["message"]
    
    reminder_message = f"""
🔔 **Reminder!** 🔔

{context.job.data['message']}

⏱️ Frequency: {time_frame}
    """
    
    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=reminder_message,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Failed to send reminder: {e}")
        # Cancel job if bot is no longer in chat
        if user_id in active_reminders:
            active_reminders[user_id].schedule_removal()
            del active_reminders[user_id]

async def send_random_reminder(context: ContextTypes.DEFAULT_TYPE):
    """Send random reminder message"""
    job = context.job
    chat_id = job.chat_id
    user_id = job.data["user_id"]
    time_frame = job.data["time_frame"]
    
    # Select random reminder message
    message = random.choice(DEFAULT_REMINDER_MESSAGES)
    
    # Add time frame info to message
    full_message = f"{message}\n\n⏱️ Random reminder interval: {time_frame}"
    
    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=full_message,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Failed to send reminder: {e}")
        # Cancel job if bot is no longer in chat
        if user_id in active_reminders:
            active_reminders[user_id].schedule_removal()
            del active_reminders[user_id]

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel active reminder"""
    user_id = update.effective_user.id
    
    # Clean up any pending states
    if user_id in user_states:
        del user_states[user_id]
    
    if user_id in active_reminders:
        active_reminders[user_id].schedule_removal()
        del active_reminders[user_id]
        await update.message.reply_text("✅ Reminder cancelled!")
    else:
        await update.message.reply_text("❌ No active reminder found!")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check reminder status"""
    user_id = update.effective_user.id
    
    if user_id in active_reminders:
        job = active_reminders[user_id]
        time_frame = job.data["time_frame"]
        reminder_type = job.data.get("type", "custom")
        
        if reminder_type == "custom":
            message = job.data["message"]
            status_text = f"🟢 Custom reminder set for every {time_frame}\n📝 Message: \"{message}\""
        else:
            status_text = f"🎲 Random reminders set for every {time_frame}"
        
        await update.message.reply_text(status_text)
    else:
        await update.message.reply_text("🔴 No active reminder. Use /start to set one!")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send help message"""
    help_text = """
📖 **Custom Reminder Bot Help** 📖

**Commands:**
/start - Start the bot and set reminders
/cancel - Cancel your active reminder
/status - Check your reminder status
/help - Show this help message

**Features:**
- Set custom reminder messages
- Choose from 1m, 5m, 30m, or 1h intervals
- Random motivational messages option
- Works in private chats and groups
- Easy to cancel anytime

**How to use:**
1. Use /start and select a time frame
2. Send your custom reminder message
3. Receive reminders automatically!

Add me to your groups to keep everyone on track! 🚀
    """
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors"""
    logger.error(f"Exception while handling an update: {context.error}")

def main():
    """Start the bot"""
    # Create Application
    application = Application.builder().token(BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(handle_reminder_selection, pattern="^reminder_|^cancel_|^random_"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message_input))
    
    # Add error handler
    application.add_error_handler(error_handler)

    # Start the Bot
    logger.info("🤖 Custom Reminder Bot is running...")
    
    # For Render.com, use polling with proper error handling
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )

if __name__ == '__main__':
    main()
