# Voicos
Simple Telegram bot that converts voice messages to text using Google Speech. Currently can be found on [@voicos_bot](https://t.me/voicos_bot)

## Dependencies
* python-telegram-bot
* pymediainfo (and a system library libmediainfo)
* google-cloud-speech
* google-cloud-storage

## Installation
1. Install the libraries via pip:
```
pip install -r requirements.txt
```
2. Go to [Google Cloud](https://cloud.google.com/) and set up a new project. You will need Google Speech API. 
   For messages longer than 1 minute you will also need Google Storage
2. Generate new service account and download a private key as JSON
2. Set environment variable `GOOGLE_APPLICATION_CREDENTIALS` to the file path of the JSON key 
   (see [here](https://cloud.google.com/speech-to-text/docs/quickstart-client-libraries) for more instructions)
2. Go to the Google Storage page and create a new bucket
2. Message [@BotFather](https://t.me/BotFather) on Telegram to [create a new bot](https://core.telegram.org/bots#6-botfather)
2. Set up `VOICOS_TOKEN`, `VOICOS_BUCKET` and `VOICOS_ADMIN_ID` environment variables
2. Run the bot
`python3 bot.py`


## Docker support
You will need to pass your credentials JSON to the container and to pass the environment variables with tokens and such.

Run command will look something like this:

```
docker run -d --restart unless-stopped --name voicos \
   -v /path/to/credentials.json:/app/credentials.json \
   -e GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json \
   -e VOICOS_TOKEN -e VOICOS_BUCKET -e VOICOS_ADMIN_ID \
   ghcr.io/graynk/voicos
```

## Usage
Launch the bot, forward the voice message, easy. Works in group chats as well. 
For messages longer than 1 minute the bot uses long recognition with uploading to Google Storage
