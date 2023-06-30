# syntax=docker/dockerfile:1

FROM python:3.11.4-slim-bookworm

WORKDIR .

RUN apt-get update && apt-get upgrade -y

COPY requirements.txt requirements.txt

RUN pip3 install --upgrade pip
RUN pip3 install -r requirements.txt

COPY . .

CMD [ "python3", "-u", "app.py" ]