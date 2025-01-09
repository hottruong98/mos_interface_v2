#!/usr/bin/env python3
import grpc
import custom_msg_pb2, custom_msg_pb2_grpc

import pika
import logging
import json
import time
import threading
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
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
# grpc_target = '172.25.15.200:50051'
grpc_target = os.environ.get('GRPC_TARGET', '143.248.221.201:50051')
speed_suggest_queue = os.environ.get('SPEED_SUGGEST_QUEUE', 'speed-suggest-C1-V1')
traffic_state_queue = os.environ.get('TRAFFIC_STATE_QUEUE', 'M_traffic_total')

def create_grpc_channel(target, retry_interval=1):
    while True:
        try:
            channel = grpc.insecure_channel(target)
            grpc.channel_ready_future(channel).result(timeout=5)
            logging.info("gRPC connection established successfully.")
            return channel
        except grpc.FutureTimeoutError: # if server isn't reachable within 5s timeout
            logging.warning(f"Failed to connect to gRPC server. Retrying in {retry_interval} seconds...")
            time.sleep(retry_interval)

def initialize_stubs(channel):
    global speed_stub, traffic_stub
    speed_stub = custom_msg_pb2_grpc.SpeedSuggestionServiceStub(channel)
    traffic_stub = custom_msg_pb2_grpc.TrafficStateServiceStub(channel)
    logging.info("gRPC stubs reinitialized.")

def reconnect_grpc_channel(target):
    logging.warning("Attempting to reconnect to gRPC server...")
    global grpc_channel
    grpc_channel = create_grpc_channel(target)
    initialize_stubs(grpc_channel)

def channel_state_callback(connectivity):
    print(f'Connectivity Status: {connectivity}')
    if connectivity != grpc.ChannelConnectivity.READY:
        logging.warning("gRPC channel is not ready. Attempting to reconnect...")
        reconnect_grpc_channel(grpc_target)

def callback_speed_suggest(ch, method, properties, body):
    # logging.info("receiving speed suggest")
    message = body.decode()
    message = json.loads(message)
    message['t_veh_rev'] = time.time()
    #TODO:
    try:
        request = custom_msg_pb2.MosSpeedSuggest(
            sgSpeed=message['sgSpeed'],
            timeStamp=message['timeStamp'],

            t_veh_sent = message['t_veh_sent'],
            t_meta_rev = message['t_meta_rev'],
            t_meta_sent = message['t_meta_sent'],
            t_intel_rev = message['t_intel_rev'],
            t_intel_sent = message['t_intel_sent'],
            t_veh_rev = message['t_veh_rev'],
        )
        response = speed_stub.SetSpeedSuggest(request)  # Unary call
        logging.info(f'Sending request to gRPC server (speed): {message}')
    except grpc.RpcError as e:
        logging.error(f"gRPC error: {e.code()} - {e.details()}")
        # ch.close()
        # reconnect_grpc_channel(grpc_target)

def callback_traffic_state(ch, method, properties, body):
    message = body.decode()
    message = json.loads(message)
    message['t_veh_rev'] = time.time()
    #TODO:
    try:
        request = custom_msg_pb2.MosTrafficState(
            cType=message['cType'],
            id=message['id'],
            position=message['position'],
            heading=message['heading'],
            speed=message['speed'],
            width=message['width'],
            lengthf = message['lengthf'],
            lengthb = message['lengthb'],
            height  = message['height'],
            accMax = message['accMax'],
            timeStamp=message['timeStamp'],

            t_veh_sent = message['t_veh_sent'],
            t_meta_rev = message['t_meta_rev'],
            t_meta_sent = message['t_meta_sent'],
            t_intel_rev = message['t_intel_rev'],
            t_intel_sent = message['t_intel_sent'],
            t_veh_rev = message['t_veh_rev'],

        )
        response = traffic_stub.SetTrafficState(request)  # Unary call
        logging.info(f'Sending request to gRPC server (traffic): {message}')
    except grpc.RpcError as e:
        logging.error(f"gRPC error: {e.code()} - {e.details()}")
        # ch.close()
        # reconnect_grpc_channel(grpc_target)

def consume_from_queue(queue_name, callback):
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()

    channel.queue_declare(queue=queue_name, arguments = {'message-ttl': 1000})  # , arguments = {'message-ttl': 1000}

    channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)
    logging.info(f"Started consuming from queue: {queue_name}")

    channel.start_consuming()

if __name__ == "__main__":
    grpc_channel = create_grpc_channel(grpc_target)
    initialize_stubs(grpc_channel)

    # Subscribe to the gRPC channel's state changes
    grpc_channel.subscribe(channel_state_callback, try_to_connect=True)

    speed_suggest_thread = threading.Thread(target=consume_from_queue, args=(speed_suggest_queue, callback_speed_suggest))
    traffic_state_thread = threading.Thread(target=consume_from_queue, args=(traffic_state_queue, callback_traffic_state))

    speed_suggest_thread.start()
    traffic_state_thread.start()

    speed_suggest_thread.join()
    traffic_state_thread.join()
