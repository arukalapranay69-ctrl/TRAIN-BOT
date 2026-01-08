import os
import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from scraper import search_trains
from datetime import datetime

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Conversation states
FROM_STATION, TO_STATION, DATE = range(3)

# Your MakeMyTrip Affiliate ID (REPLACE WITH YOUR ACTUAL AFFILIATE ID)
MAKEMYTRIP_AFFILIATE_ID = "YOUR_AFFILIATE_ID_HERE"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler"""
    user = update.effective_user
    await update.message.reply_text(
        f"👋 Hello {user.first_name}!\n\n"
        "🚂 Welcome to Train Search Bot!\n\n"
        "I can help you find available trains between stations.\n\n"
        "📍 Please enter the FROM station name:\n"
        "(Example: Mumbai, Delhi, Bangalore)"
    )
    return FROM_STATION

async def from_station(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save from station and ask for to station"""
    context.user_data['from_station'] = update.message.text.strip()
    await update.message.reply_text(
        f"✅ From: {context.user_data['from_station']}\n\n"
        "📍 Now enter the TO station name:"
    )
    return TO_STATION

async def to_station(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save to station and ask for date"""
    context.user_data['to_station'] = update.message.text.strip()
    await update.message.reply_text(
        f"✅ From: {context.user_data['from_station']}\n"
        f"✅ To: {context.user_data['to_station']}\n\n"
        "📅 Enter travel date (DD-MM-YYYY):\n"
        "(Example: 15-01-2026)"
    )
    return DATE

async def search_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get date and search for trains"""
    date_text = update.message.text.strip()
    
    # Validate date format
    try:
        travel_date = datetime.strptime(date_text, "%d-%m-%Y")
        context.user_data['date'] = date_text
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid date format!\n"
            "Please use DD-MM-YYYY format (Example: 15-01-2026)"
        )
        return DATE
    
    # Show searching message
    await update.message.reply_text("🔍 Searching for trains... Please wait...")
    
    # Search trains
    from_st = context.user_data['from_station']
    to_st = context.user_data['to_station']
    date = context.user_data['date']
    
    trains = search_trains(from_st, to_st, date)
    
    if not trains:
        await update.message.reply_text(
            "❌ No trains found or unable to fetch data.\n\n"
            "Please check:\n"
            "• Station names are correct\n"
            "• Date is valid\n"
            "• Try again with different stations\n\n"
            "Type /start to search again."
        )
        return ConversationHandler.END
    
    # Format results
    response = f"🚂 *Available Trains*\n\n"
    response += f"📍 *From:* {from_st}\n"
    response += f"📍 *To:* {to_st}\n"
    response += f"📅 *Date:* {date}\n"
    response += f"━━━━━━━━━━━━━━━━━━━━\n\n"
    
    for i, train in enumerate(trains[:10], 1):  # Show max 10 trains
        response += f"*{i}. {train['name']}* ({train['number']})\n"
        response += f"   🕐 Departure: {train['departure']}\n"
        response += f"   🕐 Arrival: {train['arrival']}\n"
        response += f"   ⏱ Duration: {train['duration']}\n"
        
        if train.get('availability'):
            response += f"   💺 {train['availability']}\n"
        
        response += f"\n"
    
    # Create MakeMyTrip booking link with affiliate
    booking_url = create_affiliate_link(from_st, to_st, date)
    
    response += f"━━━━━━━━━━━━━━━━━━━━\n"
    response += f"🎫 *Book Your Ticket:*\n"
    response += f"👉 [Click here to book on MakeMyTrip]({booking_url})\n\n"
    response += f"Type /start to search again."
    
    await update.message.reply_text(response, parse_mode='Markdown', disable_web_page_preview=True)
    
    return ConversationHandler.END

def create_affiliate_link(from_station, to_station, date):
    """Create MakeMyTrip affiliate link"""
    # Convert date format from DD-MM-YYYY to DDMMYYYY
    date_obj = datetime.strptime(date, "%d-%m-%Y")
    formatted_date = date_obj.strftime("%d%m%Y")
    
    # MakeMyTrip railways URL format
    base_url = "https://www.makemytrip.com/railways"
    
    # Add affiliate parameter
    affiliate_link = f"{base_url}?from={from_station}&to={to_station}&date={formatted_date}&affiliateId={MAKEMYTRIP_AFFILIATE_ID}"
    
    return affiliate_link

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel conversation"""
    await update.message.reply_text(
        "❌ Search cancelled.\n"
        "Type /start to search again.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command"""
    help_text = (
        "🚂 *Train Search Bot Help*\n\n"
        "*Commands:*\n"
        "/start - Start searching for trains\n"
        "/help - Show this help message\n"
        "/cancel - Cancel current search\n\n"
        "*How to use:*\n"
        "1. Type /start\n"
        "2. Enter FROM station\n"
        "3. Enter TO station\n"
        "4. Enter date (DD-MM-YYYY)\n"
        "5. Get train list with booking link\n\n"
        "Happy journey! 🎫"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

def main():
    """Main function to run the bot"""
    # Get bot token from environment variable
    TOKEN = os.getenv('BOT_TOKEN')
    
    if not TOKEN:
        logger.error("BOT_TOKEN not found in environment variables!")
        return
    
    # Create application
    application = Application.builder().token(TOKEN).build()
    
    # Conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            FROM_STATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, from_station)],
            TO_STATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, to_station)],
            DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_date)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('help', help_command))
    
    # Start the bot
    logger.info("Bot started successfully!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
