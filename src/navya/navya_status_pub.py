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
rabbitmq_service_endpoint = 'mos-rabbitmqcluster.default.svc.cluster.local' #'10.108.97.2'
rabbitmq_port = 5672
# rabbitmq_service_endpoint = '143.248.55.76'
# rabbitmq_port = 30672
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
vehicle_status_queue = os.environ.get('VEHICLE_STATUS_QUEUE', 'M_v_status')
# grpc_target = "172.25.15.107:50051"
# vehicle_status_queue = "M_v_status"

def connect_grpc(target, retry_interval=1):
    """Create and return a gRPC channel and stub."""
    while True:
        print('connect_grpc .........................')
        try:
            channel = grpc.insecure_channel(grpc_target)
            grpc.channel_ready_future(channel).result(timeout=5)
            stub = custom_msg_pb2_grpc.VehicleStatusServiceStub(channel)
            logging.info("Connected to gRPC server.")
            return channel, stub
        except grpc.FutureTimeoutError:
            logging.warning(f"Failed to connect to gRPC server. Retrying in {retry_interval} seconds...")
            time.sleep(retry_interval)
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            time.sleep(1)

def reconnect_grpc(target):
    logging.warning("Attempting to reconnect to gRPC server...")
    global grpc_channel, grpc_stub 
    grpc_channel, grpc_stub = connect_grpc(target)

def run():
    mq_connection = pika.BlockingConnection(parameters)
    mq_channel = mq_connection.channel()
    mq_channel.queue_declare(queue=vehicle_status_queue) #(queue='vehicle_data', arguments = {'message-ttl': 0})
    # keepalive_opts = [
    #             ("grpc.keepalive_time_ms", 10000),  # Send keepalive ping every 10 seconds
    #             ("grpc.keepalive_timeout_ms", 5000),  # Wait 5 seconds for keepalive ping ack
    #             ("grpc.keepalive_permit_without_calls", True),  # Allow pings when no calls in progress
    #             ("grpc.http2.max_pings_without_data", 0),  # Unlimited pings without data
    #             ("grpc.http2.min_time_between_pings_ms", 5000),  # Minimum time between pings
    #         ]
    while True:
        try:
            # with grpc.insecure_channel('localhost:50051') as channel:
            with grpc.insecure_channel(grpc_target) as channel:
                stub = custom_msg_pb2_grpc.VehicleStatusServiceStub(channel)
                try:
                    #TODO:
                    for response in stub.GetVehicleStatus(custom_msg_pb2.Empty()):
                        message = dict(
                            cType = response.cType,
                            id = response.id,
                            position = response.position,
                            heading = response.heading,
                            speed = response.speed,
                            width = response.width,
                            lengthf = response.lengthf,
                            lengthb = response.lengthb,
                            height  = response.height,
                            accMax = response.accMax,
                            timeStamp = response.timeStamp,

                            t_veh_sent = response.t_veh_sent,
                            t_meta_rev = response.t_meta_rev,
                            t_meta_sent = response.t_meta_sent,
                            t_intel_rev = response.t_intel_rev,
                            t_intel_sent = response.t_intel_sent,
                            t_veh_rev = response.t_veh_rev,
                        )
                        try:
                            mq_channel.basic_publish(
                                exchange='',
                                routing_key=vehicle_status_queue,
                                properties=pika.BasicProperties(expiration='1000'), #Old msg will remain in queue upto 1s
                                body=json.dumps(message)
                            )
                            print(f'Published rabbitmq message: {message}')
                        except pika.exceptions.UnroutableError:
                            logging.error('publish error')
                except grpc.RpcError as e:
                    # print(f'gRPC error: {e.code()} - {e.details()}')
                    logging.error(f"gRPC error: {e.code()} - {e.details()}")
                    time.sleep(1)
                    continue
                except grpc._channel._InactiveRpcError as e:
                    # print(str(e))
                    logging.error(f"_InactiveRpcError error: {e.code()} - {e.details()}")
                    time.sleep(1)
                    continue
        except Exception as e:
            logging.error(f'An error occurred: {e.code()} - {e.details()}')
            time.sleep(1)
            continue

if __name__ == "__main__":
    run()
