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
        #TODO:
        # Message to be sent
        self.mos_vehicle_status = dict(
                cType = 'vehicle',
                position = '0.0, 0.0, 0.0',
                heading = 0.0, # rad
                speed = 0.0, # m/s
                id = 1,
                width = 1.87,
                lengthf = 2.685,      
                lengthb=1.945,
                height = 1.65,
                accMax = 4.0,
                timeStamp = time.time(),
                t_veh_sent = 0,
                t_meta_rev = 0,
                t_meta_sent = 0,
                t_intel_rev = 0,
                t_intel_sent = 0,
                t_veh_rev = 0,
        )
        # Apollo message
        self.ego_vehicle_status = dict( 
            is_aeb = False,
            is_estop = False,
            is_emergency = False,
            gear_location = 0,
            left_signal = False,
            right_signal = False,
            steer_angle = 0.0,
        )
        # Apollo message
        self.localization_info = dict(
            pose_x = 0.0,
            pose_y = 0.0,
            pose_z = 0.0,
            heading = 0.0,
            linear_velocity_x = 0.0,
            linear_velocity_y = 0.0,
            linear_velocity_z = 0.0,
            linear_acceleration_x = 0.0,
            linear_acceleration_y = 0.0,
            linear_acceleration_z = 0.0,
            angular_velocity_x = 0.0,
            angular_velocity_y = 0.0,
            angular_velocity_z = 0.0,
            pose_std_x = 0.0,
            pose_std_y = 0.0,
            orientation_std_x=0.0,
            orientation_std_y=0.0,
        )
        self.timestamp = time.time()
        # rospy.Subscriber('/vdc/tucson/status', EgoVehicleStatus, self.ego_vehicle_status_callback)
        rospy.Subscriber('/vdc/tucson/odom', apollo_to_odom, self.localization_info_callback)

        # Flag to track if the first callback has been received
        self.first_localization_info_callback_received = False
        self.first_ego_vehicle_status_callback_received = False

    def localization_info_callback(self, msg):
        # print('localization_info_callback')
        self.localization_info["pose_x"] = msg.pose_x
        self.localization_info["pose_y"] = msg.pose_y
        self.localization_info["pose_z"] = msg.pose_z
        self.localization_info["heading"] = msg.heading
        self.localization_info["linear_velocity_x"] = msg.linear_velocity_x
        self.localization_info["linear_velocity_y"] = msg.linear_velocity_y
        self.localization_info["linear_velocity_z"] = msg.linear_velocity_z
        self.localization_info["linear_acceleration_x"] = msg.linear_acceleration_x
        self.localization_info["linear_acceleration_y"] = msg.linear_acceleration_y
        self.localization_info["linear_acceleration_z"] = msg.linear_acceleration_z
        self.localization_info["angular_velocity_x"] = msg.angular_velocity_x
        self.localization_info["angular_velocity_y"] = msg.angular_velocity_y
        self.localization_info["angular_velocity_z"] = msg.angular_velocity_z
        self.localization_info["pose_std_x"] = msg.pose_std_x
        self.localization_info["pose_std_y"] = msg.pose_std_y
        self.localization_info["orientation_std_x"] = msg.orientation_std_x
        self.localization_info["orientation_std_y"] = msg.orientation_std_y
        self.timestamp = time.time()
        # logger.info(f'localization_info: {self.localization_info}')

        if not self.first_localization_info_callback_received:
            self.first_localization_info_callback_received = True
        
    def ego_vehicle_status_callback(self, msg):
        # print('ego_vehicle_status_callback')
        self.ego_vehicle_status['is_aeb'] = msg.is_aeb
        self.ego_vehicle_status['is_estop'] = msg.is_estop
        self.ego_vehicle_status['is_emergency'] = msg.is_emergency
        self.ego_vehicle_status['gear_location'] = msg.gear_location
        self.ego_vehicle_status['left_signal'] = msg.left_signal
        self.ego_vehicle_status['right_signal'] = msg.right_signal
        self.ego_vehicle_status['steer_angle'] = msg.steer_angle

        if not self.first_ego_vehicle_status_callback_received:
            self.first_ego_vehicle_status_callback_received = True

    def GetVehicleStatus(self, request, context):
        # print(f'Connected to gRPC client on remote server')
        pose_x = self.localization_info["pose_x"] 
        pose_y = self.localization_info["pose_y"]
        pose_z = self.localization_info["pose_z"] 
        vx = self.localization_info["linear_velocity_x"]
        vy = self.localization_info["linear_velocity_y"]
        speed = math.sqrt(vx**2 + vy**2)
        heading = self.localization_info['heading']
        # timestamp = self.timestamp
        timestamp = time.time()
        # print(self.first_localization_info_callback_received and self.first_ego_vehicle_status_callback_received)
        #TODO: edit .... when message definition changes
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
            # logger.info(f'heading: {heading}')
            # print(f'heading: {heading}') 
            # print('Sent to gRPC client') #NOTE:
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
        # print(f"Received speed suggestion: {self.mos_speed_suggest}") #NOTE:
        logger.info(f"Received speed suggest = sgSpeed: {request.sgSpeed},  timeStamp: {request.timeStamp}, t_veh_sent: {request.t_veh_sent}, t_meta_rev: {request.t_meta_rev}, t_meta_sent: {request.t_meta_sent}, t_intel_rev: {request.t_intel_rev}, t_intel_sent: {request.t_intel_sent}, t_veh_rev: {time.time()}") #NOTE:
        self.speed_pub.publish(int(self.mos_speed_suggest * 3.6))  # m/s -> km/h
        return custom_msg_pb2.Empty()
    
class TrafficReceiver(custom_msg_pb2_grpc.TrafficStateServiceServicer):
    #TODO: MESSAGE DEFINITION
    def __init__(self):
        super().__init__()
        self.mos_traffic_state = dict(
            cType = '',
            position = '',
            heading = 0.0,
            speed = 0.0,
            id = 0,
            width = 0.0,
            lengthf = 0.0,      
            lengthb= 0.0,
            height = 0.0,
            accMax = 0.0,
            timeStamp = 0.0,
            t_veh_sent = 0,
            t_meta_rev = 0,
            t_meta_sent = 0,
            t_intel_rev = 0,
            t_intel_sent = 0,
            t_veh_rev = 0,
        )
        self.traffic_pub = rospy.Publisher('/vdc/v2x/obstacles', perceptionObstacles, queue_size=10)
        self.traffic_msg = perceptionObstacles()
        self.traffic_msg.obstacles = [] 

        self.obstacle_type = {
            'vehicle': 1, 
            'real': 2, 
            'virtual': 3,
        }

    def SetTrafficState(self, request, context):
        # print(f'received: {request}')
        #TODO:
        self.mos_traffic_state['cType'] = request.cType
        self.mos_traffic_state['position'] = request.position
        self.mos_traffic_state['heading'] = request.heading
        self.mos_traffic_state['speed'] = request.speed
        self.mos_traffic_state['id'] = request.id
        self.mos_traffic_state['width'] = request.width
        self.mos_traffic_state['lengthf'] = request.lengthf
        self.mos_traffic_state['lengthb'] = request.lengthb
        self.mos_traffic_state['height'] = request.height
        self.mos_traffic_state['accMax'] = request.accMax
        self.mos_traffic_state['timeStamp'] = request.timeStamp

        self.mos_traffic_state['t_veh_sent'] = request.t_veh_sent
        self.mos_traffic_state['t_meta_rev'] = request.t_meta_rev
        self.mos_traffic_state['t_meta_sent'] = request.t_meta_sent
        self.mos_traffic_state['t_intel_rev'] = request.t_intel_rev
        self.mos_traffic_state['t_intel_sent'] = request.t_intel_sent
        self.mos_traffic_state['t_veh_rev'] = time.time()

        # #log_timestamps(request.timeStamp)
        # logfile = "/home/user/catkin_ws/src/mos_interface_v2/scripts/timestamp.log"
        # with open(logfile, 'a') as file:
        #     file.write(f"Current: {time.time()}, Server: {request.timeStamp}, Position: {request.position}, \n")  
        
        logger.info(f"Received surrounding info: {self.mos_traffic_state}") #NOTE:

        obs = perceptionObstacle()
        obs.header.stamp = rospy.Time.from_sec(request.timeStamp) #ADD:
        obs.id = request.id
        obs.type = request.id # self.obstacle_type.get(request.cType, 0) #TODO: return 0 or None????
        obs.length = request.lengthf + request.lengthb
        obs.width = request.width
        obs.height = request.height
        obs.heading = request.heading
        obs.pose_x, obs.pose_y, obs.pose_z = map(float, request.position.split(", "))
        theta_in_rad = request.heading #TODO:
        obs.linear_velocity_x = request.speed * math.cos(theta_in_rad)
        obs.linear_velocity_y = request.speed * math.sin(theta_in_rad)
        obs.linear_velocity_z = 0.0
        obs.linear_acceleration_x = 0.0
        obs.linear_acceleration_y = 0.0
        obs.linear_acceleration_z = 0.0

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
        
        # self.traffic_msg.obstacles = [] #TODO: if the server send one by one obstacle not array
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
