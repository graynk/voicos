#!/usr/bin/env python
# -*- coding: utf-8 -*-
from telegram.ext import Updater, CallbackContext
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler
from telegram.ext import Filters
from telegram.error import TimedOut
from telegram import ChatAction, Update, Message
import os
import boto3
import time
import requests

from DateFilter import DateFilter

TOKEN = os.getenv('VOICOS_TOKEN')
BUCKET_NAME = os.getenv('VOICOS_BUCKET')
ADMIN_CHAT_ID = int(os.getenv('VOICOS_ADMIN_ID'))
PORT = int(os.environ.get('PORT', '5002'))
if not TOKEN or not BUCKET_NAME:
    exit('Check your environment variables')
updater = Updater(TOKEN)
dispatcher = updater.dispatcher
s3 = boto3.client('s3')
transcribe_client = boto3.client('transcribe')


def start(update: Update, context: CallbackContext) -> None:
    update.effective_message.reply_text("Say stuff, I'll transcribe.")


def voice_to_text(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_message.chat.id
    file_name = '%s_%s%s.ogg' % (chat_id, update.message.from_user.id, update.message.message_id)
    update.effective_message.voice.get_file().download(file_name)

    message_text = transcribe(file_name, update.message)

    if message_text == '':
        update.effective_message.reply_text('Transcription results are empty',
                                            quote=True)
        return
    update.effective_message.reply_text(message_text, quote=True)


def ping_me(update: Update, context: CallbackContext) -> None:
    update.effective_message.reply_text('Failed')
    if context.error is not TimedOut:
        err = str(context.error)
        print(err)
        if len(err) > 4000:
            return
        context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=err)


def transcribe(file_name: str, message: Message):
    try:
        response = s3.put_object(Bucket=BUCKET_NAME, Key=file_name, Body=open(file_name, 'rb'))
        # TODO: check actual response
        response = transcribe_client.start_transcription_job(
            TranscriptionJobName=file_name,
            Media={'MediaFileUri': 's3://{}/{}'.format(BUCKET_NAME, file_name)},
            IdentifyLanguage=True,
            MediaFormat='ogg',
            LanguageOptions=[
                'ru-RU', 'en-US',
            ]
        )
        while response['TranscriptionJob']['TranscriptionJobStatus'] == 'IN_PROGRESS':
            message.reply_chat_action(action=ChatAction.TYPING)
            time.sleep(5)  # TODO: da fuck is a waiter
            response = transcribe_client.get_transcription_job(
                TranscriptionJobName=file_name
            )
        response = requests.get(response['TranscriptionJob']['Transcript']['TranscriptFileUri']).json()
        s3.delete_object(
            Bucket=BUCKET_NAME,
            Key=file_name,
        )
    except Exception as e:
        os.remove(file_name)
        raise e

    os.remove(file_name)

    message_text = ''
    for result in response['results']['transcripts']:
        message_text += result['transcript'] + '\n'

    return message_text


if __name__ == '__main__':
    start_handler = CommandHandler('start', start)
    voice_handler = MessageHandler(Filters.voice & DateFilter(), voice_to_text, run_async=True)

    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(voice_handler)
    dispatcher.add_error_handler(ping_me)

    updater.start_polling()
    updater.idle()
