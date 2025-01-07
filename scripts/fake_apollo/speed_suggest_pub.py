import pika
import json
import time
import threading
import logging

# rabbitmq_service_endpoint = '143.248.55.76'
# rabbitmq_port = 30672
rabbitmq_service_endpoint = 'mos-rabbitmqcluster.default.svc.cluster.local'
rabbitmq_port = 5672
rabbitmq_user = 'mos'
rabbitmq_password = 'mos'

credentials = pika.PlainCredentials(rabbitmq_user, rabbitmq_password)
parameters = pika.ConnectionParameters(
    host=rabbitmq_service_endpoint,
    port=rabbitmq_port,
    virtual_host='/',
    credentials=credentials
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Function to send messages to the 'speed_suggest' queue
def send_speed_suggest(channel):
    while True:
        message = {'suggested_speed': 10.0}  # Example data, adjust as needed
        channel.basic_publish(
            exchange='',  # Direct exchange (default)
            routing_key='speed_suggest',  # Queue name
            body=json.dumps(message)  # Convert message to JSON
        )
        logging.info(f"Sent message to 'speed_suggest' queue: {message}")
        time.sleep(0.5)  # Adjust sleep time as needed to control the rate

# Function to send messages to the 'traffic_situation' queue
def send_traffic_situation(channel):
    while True:
        message = {'traffic_condition': 'clear'}  # Example data, adjust as needed
        channel.basic_publish(
            exchange='',  # Direct exchange (default)
            routing_key='traffic_situation',  # Queue name
            body=json.dumps(message)  # Convert message to JSON
        )
        logging.info(f"Sent message to 'traffic_situation' queue: {message}")
        time.sleep(1)  # Adjust sleep time as needed to control the rate

def main():
    # Establish connection and create a channel
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()

    # Declare the queues (ensure they exist)
    channel.queue_declare(queue='speed_suggest', arguments = {'message-ttl': 0})
    # channel.queue_declare(queue='traffic_situation')

    # Start threads for sending messages to both queues concurrently
    speed_suggest_thread = threading.Thread(target=send_speed_suggest, args=(channel,))
    # traffic_situation_thread = threading.Thread(target=send_traffic_situation, args=(channel,))

    # Start both threads
    speed_suggest_thread.start()
    # traffic_situation_thread.start()

    # Join both threads to keep the main program alive until it's interrupted
    speed_suggest_thread.join()
    # traffic_situation_thread.join()

if __name__ == '__main__':
    main()
