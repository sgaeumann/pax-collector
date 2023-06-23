# SPDX-License-Identifier: MIT
'''This code provides an MQTT client that receives message from broker and parses them.
   To differenciate between data received, the code relies on the 'FPort' value:
        - 13 : list of Wifi IDs
        - 14 : list of Bluetooth IDs
        - 8 : Battery voltage
        - 1 : Wifi and Bluetooth counters
    >Note: all retrieved values are cumulated. This way, there is no data loss.
            This provides a solution to this asynchronous system
            (reception of MQTT messages, Prometheus scraping and Grafana scraping).
'''
__author__ = "Sarah Gäumann <sarah.gaeumann@edu.hefr.ch>"
__date__ = "2023-6-21"

import json
import logging
import os
import random

from paho.mqtt import client as mqtt_client  # import client class

logger = logging.getLogger(__name__)

class Client:  # pylint: disable=too-many-instance-attributes
    '''MQTT Client class'''
    def __init__(self, event, queue, condition):
        '''init client mqtt'''
        # generate client client_id with pub prefix randomly
        self.client_id = f'my-mqtt-client-{random.randint(0, 100)}'
        # Load environment variables
        self.mqtt_username = os.getenv('MQTT_USERNAME')
        self.mqtt_password = os.getenv('MQTT_PASSWORD')
        self.mqtt_broker = os.getenv('MQTT_BROKER')
        self.mqtt_port = int(os.getenv('MQTT_PORT'))
        self.mqtt_topic = os.getenv('MQTT_TOPIC')
        self.mqtt_client = mqtt_client.Client(self.client_id)
        # data exchange handling
        self.event = event
        self.queue = queue
        self.condition = condition
        self.received_wifi_msg = False
        self.received_bt_msg = False
        self.received_batt_msg = False
        self.unsent_ids_null = True
        self.received_msg_fp1 = False
        self.sum_wifi = 0
        self.sum_bt = 0
        self.unsent_ids = 0
        self.wifi = 0
        self.ble = 0
        self.batt = 0

    def connect_mqtt(self):
        '''connects to MQTT broker'''
        def on_connect(self, userdata, flags, return_code):  # pylint: disable=unused-argument
            if return_code == 0:
                logger.info("Connected to MQTT Broker!")
            else:
                logger.error("Failed to connect, return code %d", return_code)
        print(self.client_id)
        self.mqtt_client.username_pw_set(
            self.mqtt_username, self.mqtt_password)
        self.mqtt_client.on_connect = on_connect
        self.mqtt_client.connect(self.mqtt_broker, self.mqtt_port)

    def on_disconnect(self, return_code):
        '''handle disconnect callback'''
        if return_code != 0:
            logger.info('Disconnected, result code %s', str(return_code))
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()

    def subscribe_mqtt(self):
        '''subscribe to topic'''
        self.mqtt_client.subscribe(self.mqtt_topic)
        print(f"Subscribed to {self.mqtt_topic}")
        self.mqtt_client.on_message = lambda client, userdata, msg: self.on_message(
            client, userdata, msg)  # pylint: disable=line-too-long, unnecessary-lambda
        self.mqtt_client.on_disconnect = lambda return_code: self.on_disconnect(
            return_code)  # pylint: disable=unnecessary-lambda

    def on_message(self, client, userdata, msg):  # pylint: disable=unused-argument
        '''handle on_message callback'''
        json_msg = json.loads(msg.payload)
        if not 'uplink_message' in json_msg:
            return
        if not 'decoded_payload' in json_msg['uplink_message']:
            return
        if not 'port' in json_msg['uplink_message']['decoded_payload']:
            return
        port = json_msg['uplink_message']['decoded_payload']['port']
        if port == 13:  # wifi messages
            list_client_ids = json_msg['uplink_message']['decoded_payload']['bytes']
            self.received_wifi_msg = True
            # first byte signals number of IDs that couldn't be sent
            # sum for synchronization reasons
            self.unsent_ids = list_client_ids[0] + self.unsent_ids
            logger.info("unsent ids: %d", self.unsent_ids)
            # int(x) truncates x, in our case the first byte isn't counted (list is odd).
            wifi = int((len(list_client_ids))/2)  # 1 client_id == 2 Bytes
            self.sum_wifi += wifi
            logger.info("wifi fp13= %d", wifi)
            logger.debug("sum_wifi = %d", self.sum_wifi)
        elif port == 14:  # bluetooth messages
            list_client_ids = json_msg['uplink_message']['decoded_payload']['bytes']
            self.received_bt_msg = True
            # first byte signals number of IDs that couldn't be sent
            self.unsent_ids = list_client_ids[0] + \
                self.unsent_ids  # sum for compatibility
            logger.info("unsent ids: %d", self.unsent_ids)
            # int(x) truncates x, in our case the first byte isn't counted (list is odd).
            bluetooth = int((len(list_client_ids))/2)  # 1 client_id == 2 Bytes
            self.sum_bt += bluetooth
            logger.info("bluetooth fp14= %d", bluetooth)
            logger.debug("sum_bluetooth = %d", self.sum_bt)
        elif port == 1:
            wifi = json_msg['uplink_message']['decoded_payload']['wifi']
            logger.info("wifi fp1= %d", wifi)
            self.wifi += wifi
            ble = json_msg['uplink_message']['decoded_payload']['ble']
            logger.info("ble fp1= %d", ble)
            self.ble += ble
            self.received_msg_fp1 = True
        elif port == 8:  # battery messages
            batt_voltage = json_msg['uplink_message']['decoded_payload']['voltage']
            self.batt += batt_voltage
            self.received_batt_msg = True
            logger.info("battery voltage = %d", batt_voltage)
        with self.condition:
            if self.received_wifi_msg:
                self.queue.put(self.sum_wifi)
                logger.debug('wifi added to queue')
                self.queue.put(self.unsent_ids)
                logger.debug("unsent ids added to queue")
            elif self.received_bt_msg:
                self.queue.put(self.sum_bt)
                logger.debug('bluetooth added to queue')
                self.queue.put(self.unsent_ids)
                logger.debug("unsent ids added to queue")
            elif self.received_msg_fp1:
                self.queue.put(self.wifi)
                logger.debug("wifi fp1 added to queue")
                self.queue.put(self.ble)
                logger.debug("ble fp1 added to queue")
            elif self.received_batt_msg:
                self.queue.put(self.batt)
                logger.debug("batt voltage added to queue")
            logger.debug('notify thread')
            self.condition.notify_all()

    def run(self):
        '''connect to MQTT broker, handle callbacks'''
        self.connect_mqtt()
        self.subscribe_mqtt()
        self.mqtt_client.loop_start()
        logger.debug('loop started')
        self.event.wait()
        self.mqtt_client.loop_stop()
