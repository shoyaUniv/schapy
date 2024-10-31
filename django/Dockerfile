# FROM python:3.11-slim

# ENV PYTHONUNBUFFERED 1

# WORKDIR /code

# COPY . /code/

# RUN pip install -r requirements.txt

# RUN python /code/src/superuser.py

# ---------------------------------------------------------------

# FROM python:3.11-slim

# ENV PYTHONUNBUFFERED 1

# WORKDIR /code

# COPY . /code/
# RUN pip install -r requirements.txt

# COPY entrypoint.sh /code/entrypoint.sh
# RUN chmod +x /code/entrypoint.sh

# ENTRYPOINT ["/code/entrypoint.sh"]

# CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]

FROM python:3.11-slim

ENV PYTHONUNBUFFERED 1

WORKDIR /code

COPY requirements.txt /code/
RUN pip install -r requirements.txt

COPY entrypoint.sh /code/entrypoint.sh
RUN chmod +x /code/entrypoint.sh

COPY . /code/

ENTRYPOINT ["/code/entrypoint.sh"]

CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]