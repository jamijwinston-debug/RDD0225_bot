import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
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

# Reminder messages (5 different messages)
REMINDER_MESSAGES = [
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

# Store active reminders
active_reminders = {}

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
            InlineKeyboardButton("Cancel Reminder", callback_data="cancel_reminder")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message and reminder menu"""
    welcome_text = """
🤖 **Reminder Bot Activated!** 🤖

I can send you helpful reminders at regular intervals. Choose your preferred time frame below:

• **1 Minute** - Quick check-ins
• **5 Minutes** - Regular pauses
• **30 Minutes** - Task reviews
• **1 Hour** - Progress updates

Select a time frame to start receiving reminders! 🔔
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
    
    # Extract time frame from callback data
    time_frame = query.data.replace("reminder_", "")
    
    if time_frame in TIME_FRAMES:
        # Cancel existing reminder if any
        if user_id in active_reminders:
            active_reminders[user_id].schedule_removal()
        
        # Create new reminder job
        minutes = TIME_FRAMES[time_frame]
        job = context.application.job_queue.run_repeating(
            send_reminder,
            interval=minutes * 60,
            first=minutes * 60,
            chat_id=chat_id,
            user_id=user_id,
            data={"time_frame": time_frame}
        )
        
        active_reminders[user_id] = job
        
        confirmation_text = f"""
✅ **Reminder Set!** ✅

I'll send you reminders every **{time_frame}** starting in {minutes} minute{'s' if minutes > 1 else ''}.

You can cancel anytime using the "Cancel Reminder" button.
        """
        
        await query.edit_message_text(
            confirmation_text,
            reply_markup=get_reminder_keyboard(),
            parse_mode='Markdown'
        )

async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    """Send reminder message"""
    job = context.job
    chat_id = job.chat_id
    user_id = job.data["user_id"]
    time_frame = job.data["time_frame"]
    
    # Select random reminder message
    message = random.choice(REMINDER_MESSAGES)
    
    # Add time frame info to message
    full_message = f"{message}\n\n⏱️ Reminder interval: {time_frame}"
    
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
        await update.message.reply_text(f"🟢 Active reminder set for every {time_frame}")
    else:
        await update.message.reply_text("🔴 No active reminder. Use /start to set one!")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send help message"""
    help_text = """
📖 **Reminder Bot Help** 📖

**Commands:**
/start - Start the bot and set reminders
/cancel - Cancel your active reminder
/status - Check your reminder status
/help - Show this help message

**Features:**
- Set reminders for 1m, 5m, 30m, or 1h intervals
- Works in private chats and groups
- Random helpful messages each time
- Easy to cancel anytime

Add me to your groups to keep everyone motivated! 🚀
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
    application.add_handler(CallbackQueryHandler(handle_reminder_selection, pattern="^reminder_|^cancel_reminder"))
    
    # Add error handler
    application.add_error_handler(error_handler)

    # Start the Bot
    logger.info("🤖 Reminder Bot is running...")
    
    # For Render.com, use polling with proper error handling
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )

if __name__ == '__main__':
    main()
