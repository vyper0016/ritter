FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot.py ritter_api.py ./

# bot.py only uses /app/data if it exists; mount a volume here to persist connections/config
RUN mkdir -p /app/data
VOLUME /app/data

CMD ["python", "bot.py"]
