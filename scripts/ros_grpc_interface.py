#!/usr/bin/env python3

import custom_msg_pb2, custom_msg_pb2_grpc
import grpc 
from concurrent import futures
#############################
import logging
import json
import time
import threading
import math

import rospy
from std_msgs.msg import Float32, Int32
from vdc_msgs.msg import apollo_to_odom, EgoVehicleStatus
from vdc_msgs.msg import perceptionObstacle, perceptionObstacles

import asyncio

logger = logging.getLogger("ros_grpc_interface")
formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')
file_handler = logging.FileHandler('/home/hottruong/Projects/catkin_ws/src/mos_interface_v2/scripts/logs_20250103_intelligence_to_local_vehicle.log')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.setLevel(logging.DEBUG)

rospy.init_node('ros_grpc_interface_node', anonymous=True)

def log_timestamps(server_timestamp):
    current_timestamp = time.time()
    logging.info(f"Server: {server_timestamp}, Tucson: {current_timestamp}")

class StatusSender(custom_msg_pb2_grpc.VehicleStatusServiceServicer):
    def __init__(self):
        super().__init__()
        # Apollo message
        self.localization_info = dict(
            pose_x = 0.0,
            pose_y = 0.0,
            pose_z = 0.0,
            heading = 0.0,
            linear_velocity_x = 0.0,
            linear_velocity_y = 0.0,
        )
        rospy.Subscriber('/vdc/tucson/odom', apollo_to_odom, self.localization_info_callback)

        self.first_localization_info_callback_received = False

    def localization_info_callback(self, msg):
        self.localization_info["pose_x"] = msg.pose_x
        self.localization_info["pose_y"] = msg.pose_y
        self.localization_info["pose_z"] = msg.pose_z
        self.localization_info["heading"] = msg.heading
        self.localization_info["linear_velocity_x"] = msg.linear_velocity_x
        self.localization_info["linear_velocity_y"] = msg.linear_velocity_y

        if not self.first_localization_info_callback_received:
            self.first_localization_info_callback_received = True

    def GetVehicleStatus(self, request, context):
        pose_x = self.localization_info["pose_x"] 
        pose_y = self.localization_info["pose_y"]
        pose_z = self.localization_info["pose_z"] 
        vx = self.localization_info["linear_velocity_x"]
        vy = self.localization_info["linear_velocity_y"]
        speed = math.sqrt(vx**2 + vy**2)
        heading = self.localization_info['heading']
        timestamp = time.time()

        if (self.first_localization_info_callback_received):
            yield custom_msg_pb2.MosVehicleStatus(
                cType = 'vehicle',
                position = str(pose_x) + ", " + str(pose_y) + ", " + str(pose_z),
                heading = heading,
                speed = speed,
                id = 1,
                width = 1.87,
                lengthf = 2.685,      
                lengthb=1.945,
                height = 1.65,
                accMax=4.0,
                timeStamp = timestamp,

                t_veh_sent = timestamp,
                t_meta_rev = 0,
                t_meta_sent = 0,
                t_intel_rev = 0,
                t_intel_sent = 0,
                t_veh_rev = 0,
            )
            time.sleep(0.05)

class SpeedReceiver(custom_msg_pb2_grpc.SpeedSuggestionServiceServicer):
    def __init__(self):
        super().__init__()
        self.mos_speed_suggest = 0.0
        self.speed_pub = rospy.Publisher('mos_cmd_vel', Int32, queue_size=1)
        self.last_received_time = time.time()
        self.lock = threading.Lock()
        self.has_published_timeout = False

        # Start a thread to monitor timeout
        self.monitor_thread = threading.Thread(target=self.monitor_timeout)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

    def monitor_timeout(self):
        while not rospy.is_shutdown():
            time.sleep(0.1)  # Check periodically
            with self.lock:
                if time.time() - self.last_received_time > 1.0:  # 1 second timeout
                    if not self.has_published_timeout:
                        print("Server speed suggestion timeout")
                        self.speed_pub.publish(-1)
                        self.has_published_timeout = True

    def SetSpeedSuggest(self, request, context):
        with self.lock:
            self.mos_speed_suggest = request.sgSpeed
            self.last_received_time = time.time()
            self.has_published_timeout = False
        # logger.info(f"Received speed suggest = sgSpeed: {request.sgSpeed},  timeStamp: {request.timeStamp}, t_veh_sent: {request.t_veh_sent}, t_meta_rev: {request.t_meta_rev}, t_meta_sent: {request.t_meta_sent}, t_intel_rev: {request.t_intel_rev}, t_intel_sent: {request.t_intel_sent}, t_veh_rev: {time.time()}") #NOTE:
        self.speed_pub.publish(int(self.mos_speed_suggest * 3.6))  # m/s -> km/h
        return custom_msg_pb2.Empty()
    
class TrafficReceiver(custom_msg_pb2_grpc.TrafficStateServiceServicer):
    #TODO: MESSAGE DEFINITION
    def __init__(self):
        super().__init__()
        self.traffic_pub = rospy.Publisher('/vdc/v2x/obstacles', perceptionObstacles, queue_size=10)
        self.traffic_msg = perceptionObstacles(obstacles=[])
        self.obstacle_type = {
            'vehicle': 1, 
            'real': 2, 
            'virtual': 3,
        }

    def SetTrafficState(self, request, context):
        # logfile = "/home/user/catkin_ws/src/mos_interface_v2/scripts/timestamp.log"
        # with open(logfile, 'a') as file:
        #     file.write(f"Current: {time.time()}, Server: {request.timeStamp}, Position: {request.position}, \n")  
        
        #logger.info(f"Received surrounding info = timeStamp: {request.timeStamp} - id: {request.id} -  t_veh_sent: {request.t_veh_sent} - t_meta_rev: {request.t_meta_rev} - t_meta_sent: {request.t_meta_sent} - t_intel_rev: {request.t_intel_rev} - t_intel_sent: {request.t_intel_sent} - t_veh_rev: {time.time()}") #NOTE:
        theta_in_rad = request.heading #TODO:
        obs = perceptionObstacle(
            header = rospy.Header(stamp=rospy.Time.from_sec(request.timeStamp)),
            id = request.id,
            type = request.id, # self.obstacle_type.get(request.cType, 0)
            length = request.lengthf + request.lengthb,
            width = request.width,
            height = request.height,
            heading = request.heading,
            pose_x=float(request.position.split(", ")[0]),
            pose_y=float(request.position.split(", ")[1]),
            pose_z=float(request.position.split(", ")[2]),
            linear_velocity_x = request.speed * math.cos(theta_in_rad),
            linear_velocity_y = request.speed * math.sin(theta_in_rad),
            linear_velocity_z = 0.0,
        )

        # is_duplicate = False
        # for i in range(len(self.traffic_msg.obstacles)):
        #     if obs.id == self.traffic_msg.obstacles[i].id:
        #         del self.traffic_msg.obstacles[i]
        #         is_duplicate = True
        #         break
        # self.traffic_msg.obstacles.append(obs)

        #TODO:
        current_stamp = rospy.Time.from_sec(time.time())
        i = 0
        while i < len(self.traffic_msg.obstacles):
            if current_stamp.secs - self.traffic_msg.obstacles[i].header.stamp.secs >= 300: #5min
                del self.traffic_msg.obstacles[i]
                i = i - 1
            else:
                if obs.id == self.traffic_msg.obstacles[i].id:
                    del self.traffic_msg.obstacles[i]
                    break
            i  = i + 1
        self.traffic_msg.obstacles.append(obs)
        
        # self.traffic_msg.obstacles = []
        # self.traffic_msg.obstacles.append(obs)
        self.traffic_pub.publish(self.traffic_msg)
        return custom_msg_pb2.Empty()

if __name__ == '__main__':
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    custom_msg_pb2_grpc.add_VehicleStatusServiceServicer_to_server(StatusSender(), server)
    custom_msg_pb2_grpc.add_SpeedSuggestionServiceServicer_to_server(SpeedReceiver(), server)
    custom_msg_pb2_grpc.add_TrafficStateServiceServicer_to_server(TrafficReceiver(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    print('Server on port 50051 + ROS')
    try:
        # Keep the ROS node running and handle callbacks
        # NOTE: In python the callbacks are multithreaded by default!!!
        rospy.spin()

    except KeyboardInterrupt:
        print('Server is shutting down')
    finally:
        server.stop(0)
