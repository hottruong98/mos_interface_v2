#!/usr/bin/env python3
#############################
import logging
import json
import time
import threading
import math

import rospy
from std_msgs.msg import Int32
from vdc_msgs.msg import apollo_to_odom
from vdc_msgs.msg import perceptionObstacle, perceptionObstacles

logger = logging.getLogger("ros_grpc_interface")
formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')
file_handler = logging.FileHandler('/home/hottruong/Projects/catkin_ws/src/mos_interface_v2/scripts/logs_20250103_intelligence_to_local_vehicle.log')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.setLevel(logging.DEBUG)

rospy.init_node('ros_mqtt_node', anonymous=True)

# MQTT Broker settings #######################################################
import paho.mqtt.client as mqtt
MQTT_HOST = "172.25.15.204"  # Replace with the server's public IP
MQTT_PORT = 1883
MQTT_TUCSON_STATUS_TOPIC = 'tucson/status'
MQTT_TUCSON_TRAFFIC_TOPIC = 'tucson/traffic'
MQTT_TUCSON_SPEED_TOPIC = 'tucson/speed'
# client = mqtt.Client()
# client.connect(MQTT_HOST, MQTT_PORT)
##########################################################################

class StatusSender():
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

        # Publishing frequency control
        self.publish_interval_in_sec = 0.04  # Interval in seconds
        self.latest_publish_time = 0.0
        
        # MQTT setup
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.connect(MQTT_HOST, MQTT_PORT)
        self.client.loop_start()
    
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            rospy.loginfo(f"StatusSender | Connected to MQTT Broker")
        else:
            rospy.loginfo(f"StatusSender | Failed to connect, return code {rc}")

    def on_disconnect(self, client, userdata, rc):
        rospy.loginfo("StatusSender | Disconnected from broker. Reconnecting...")
        while True:
            try:
                self.client.reconnect()
                rospy.loginfo("StatusSender | Reconnected successfully.")
                break
            except Exception as e:
                rospy.loginfo(f"StatusSender | Reconnect failed: {e}")
                time.sleep(5)  # Retry every 5 seconds

    def localization_info_callback(self, msg):
        current_time = time.time()
        if current_time - self.latest_publish_time <= self.publish_interval_in_sec:
            return
        
        pose_x = msg.pose_x
        pose_y = msg.pose_y
        pose_z = msg.pose_z
        vx = msg.linear_velocity_x
        vy = msg.linear_velocity_y
        speed = math.sqrt(vx**2 + vy**2)
        heading = msg.heading
        timestamp = time.time()

        message = dict(
            timeStamp = timestamp,
            id = 1,
            cType = 'vehicle',
            position = str(pose_x) + ", " + str(pose_y) + ", " + str(pose_z),
            heading = heading,
            speed = speed,
            width = 1.87,
            lengthf = 2.685,      
            lengthb=1.945,
            height = 1.65,
            accMax=4.0,
            t_veh_sent = timestamp,
            t_meta_rev = 0,
            t_meta_sent = 0,
            t_intel_rev = 0,
            t_intel_sent = 0,
            t_veh_rev = 0,
        )
        self.client.publish(MQTT_TUCSON_STATUS_TOPIC, json.dumps(message))
        self.latest_publish_time = current_time

class SpeedReceiver():
    def __init__(self):
        super().__init__()
        # self.mos_speed_suggest = 0.0
        self.speed_pub = rospy.Publisher('mos_cmd_vel', Int32, queue_size=1)
        self.last_received_time = time.time()
        self.lock = threading.Lock()
        self.has_published_timeout = False

        # Start a thread to monitor timeout
        self.monitor_thread = threading.Thread(target=self.monitor_timeout)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

        # MQTT setup
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_speed_message
        self.client.connect(MQTT_HOST, MQTT_PORT)
        # self.client.subscribe("MQTT_TUCSON_SPEED_TOPIC") 
        self.client.loop_start()

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.client.subscribe("MQTT_TUCSON_SPEED_TOPIC") 
            rospy.loginfo(f"SpeedReceiver | Connected to MQTT Broker")
        else:
            rospy.loginfo(f"SpeedReceiver | Failed to connect, return code {rc}")

    def on_disconnect(self, client, userdata, rc):
        rospy.loginfo("SpeedReceiver | Disconnected from broker. Reconnecting...")
        while True:
            try:
                self.client.reconnect()
                # self.client.subscribe("MQTT_TUCSON_SPEED_TOPIC") 
                rospy.loginfo("SpeedReceiver | Reconnected successfully.")
                break
            except Exception as e:
                rospy.loginfo(f"SpeedReceiver | Reconnect failed: {e}")
                time.sleep(5)  # Retry every 5 seconds

    def monitor_timeout(self):
        while not rospy.is_shutdown():
            time.sleep(0.1)  # Check periodically
            with self.lock:
                if time.time() - self.last_received_time > 1.0:  # 1 second timeout
                    if not self.has_published_timeout:
                        rospy.loginfo("SpeedReceiver | Timeout: no response from Intelligence server")
                        self.speed_pub.publish(-1)
                        self.has_published_timeout = True

    def on_speed_message(self, client, userdata, msg):
        # rospy.loginfo(f'speed: {msg}')
        speed_data = json.loads(msg.payload.decode()) 
        speed_suggest = float(speed_data['sgSpeed'])
        with self.lock:
            self.last_received_time = time.time()
            self.has_published_timeout = False
        self.speed_pub.publish(int(speed_suggest * 3.6))  # m/s -> km/h
    
class TrafficReceiver():
    def __init__(self):
        super().__init__()
        self.traffic_pub = rospy.Publisher('/vdc/v2x/obstacles', perceptionObstacles, queue_size=10)
        self.traffic_msg = perceptionObstacles(obstacles=[])
        self.obstacle_type = {
            'vehicle': 1, 
            'real': 2, 
            'virtual': 3,
        }
        # MQTT setup
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_traffic_message
        self.client.connect(MQTT_HOST, MQTT_PORT)
        # self.client.subscribe("MQTT_TUCSON_TRAFFIC_TOPIC")  # Subscribe to the relevant traffic update topic
        self.client.loop_start()
    
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.client.subscribe("MQTT_TUCSON_TRAFFIC_TOPIC")
            rospy.loginfo(f"TrafficReceiver | Connected to MQTT Broker")
        else:
            rospy.loginfo(f"TrafficReceiver | Failed to connect, return code {rc}")

    def on_disconnect(self, client, userdata, rc):
        rospy.loginfo("TrafficReceiver | Disconnected from broker. Reconnecting...")
        while True:
            try:
                self.client.reconnect()
                # self.client.subscribe("MQTT_TUCSON_TRAFFIC_TOPIC")
                rospy.loginfo("TrafficReceiver | Reconnected successfully.")
                break
            except Exception as e:
                rospy.loginfo(f"TrafficReceiver | Reconnect failed: {e}")
                time.sleep(5)  # Retry every 5 seconds

    def on_traffic_message(self, client, userdata, msg):
        traffic_data = msg.payload.decode() 
        obs = self.parse_traffic_data(traffic_data)

        #TODO:
        # is_duplicate = False
        # for i in range(len(self.traffic_msg.obstacles)):
        #     if obs.id == self.traffic_msg.obstacles[i].id:
        #         del self.traffic_msg.obstacles[i]
        #         is_duplicate = True
        #         break
        # self.traffic_msg.obstacles.append(obs)

        current_stamp = rospy.Time.from_sec(time.time())
        i = 0
        while i < len(self.traffic_msg.obstacles):
            if current_stamp.secs - self.traffic_msg.obstacles[i].header.stamp.secs >= 10: # seconds
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

    def parse_traffic_data(self, data):
        traffic_info = json.loads(data)  # Example: {'id': 1, 'speed': 10, 'position': 'x,y,z', ...}
        rospy.loginfo(f"traffic_info: {traffic_info}")
        theta_in_rad = traffic_info['heading']
        obs = perceptionObstacle(
            header=rospy.Header(stamp=rospy.Time.from_sec(traffic_info['timeStamp'])),
            id=traffic_info['id'],
            type=traffic_info['id'], # traffic_info.get('cType', 0),
            length=traffic_info['lengthf'] + traffic_info['lengthb'],
            width=traffic_info['width'],
            height=traffic_info['height'],
            heading=traffic_info['heading'],
            pose_x=float(traffic_info['position'].split(", ")[0]),
            pose_y=float(traffic_info['position'].split(", ")[1]),
            pose_z=float(traffic_info['position'].split(", ")[2]),
            linear_velocity_x = traffic_info['speed'] * math.cos(theta_in_rad),
            linear_velocity_y = traffic_info['speed'] * math.sin(theta_in_rad),
            linear_velocity_z = 0.0,
        )
        return obs


if __name__ == '__main__':

    status_sender = StatusSender()
    speed_receiver = SpeedReceiver()
    traffic_receiver = TrafficReceiver()

    rospy.spin()  # Keep the ROS node running
