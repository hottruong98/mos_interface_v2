FROM python:3.9-slim
WORKDIR /app
COPY .  /app
RUN pip install --no-cache-dir -r requirements.txt
# RUN apt-get update
# RUN apt-get install -y dnsutils
# RUN apt-get install -y iputils-ping

ENV GRPC_SERVER_PORT=50051
ENV RABBITMQ_PORT=5672

# ENV PYTHONUNBUFFERED=1
# CMD ["python", "-u", "tucson_status_pub.py"]
CMD ["python", "-u", "server_to_tucson.py"]

