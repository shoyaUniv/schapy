FROM python:3.11-slim

ENV PYTHONUNBUFFERED 1

WORKDIR /code

COPY . /code/

RUN pip install -r requirements.txt

RUN python /code/src/superuser.py
