# syntax=docker/dockerfile:1

FROM python:3.8-slim-buster

WORKDIR .

RUN apt-get update && apt-get upgrade -y

COPY requirements.txt requirements.txt

RUN pip3 install --upgrade pip
RUN pip3 install -r requirements.txt

COPY . .

ENV SPOTIPY_CLIENT_ID=""
ENV SPOTIPY_CLIENT_SECRET=""
ENV SPOTIPY_REDIRECT_URI=""

CMD [ "python3", "-u", "main.py" ]