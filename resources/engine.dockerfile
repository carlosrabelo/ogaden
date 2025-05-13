FROM python:3.9-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY resources/engine.requirements.txt requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

COPY broker.py loader.py engine.py trader.py ./

CMD [ "python", "engine.py" ]
