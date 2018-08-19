# Voicos
Simple Telegram bot that converts voice messages to text using Google Speech. Currently can be found on [@voicos_bot](https://t.me/voicos_bot)

## Dependencies
* python-telegram-bot
* TinyTag
* google-cloud

## Installation
1. Install the libraries via pip:
```
pip install --upgrade python-telegram-bot
pip install --upgrade TinyTag
pip install --upgrade google-cloud
pip install --upgrade google-cloud-speech
pip install --upgrade google-cloud-storage
```
2. Go to [Google Cloud](https://cloud.google.com/) and set up a new project. You will need Google Speech API. For messages longer than 1m you will also need Google Storage
3. Generate new service account and download a private key as JSON
4. Set environment variable _GOOGLE_APPLICATION_CREDENTIALS_ to the file path of the JSON key (see [here](https://cloud.google.com/speech-to-text/docs/quickstart-client-libraries) for more instructions)
5. Install [gcloud](https://cloud.google.com/sdk/docs/) tool and follow the instructions to authenicate
6. Go to the Google Storage page and create a new bucket
7. Message [@BotFather](https://t.me/BotFather) on Telegram to [create a new bot](https://core.telegram.org/bots#6-botfather)
8. Fill the necessary constants in bot.py with your token and bucket names
9. Run the bot
`python3 bot.py`

## Usage
Launch the bot, forward the voice message, easy. Works in group chats as well. For messages longer than 1 minute the bot uses long recognition with uploading to Google Storage
