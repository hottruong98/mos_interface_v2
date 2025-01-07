FROM python:3.9-slim
WORKDIR /app
COPY .  /app
RUN pip install --no-cache-dir -r requirements.txt

ENV GRPC_SERVER_PORT=50051
ENV RABBITMQ_PORT=5672

# ENV PYTHONUNBUFFERED=1
CMD ["python", "-u", "speed_suggest_pub.py"]