import os
import logging
from pytube import YouTube, exceptions as pytube_exceptions
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext
import subprocess
from movies_scraper import get_movie, search_movies, url_list
import random

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def start(update: Update, context: CallbackContext):
    update.message.reply_text('Welcome to the YouTube / Movie Downloader Bot!')

def help_command(update: Update, context: CallbackContext):
    """Send the message when the command /help is issued."""
    update.message.reply_text('This bot can help you download YouTube videos. \n'
                              'Commands:\n'
                              '/start - Start the bot and get a welcome message.\n'
                              '/link <YouTube URL> - Download the video directly from the provided link.\n'
                              '/help - Get help on how to use the bot.\n'
                              '/search <Movie Name> - Scrape A Movie link for u , u can directly download Movie from it.')


def link(update: Update, context: CallbackContext):
    url = update.message.text.strip()
    if not url:
        update.message.reply_text('Please provide a valid YouTube URL.')
        return
    try:
        yt = YouTube(url)
        context.user_data['yt'] = yt  # Store YouTube object for later use
        show_download_options(update, yt)
    except pytube_exceptions.PytubeError as e:
        logger.error(f"Failed to fetch video data: {e}")
        update.message.reply_text('Failed to fetch video data. Please check the URL and try again.')

def show_download_options(update, yt):
    video_title = yt.title
    keyboard = [
        [InlineKeyboardButton("MP3 (Audio)", callback_data='mp3')],
        [InlineKeyboardButton("360p", callback_data='360p')],
        [InlineKeyboardButton("720p", callback_data='720p')],
        [InlineKeyboardButton("1080p", callback_data='1080p')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(f'Title: {video_title}\nChoose your download option:', reply_markup=reply_markup)

def youtube_button(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    if 'yt' not in context.user_data:
        query.edit_message_text(text="Session expired or invalid, please send the URL again.")
        return

    yt = context.user_data['yt']
    choice = query.data

    download_folder = 'downloads'
    os.makedirs(download_folder, exist_ok=True)

    if choice == 'mp3':
        download_audio(update, yt, download_folder)
    else:
        download_video(update, yt, choice, download_folder)


def download_audio(update, yt, download_folder):
    query = update.callback_query
    try:
        audio_stream = yt.streams.get_audio_only()
        if not audio_stream:
            query.edit_message_text(text="Audio stream is not available.")
            return

        query.edit_message_text(text="Downloading audio...")
        filename = audio_stream.download(output_path=download_folder)
        query.edit_message_text(text="Audio downloaded. Converting to MP3...")

        new_filename = convert_to_mp3(filename)
        query.edit_message_text(text="Audio converted. Sending to Telegram...")

        send_file(update, new_filename, 'audio')
    except Exception as e:
        logger.error(f"Failed to process audio: {e}")

def download_video(update, yt, resolution, download_folder):
    query = update.callback_query
    try:
        if resolution == '1080p':
            download_high_resolution(update, yt, download_folder)
        else:
            video_stream = yt.streams.filter(res=resolution, progressive=True, file_extension='mp4').first()
            if not video_stream:
                query.edit_message_text(text=f"{resolution} video stream is not available.")
                return

            query.edit_message_text(text=f"Downloading {resolution} video...")
            filename = video_stream.download(output_path=download_folder)
            query.edit_message_text(text=f"{resolution} video downloaded. Sending to Telegram...")

            send_file(update, filename, 'video')
    except Exception as e:
        logger.error(f"Failed to process video: {e}")
        query.edit_message_text(text=f"Failed to process video: {e}")

def download_high_resolution(update, yt, download_folder):
    try:
        # Fetch the best quality video-only stream and the best audio stream
        video_stream = yt.streams.filter(res='1080p', only_video=True, file_extension='mp4').order_by('fps').desc().first()
        audio_stream = yt.streams.filter(only_audio=True).order_by('abr').desc().first()

        if not video_stream or not audio_stream:
            update.callback_query.edit_message_text(text="1080p video or audio stream is not available.")
            return

        video_filename = video_stream.download(output_path=download_folder, filename_prefix='video_')
        audio_filename = audio_stream.download(output_path=download_folder, filename_prefix='audio_')

        if not os.path.exists(video_filename) or not os.path.exists(audio_filename):
            update.callback_query.edit_message_text(text="Failed to download video or audio stream.")
            return

        new_filename = mux_audio_video(video_filename, audio_filename, download_folder)
        send_file(update, new_filename, 'video')
    except Exception as e:
        logger.error(f"Failed to download or process 1080p video: {e}")
        update.callback_query.edit_message_text(text=f"Error processing 1080p video: {e}")

def convert_to_mp3(filename):
    base, _ = os.path.splitext(filename)
    new_filename = f"{base}.mp3"
    subprocess.run(['ffmpeg', '-i', filename, new_filename], check=True)
    os.remove(filename)
    return new_filename

def mux_audio_video(video_filename, audio_filename, download_folder):
    base = os.path.splitext(video_filename)[0]
    new_filename = f"{base}_1080p.mp4"
    subprocess.run(['ffmpeg', '-i', video_filename, '-i', audio_filename, '-c:v', 'copy', '-c:a', 'aac', new_filename], check=True)
    os.remove(video_filename)
    os.remove(audio_filename)
    return new_filename

def send_file(update, filename, file_type):
    query = update.callback_query
    try:
        with open(filename, 'rb') as file:
            if file_type == 'audio':
                query.message.reply_audio(audio=file)
                query.edit_message_text(text='Audio sent successfully!')
            elif file_type == 'video':
                query.message.reply_video(video=file)
                query.edit_message_text(text='Video sent successfully!')
    except Exception as e:
        query.edit_message_text(text=f"Failed to send {file_type}: {e}")
    finally:
        os.remove(filename)  # Clean up the file regardless of success or failure

def search_movies_command(update: Update, context: CallbackContext):
    movie_name = ' '.join(context.args)
    if movie_name:
        results = search_movies(movie_name)  # The scraping function from your scraper code
        if results:
            keyboard = [[InlineKeyboardButton(movie['title'], callback_data=movie['id'])] for movie in results]
            reply_markup = InlineKeyboardMarkup(keyboard)
            update.message.reply_text('Please choose:', reply_markup=reply_markup)
        else:
            update.message.reply_text('No movies found. Try another search.')
    else:
        update.message.reply_text('Usage: /search <movie name>')

def handle_movie_selection(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    movie_id = query.data
    movie_details = get_movie(movie_id)  # The function from your scraper code to get movie details
    if movie_details and movie_details.get('links'):
        # Instead of sending a message with the link, you can forward the file from a channel
        try:
            context.bot.forward_message(chat_id=update.effective_chat.id,
                                        from_chat_id="@channelusername",  # Replace with your channel username
                                        message_id=movie_details['links']['file_message_id'])
        except Exception as e:
            update.message.reply_text(f"An error occurred: {e}")
    else:
        query.edit_message_text('Sorry, could not retrieve the movie details.')

def movie_button(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    movie_id = query.data

    if movie_id not in url_list:
        query.edit_message_text(text="Movie details are currently unavailable or the movie ID is incorrect.")
        return

    movie_details = get_movie(movie_id)
    if movie_details and 'links' in movie_details:
        keyboard = [[InlineKeyboardButton(text=key, url=value) for key, value in movie_details['links'].items()]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        try:
            context.bot.send_photo(chat_id=query.message.chat_id, photo=movie_details['img'],
                                   caption=f"Selected: {movie_details['title']}", reply_markup=reply_markup)
            query.message.delete()  # Optional: Remove the original message
        except Exception as e:
            query.edit_message_text(text=f"Failed to send movie details or delete message: {str(e)}")
    else:
        query.edit_message_text(text="Sorry, could not retrieve the movie details.")


def main():
    # Replace with your actual Telegram Bot Token
    TOKEN = 'TOKEN'
    updater = Updater(TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('help', help_command))
    dispatcher.add_handler(CommandHandler('link', link))
    dispatcher.add_handler(CallbackQueryHandler(youtube_button, pattern='^(mp3|360p|720p|1080p)$'))
    dispatcher.add_handler(CallbackQueryHandler(movie_button))  # Handles all other callbacks not matched by the above
    dispatcher.add_handler(CommandHandler('search', search_movies_command))
    dispatcher.add_handler(CallbackQueryHandler(handle_movie_selection))


    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
