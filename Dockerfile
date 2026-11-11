# Public deployment (e.g. Render, Railway, Fly.io). Locally you do not need this: run `py app.py`.
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn==23.0.0
COPY . .
# full version (collect any area, websites + AI). Set TC_PUBLIC_DEMO=1 for a read-only copy.
ENV TC_PUBLIC_DEMO=0 PORT=10000
# one worker: background jobs keep their state in memory
CMD gunicorn -w 1 --threads 8 -b 0.0.0.0:$PORT app:app
