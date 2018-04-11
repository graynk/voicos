# Voicos
Simple Telegram bot that converts voice messages to text using Google Speech

## Dependencies
python-telegram-bot

TinyTag

google-cloud

## Installation
1. Install the libraries via pip:

`pip install --upgrade python-telegram-bot`

`pip install --upgrade TinyTag`

`pip install --upgrade google-cloud`
2. Go to [https://cloud.google.com/](Google Cloud) and set up a new project. You will need Google Speech API and Google Storage
3. Generate new service account and download a private key as JSON
4. Set environment variable GOOGLE_APPLICATION_CREDENTIALS to the file path of the JSON key (see [https://cloud.google.com/speech-to-text/docs/quickstart-client-libraries](here) for more instructions)
5. Install [https://cloud.google.com/sdk/docs/](gcloud) tool and follow the instructions to authenicate
6. Go to the Google Storage page and create a new bucket
7. Message [https://t.me/BotFather](@BotFather) on Telegram to [https://core.telegram.org/bots#6-botfather](create a new bot)
8. Fill the necessary constants in bot.py with your token and bucket names
9. Run the bot

`python3 bot.py`

## Usage
Launch the bot, forward the voice message, easy. Works in group chats as well.
