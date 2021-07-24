FROM python:3.9-slim-buster

COPY bot.py /app/bot.py
COPY DateFilter.py /app/DateFilter.py
COPY requirements.txt /

RUN apt-get update && apt-get install libmediainfo0v5 ffmpeg -y
RUN pip3 install -r requirements.txt

WORKDIR app

ENTRYPOINT ["python3", "bot.py"]