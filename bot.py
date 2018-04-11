#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from telegram.ext import Updater
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler
from telegram.ext import Filters
from telegram import ChatAction
from tinytag import TinyTag
from google.cloud import speech
from google.cloud import storage
from google.cloud.speech import enums
from google.cloud.speech import types
import os
import io

TOKEN = 'YOUR_TOKEN'
PORT = int(os.environ.get('PORT', '5002'))
BUCKET_NAME = 'YOUR_BUCKET_NAME'
updater = Updater(TOKEN)
dispatcher = updater.dispatcher


def start(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="YOUR_WELCOME_MESSAGE")


def voice_to_text(bot, update):
    chat_id = update.message.chat_id

    bot.getFile(update.message.voice.file_id).download('voice.ogg')
    tag = TinyTag.get('voice.ogg')
    length = tag.duration
    speech_client = speech.SpeechClient()

    to_gs = length > 58

    if to_gs:
        storage_client = storage.Client()

        bucket = storage_client.get_bucket(BUCKET_NAME)
        blob = bucket.blob('voice.ogg')
        blob.upload_from_filename('voice.ogg')
        audio = types.RecognitionAudio(uri='gs://' + BUCKET_NAME + '/voice.ogg')
    else:
        with io.open('voice.ogg', 'rb') as audio_file:
            content = audio_file.read()
            audio = types.RecognitionAudio(content=content)

    config = types.RecognitionConfig(
        encoding=enums.RecognitionConfig.AudioEncoding.OGG_OPUS,
        sample_rate_hertz=16000,
        language_code='ru-RU')

    bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    response = speech_client.long_running_recognize(config, audio).result(timeout=500) \
        if to_gs else \
        speech_client.recognize(config, audio)
    for result in response.results:
        bot.send_message(update.message.chat_id, result.alternatives[0].transcript)


def ping_me(bot, update, error):
    if not error.message == 'Timed out':
        bot.send_message(chat_id=123456, text=error.message) # YOUR_CHAT_ID


start_handler = CommandHandler(str('start'), start)
oh_handler = MessageHandler(Filters.voice, voice_to_text)
dispatcher.add_handler(start_handler)
dispatcher.add_handler(oh_handler)
dispatcher.add_error_handler(ping_me)
updater.start_polling()
updater.idle()
