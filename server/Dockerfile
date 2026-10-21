FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /service
COPY server/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY server/app.py app.py
RUN useradd --create-home --uid 10001 opsbrief && mkdir -p /data && chown opsbrief:opsbrief /data
USER opsbrief
EXPOSE 8080
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers", "--forwarded-allow-ips", "127.0.0.1", "--no-access-log"]
