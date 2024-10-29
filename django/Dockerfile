FROM python:3.11-slim 

ENV PYTHONUNBUFFERED 1 

WORKDIR /code 

COPY django/requirements.txt /code/requirements.txt

RUN pip install -r requirements.txt 

COPY . /code/
