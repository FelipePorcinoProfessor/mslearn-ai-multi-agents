FROM python:3.13-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY dashboard ./dashboard
COPY src ./src

ENV PORT=8000
EXPOSE 8000
CMD ["python", "-m", "dashboard.app"]
