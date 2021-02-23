#!/usr/bin/env python
# -*- coding: utf-8 -*-
from telegram.ext import Updater, CallbackContext
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler
from telegram.ext import Filters
from telegram.error import TimedOut
from telegram import ChatAction, Update
from google.cloud import speech
from google.cloud import storage
from pymediainfo import MediaInfo
import os
import io

TOKEN = os.getenv('VOICOS_TOKEN')
BUCKET_NAME = os.getenv('VOICOS_BUCKET')
ADMIN_CHAT_ID = int(os.getenv('VOICOS_ADMIN_ID'))
PORT = int(os.environ.get('PORT', '5002'))
if not TOKEN or not BUCKET_NAME or not os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
    exit('Check your environment variables')
updater = Updater(TOKEN)
dispatcher = updater.dispatcher
speech_client = speech.SpeechClient()
storage_client = storage.Client()


def start(update: Update, context: CallbackContext) -> None:
    update.effective_message.reply_text("Say stuff, I'll transcribe")


def voice_to_text(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat.id
    file_name = '%s_%s%s.ogg' % (chat_id, update.message.from_user.id, update.message.message_id)

    update.message.voice.get_file().download(file_name)
    media_info = MediaInfo.parse(file_name)
    if len(media_info.audio_tracks) != 1 or not hasattr(media_info.audio_tracks[0], 'sampling_rate'):
        os.remove(file_name)
        raise ValueError('Failed to parse sample rate')
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.OGG_OPUS,
        sample_rate_hertz=media_info.audio_tracks[0].sampling_rate,
        language_code='ru-RU')

    update.effective_message.reply_chat_action(action=ChatAction.TYPING)

    to_gs = update.message.voice.duration > 58

    try:
        if to_gs:
            bucket = storage_client.get_bucket(bucket_or_name=BUCKET_NAME)
            blob = bucket.blob(file_name)
            blob.upload_from_filename(file_name)
            audio = speech.RecognitionAudio(uri='gs://%s/%s' % (BUCKET_NAME, file_name))
            response = speech_client.long_running_recognize(config=config, audio=audio).result(timeout=500)
            blob.delete()
        else:
            with io.open(file_name, 'rb') as audio_file:
                content = audio_file.read()
            audio = speech.RecognitionAudio(content=content)
            response = speech_client.recognize(config=config, audio=audio)
    except Exception as e:
        os.remove(file_name)
        raise e

    os.remove(file_name)
    
    message_text = ''
    for result in response.results:
        message_text += result.alternatives[0].transcript + '\n'

    update.effective_message.reply_text(message_text)


def ping_me(update: Update, context: CallbackContext) -> None:
    update.effective_message.reply_text('Failed')
    if context.error is not TimedOut:
        context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=str(context.error))


if __name__ == '__main__':
    start_handler = CommandHandler('start', start)
    voice_handler = MessageHandler(Filters.voice, voice_to_text, run_async=True)
    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(voice_handler)
    dispatcher.add_error_handler(ping_me)
    updater.start_polling()
    updater.idle()
