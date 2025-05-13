FROM python:3.9-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY resources/dashboard.requirements.txt requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

COPY dashboard.py .

RUN mkdir -p templates

COPY templates/*.html templates/

CMD ["python", "dashboard.py"]
