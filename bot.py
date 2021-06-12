#!/usr/bin/env python
# -*- coding: utf-8 -*-
from telegram.ext import Updater, CallbackContext
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler
from telegram.ext import Filters
from telegram.error import TimedOut
from telegram import ChatAction, Update, Message, Voice
from google.cloud import speech
from google.cloud import storage
from pymediainfo import MediaInfo
import os
import io

from DateFilter import DateFilter

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
    update.effective_message.reply_text("Say stuff, I'll transcribe.\n\nYou can also reply to the voice message with "
                                        "the language code like en-US/ru-RU/something else to use that language when "
                                        "transcribing")


def transcribe_with_langcode(update: Update, context: CallbackContext) -> None:
    message = update.effective_message
    if len(message.text) != 5:
        return

    reply_message = message.reply_to_message
    if not reply_message.voice:
        return
    file_name = '%s_%s%s.ogg' % (update.effective_message.chat_id, reply_message.from_user.id, reply_message.message_id)
    to_gs = download_and_prep(file_name, update.effective_message, reply_message.voice)

    message_text = transcribe(file_name, to_gs, lang_code=message.text)

    if message_text == '':
        update.effective_message.reply_text('Welp. Transcription results are still empty, but we tried, right?')
        return
    update.effective_message.reply_text(message_text)


def voice_to_text(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_message.chat.id
    file_name = '%s_%s%s.ogg' % (chat_id, update.message.from_user.id, update.message.message_id)
    to_gs = download_and_prep(file_name, update.effective_message, update.effective_message.voice)

    message_text = transcribe(file_name, to_gs)

    if message_text == '':
        update.effective_message.reply_text('Transcription results are empty. You can try setting language manually by '
                                            'replying to the voice message with the language code like ru-RU or en-US')
        return
    update.effective_message.reply_text(message_text)


def ping_me(update: Update, context: CallbackContext) -> None:
    update.effective_message.reply_text('Failed')
    if context.error is not TimedOut:
        err = str(context.error)
        print(err)
        if len(err) > 4000:
            return
        context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=err)


def transcribe(file_name: str, to_gs: bool, lang_code: str = 'ru-RU'):
    media_info = MediaInfo.parse(file_name)
    if len(media_info.audio_tracks) != 1 or not hasattr(media_info.audio_tracks[0], 'sampling_rate'):
        os.remove(file_name)
        raise ValueError('Failed to parse sample rate')
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.OGG_OPUS,
        sample_rate_hertz=media_info.audio_tracks[0].sampling_rate,
        enable_automatic_punctuation=True,
        language_code=lang_code)

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

    return message_text


def download_and_prep(file_name: str, message: Message, voice: Voice) -> bool:
    voice.get_file().download(file_name)
    message.reply_chat_action(action=ChatAction.TYPING)
    return voice.duration > 58


if __name__ == '__main__':
    start_handler = CommandHandler('start', start)
    voice_handler = MessageHandler(Filters.voice & DateFilter(), voice_to_text, run_async=True)
    language_handler = MessageHandler(Filters.reply & Filters.text & DateFilter(), transcribe_with_langcode, run_async=True)

    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(voice_handler)
    dispatcher.add_handler(language_handler)
    dispatcher.add_error_handler(ping_me)

    updater.start_polling()
    updater.idle()
