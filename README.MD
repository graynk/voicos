# Voicos
Simple Telegram bot that converts voice messages to text using Google Speech. Currently can be found on [@voicos_bot](https://t.me/voicos_bot)

## Dependencies
* python-telegram-bot
* pymediainfo (and a system library libmediainfo)
* google-cloud-speech
* google-cloud-storage
* psycopg2-binary (and, well, PostgreSQL itself)

## Installation
1. Install the libraries via pip:
```
pip install -r requirements.txt
```
2. Go to [Google Cloud](https://cloud.google.com/) and set up a new project. You will need Google Speech API. 
   For messages longer than 1 minute you will also need Google Storage
3. Generate new service account and download a private key as JSON
4. Set environment variable `GOOGLE_APPLICATION_CREDENTIALS` to the file path of the JSON key 
   (see [here](https://cloud.google.com/speech-to-text/docs/quickstart-client-libraries) for more instructions)
5. Go to the Google Storage page and create a new bucket
6. Message [@BotFather](https://t.me/BotFather) on Telegram to [create a new bot](https://core.telegram.org/bots#6-botfather)
7. Set up `VOICOS_TOKEN`, `VOICOS_BUCKET` and `VOICOS_ADMIN_ID` environment variables
8. Set up PostgreSQL and change connection string in bot.py
9. Run the bot
`python3 bot.py`


## Docker support
You will need to pass your credentials JSON to the container and to pass the environment variables with tokens and such.

With PostgreSQL already set up natively (please don't leave it with open ports, I will not responsible), your run command will look something like this:

```Bash
docker run -d --restart unless-stopped --name voicos \
   --mount type=bind,source=/path/to/credentials.json,target=/app/credentials.json,readonly \ 
   --env-file voicos.env \
   ghcr.io/graynk/voicos:latest
```

To use Postgre in container as well, put `docker-compose.yml`, `credentials.json`, `voicos.env`, `data` directory and your `postgres.conf` 
in the same directory, then run:
```Bash
sudo docker-compose up &
```

Hopefully you know what you're doing and can edit `docker-compose.yml` if needed, because I don't have any desire to write a longer instruction than this.

## Usage
Launch the bot, forward the voice message, easy. Works in group chats as well. 
For messages longer than 1 minute the bot uses long recognition with uploading to Google Storage
