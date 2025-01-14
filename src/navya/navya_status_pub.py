#!/usr/bin/env python3

import pika
import logging
import json
import time
import threading
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
RABBITMQ_HOST = os.environ.get('RABBITMQ_HOST', '143.248.55.76')
RABBITMQ_PORT = os.environ.get('RABBITMQ_PORT', 30672)
RABBITMQ_USER = 'mos'
RABBITMQ_PASSWORD = 'mos'
credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
parameters = pika.ConnectionParameters(
    host=RABBITMQ_HOST,
    port=RABBITMQ_PORT,
    virtual_host='/',
    credentials=credentials
)

VEHICLE_STATUS_QUEUE = os.environ.get('VEHICLE_STATUS_QUEUE', 'M_v_status')

# MQTT Broker settings ########################################################################
import paho.mqtt.client as mqtt
MQTT_HOST = os.environ.get('MQTT_HOST', '143.248.221.201')
MQTT_PORT = 1883
MQTT_TUCSON_STATUS_TOPIC = 'navya/status'
# MQTT Broker settings ########################################################################

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        client.subscribe(MQTT_TUCSON_STATUS_TOPIC)
        print(f"STATUS PUBLISHER | Connected to MQTT Broker")
    else:
        print(f"STATUS PUBLISHER | Failed to connect, return code {rc}")

def on_disconnect(client, userdata, rc):
    print("Disconnected from broker. Reconnecting...")
    while True:
        try:
            client.reconnect()
            # client.subscribe(MQTT_TUCSON_STATUS_TOPIC)
            print("Reconnected successfully.")
            break
        except Exception as e:
            print(f"Reconnect failed: {e}")
            time.sleep(5)  # Retry every 5 seconds

def on_message(client, userdata, message):
    message = message.payload.decode()
    message = json.loads(message)
    message = dict (
            timeStamp = message['timeStamp'],
            id = message['id'],
            cType = message['cType'],
            position = message['position'],
            heading = message['heading'],
            speed = message['speed'],
            width = message['width'],
            lengthf = message['lengthf'],      
            lengthb= message['lengthb'],
            height = message['height'],
            accMax = message['accMax'],
            t_veh_sent = message['t_veh_sent'],
            t_meta_rev = message['t_meta_rev'],
            t_meta_sent = message['t_meta_sent'],
            t_intel_rev = message['t_intel_rev'],
            t_intel_sent = message['t_intel_sent'],
            t_veh_rev = message['t_veh_rev'],
    )
    # print(message)
    try:
        mq_channel.basic_publish(
            exchange='',
            routing_key=VEHICLE_STATUS_QUEUE,
            properties=pika.BasicProperties(expiration='1000'), # Old msg will remain in queue upto 1s
            body=json.dumps(message)
        )
        logging.info(f'RabbitMQ | Published message: {message}')
    except Exception as e:
        logging.error(f'RabbitMQ | Publish error')

def rabbitmq_reconnect():
    while True:
        try:
            logging.info(f"RabbitMQ reconnection attempt")
            mq_connection = pika.BlockingConnection(parameters)
            mq_channel = mq_connection.channel()
            mq_channel.queue_declare(queue=VEHICLE_STATUS_QUEUE, arguments = {'message-ttl': 1000}) # (queue='vehicle_data', arguments = {'message-ttl': 0})
        except Exception as e:
            logging.error(f"RabbitMQ connection failed, retrying every 5s...")
            time.sleep(5)  # wait before retrying

if __name__ == "__main__":
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    client.connect(MQTT_HOST, MQTT_PORT)
    # client.subscribe(MQTT_TUCSON_STATUS_TOPIC)
    client.loop_start()

    mq_connection = pika.BlockingConnection(parameters)
    mq_channel = mq_connection.channel()
    mq_channel.queue_declare(queue=VEHICLE_STATUS_QUEUE, arguments = {'message-ttl': 1000}) # (queue='vehicle_data', arguments = {'message-ttl': 0})
    while True:
        pass