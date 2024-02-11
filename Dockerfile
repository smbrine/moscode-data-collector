FROM --platform=linux/amd64 python:3.11-slim

WORKDIR /app

COPY . ./

ENV PYTHONPATH=./
ENV PYTHONUNBUFFERED=True
EXPOSE "$LISTEN_PORT"

RUN apt-get update && apt-get upgrade -y

RUN python -m ensurepip --upgrade && pip install --upgrade pip
RUN pip install poetry

RUN poetry config virtualenvs.create false \
  && poetry install --no-interaction --no-ansi

ENTRYPOINT ["poetry"]
CMD ["run", "python", "app/main.py"]
