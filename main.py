import os
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext
from pytube import YouTube

# Load environment variables from .env file where your bot token is stored
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# Ensure you replace this with your actual token
if TELEGRAM_TOKEN is None:
    raise ValueError("No TELEGRAM_TOKEN found in your .env file")

def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('Hello! Send me a YouTube URL and select the resolution to download.')

def ask_for_resolution(update: Update, context: CallbackContext) -> None:
    url = update.message.text
    context.user_data['url'] = url  # Store the URL in the user data dictionary

    # Inline keyboard options for different video resolutions
    keyboard = [
        [InlineKeyboardButton("144p", callback_data='144'),
         InlineKeyboardButton("240p", callback_data='240')],
        [InlineKeyboardButton("360p", callback_data='360'),
         InlineKeyboardButton("480p", callback_data='480')],
        [InlineKeyboardButton("720p", callback_data='720'),
         InlineKeyboardButton("1080p", callback_data='1080')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Please choose your desired resolution:', reply_markup=reply_markup)

def download_video(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()  # Stop the loading animation on the button
    resolution = query.data
    url = context.user_data.get('url')

    try:
        yt = YouTube(url)
        video = yt.streams.filter(res=f"{resolution}p").first()
        if video:
            # Here you would implement the download functionality
            # For instance, video.download(filename=f"{yt.title}.mp4")
            query.edit_message_text(text=f"Downloading video at {resolution}p...")
        else:
            query.edit_message_text(text="Sorry, the requested resolution is not available.")
    except Exception as e:
        query.edit_message_text(text=f"An error occurred: {e}")

def main() -> None:
    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher

    # Add command and message handlers
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, ask_for_resolution))
    dp.add_handler(CallbackQueryHandler(download_video))

    # Start the bot
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
