#!/usr/bin/env python3
import pika
import logging
import json
import time
import threading
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
rabbitmq_service_endpoint = os.environ.get('RABBITMQ_HOST', '143.248.55.76')
rabbitmq_port = os.environ.get('RABBITMQ_PORT', 30672)
rabbitmq_user = 'mos'
rabbitmq_password = 'mos'
credentials = pika.PlainCredentials(rabbitmq_user, rabbitmq_password)
parameters = pika.ConnectionParameters(
    host=rabbitmq_service_endpoint,
    port=rabbitmq_port,
    virtual_host='/',
    credentials=credentials
)
SPEED_SUGGEST_QUEUE = os.environ.get('SPEED_SUGGEST_QUEUE', 'speed-suggest-C1-V1')
TRAFFIC_STATE_QUEUE = os.environ.get('TRAFFIC_STATE_QUEUE', 'M_traffic_total')

# MQTT Broker settings ########################################################################
import paho.mqtt.client as mqtt
MQTT_HOST = os.environ.get('MQTT_HOST', '143.248.221.201')
MQTT_PORT = 1883
MQTT_TUCSON_TRAFFIC_TOPIC = 'navya/traffic'
client = mqtt.Client()
client.connect(MQTT_HOST, MQTT_PORT)
client.loop_start()
# MQTT Broker settings ########################################################################

def on_disconnect(client, userdata, rc):
    print("Disconnected from broker. Reconnecting...")
    while True:
        try:
            client.reconnect()
            print("Reconnected successfully.")
            break
        except Exception as e:
            print(f"Reconnect failed: {e}")
            time.sleep(5)  # Retry every 5 seconds

def callback_traffic_state(ch, method, properties, body):
    message = body.decode()
    message = json.loads(message)
    message['t_veh_rev'] = time.time()
    #TODO:
    if (time.time() - message['t_meta_sent']) > 1:
        logging.info(f"Got old messages from metaverse at {message['t_meta_sent']}")
        return
    try: 
        client.publish(MQTT_TUCSON_TRAFFIC_TOPIC, json.dumps(message))
        logging.info(f"Consumed from {TRAFFIC_STATE_QUEUE} queue: {message}")
    except Exception as e:
        logging.info("MQTT publishing error")
    
def main():
    
    client.on_disconnect = on_disconnect

    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()
    channel.queue_declare(queue=TRAFFIC_STATE_QUEUE)
    channel.basic_consume(
        queue=TRAFFIC_STATE_QUEUE, on_message_callback=callback_traffic_state, auto_ack=True
    )
    logging.info(f"Starting to consume messages from {TRAFFIC_STATE_QUEUE} queue...")
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        logging.info("Receiver interrupted. Closing connection...")
        channel.stop_consuming()
        connection.close()

if __name__ == '__main__':
    main()