#!/usr/bin/env python
# -*- coding: utf-8 -*-
import io
import os
import subprocess
from typing import List

import psycopg2
from google.cloud import storage
from google.cloud.speech import SpeechClient, RecognitionConfig, RecognitionAudio, RecognizeResponse
from pymediainfo import MediaInfo
from telegram import ChatAction, Update, Message
from telegram.constants import MAX_MESSAGE_LENGTH
from telegram.error import TimedOut
from telegram.ext import CommandHandler
from telegram.ext import Filters
from telegram.ext import MessageHandler
from telegram.ext import Updater, CallbackContext

from DateFilter import DateFilter

SUPPORTED_SAMPLE_RATES = [8000, 12000, 16000, 24000, 48000]
RESAMPLE_RATE = 48000
UPLOAD_LIMIT = 58  # everything longer than a minute we have to upload to bucket. More than 58 seconds to be sure
MY_NERVES_LIMIT = 5 * 60  # five minutes is all you get bruh. don't be tellin stories
POLITE_RESPONSE = 'Sorry, but no messages longer than 5 minutes.'

TOKEN = os.getenv('VOICOS_TOKEN')
BUCKET_NAME = os.getenv('VOICOS_BUCKET')
ADMIN_CHAT_ID = int(os.getenv('VOICOS_ADMIN_ID'))
PORT = int(os.environ.get('PORT', '5002'))
if not TOKEN or not BUCKET_NAME or not os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
    exit('Check your environment variables')
updater = Updater(TOKEN)
dispatcher = updater.dispatcher
speech_client = SpeechClient()
storage_client = storage.Client()
conn = psycopg2.connect('host=localhost dbname=voicos user=postgres password=bruhpostgres')


def start(update: Update, context: CallbackContext) -> None:
    update.effective_message.reply_text("Say stuff, I'll transcribe.\n\nYou can also reply to the voice message with "
                                        "the language code like en-US/ru-RU/something else to use that language when "
                                        "transcribing")


def voice_to_text(update: Update, context: CallbackContext) -> None:
    message = update.effective_message
    if message.voice.duration > MY_NERVES_LIMIT:
        message.reply_text(POLITE_RESPONSE, quote=True)
        return

    chat_id = update.effective_message.chat.id
    file_name = '%s_%s%s.ogg' % (chat_id, update.message.from_user.id, update.message.message_id)
    download_and_prep(file_name, message)

    transcriptions = transcribe(file_name, update.message)

    if len(transcriptions) == 0 or transcriptions[0] == '':
        message.reply_text('Transcription results are empty. You can try setting language manually by '
                           'replying to the voice message with the language code like ru-RU or en-US',
                           quote=True)
        return

    for transcription in transcriptions:
        message.reply_text(transcription, quote=True)


def transcribe_with_langcode(update: Update, context: CallbackContext) -> None:
    message = update.effective_message
    if len(message.text) != 5:
        return

    reply_message = message.reply_to_message
    if not reply_message.voice:
        return

    voice = reply_message.voice
    if voice.duration > MY_NERVES_LIMIT:
        message.reply_text(POLITE_RESPONSE, quote=True)
        return

    file_name = '%s_%s%s.ogg' % (message.chat_id, reply_message.from_user.id, reply_message.message_id)
    download_and_prep(file_name, reply_message)

    transcriptions = transcribe(file_name, reply_message, lang_code=message.text, alternatives=[])

    if len(transcriptions) == 0 or transcriptions[0] == '':
        message.reply_text('Welp. Transcription results are still empty, but we tried, right?',
                           quote=True)
        return
    for transcription in transcriptions:
        message.reply_text(transcription, quote=True)


def ping_me(update: Update, context: CallbackContext) -> None:
    if context.error is not TimedOut:
        err = str(context.error)
        print(err)
        if len(err) > 4000:
            return
        context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=err)


def transcribe(file_name: str, message: Message, lang_code: str = 'ru-RU', alternatives: List[str] = ['en-US', 'uk-UA']) -> List[str]:
    media_info = MediaInfo.parse(file_name)
    if len(media_info.audio_tracks) != 1 or not hasattr(media_info.audio_tracks[0], 'sampling_rate'):
        os.remove(file_name)
        raise ValueError('Failed to detect sample rate')
    actual_duration = round(media_info.audio_tracks[0].duration / 1000)

    sample_rate = media_info.audio_tracks[0].sampling_rate
    encoding = RecognitionConfig.AudioEncoding.OGG_OPUS
    if sample_rate not in SUPPORTED_SAMPLE_RATES:
        message.reply_text('Your voice message has a sample rate of {} Hz which is not in the list '
                           'of supported sample rates ({}).\n\nI will try to resample it, '
                           'but this may reduce recognition accuracy'
                           .format(sample_rate,
                                   ', '.join(str(int(rate / 1000)) + ' kHz' for rate in SUPPORTED_SAMPLE_RATES)
                                   ),
                           quote=True)
        message.reply_chat_action(action=ChatAction.TYPING)
        encoding, file_name, sample_rate = resample(file_name)
    config = RecognitionConfig(
        encoding=encoding,
        sample_rate_hertz=sample_rate,
        enable_automatic_punctuation=True,
        language_code=lang_code,
        alternative_language_codes=alternatives,
    )

    try:
        response = upload_to_gs(file_name, config) \
            if actual_duration > UPLOAD_LIMIT \
            else regular_upload(file_name, config)
    except Exception as e:
        print(e)
        os.remove(file_name)
        return ['Failed']

    with conn.cursor() as cur:
        cur.execute("insert into customer(user_id) values (%s) on conflict (user_id) do nothing;",
                    (message.chat_id,))
        cur.execute("update customer set balance = balance - (%s) where user_id = (%s);",
                    (actual_duration, message.chat_id))
        cur.execute("insert into stat(user_id, message_timestamp, duration) values (%s, current_timestamp, %s);",
                    (message.chat_id, actual_duration))
        conn.commit()

    os.remove(file_name)

    message_text = ''
    for result in response.results:
        message_text += result.alternatives[0].transcript + '\n'

    return split_long_message(message_text)


def regular_upload(file_name: str, config: RecognitionConfig) -> RecognizeResponse:
    with io.open(file_name, 'rb') as audio_file:
        content = audio_file.read()
    audio = RecognitionAudio(content=content)
    return speech_client.recognize(config=config, audio=audio)


def upload_to_gs(file_name: str, config: RecognitionConfig) -> RecognizeResponse:
    bucket = storage_client.get_bucket(bucket_or_name=BUCKET_NAME)

    blob = bucket.blob(file_name)
    blob.upload_from_filename(file_name)
    audio = RecognitionAudio(uri='gs://%s/%s' % (BUCKET_NAME, file_name))
    response = speech_client.long_running_recognize(config=config, audio=audio).result(timeout=500)
    blob.delete()

    return response


def split_long_message(text: str) -> List[str]:
    length = len(text)
    if length < MAX_MESSAGE_LENGTH:
        return [text]

    results = []
    for i in range(0, length, MAX_MESSAGE_LENGTH):
        results.append(text[i:MAX_MESSAGE_LENGTH])

    return results


def download_and_prep(file_name: str, message: Message) -> None:
    message.voice.get_file().download(file_name)
    message.reply_chat_action(action=ChatAction.TYPING)


def resample(file_name) -> (RecognitionConfig.AudioEncoding, str, int):
    new_file_name = file_name + '.raw'

    cmd = [
        'ffmpeg',
        '-loglevel', 'quiet',
        '-i', file_name,
        '-f', 's16le',
        '-acodec', 'pcm_s16le',
        '-ar', str(RESAMPLE_RATE),
        new_file_name
    ]

    try:
        subprocess.run(args=cmd)
    except Exception as e:
        os.remove(file_name)
        raise e

    return RecognitionConfig.AudioEncoding.LINEAR16, new_file_name, RESAMPLE_RATE


if __name__ == '__main__':
    with conn.cursor() as cur:
        cur.execute("create table if not exists customer (user_id bigint primary key, balance integer default 1200);")
        cur.execute("create table if not exists stat (id serial primary key, user_id bigint references customer(user_id), message_timestamp timestamp, duration integer);")
        conn.commit()

    start_handler = CommandHandler('start', start)
    voice_handler = MessageHandler(Filters.voice & DateFilter(), voice_to_text, run_async=True)
    language_handler = MessageHandler(Filters.reply & Filters.text & DateFilter(), transcribe_with_langcode,
                                      run_async=True)

    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(voice_handler)
    dispatcher.add_handler(language_handler)
    dispatcher.add_error_handler(ping_me)

    updater.start_polling()
    updater.idle()
