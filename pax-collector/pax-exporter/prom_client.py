# SPDX-License-Identifier: MIT
'''This code does...

    - collect messages from an MQTT Topic based on FPort:
        - 13 : message contains Wifi IDs
        - 14 : message contains Bluetooth IDs
        - 8 : message contains battery info
    - parse the message to calculate the number of IDs
    - create the following metrics:
        - wifi_gauge : number of Wifi IDs after each SENDCYCLE
        - bt_gauge : number of Bluetooth IDs after each SENDCYCLE
        - sum_ids_wifi_gauge : sum of all Wifi IDs since the beginning of the program
        - sum_ids_bt_gauge : sum of all Bluetooth IDs since the beginning of the program
    - expose metrics to an endpoint (HTTP server).
'''
__author__ = "Sarah Gäumann <sarah.gaeumann@edu.hefr.ch>"
__date__ = "2023-6-21"

import queue
import sys
import threading
import time
import logging

# Prometheus Python Client library :
# https://github.com/prometheus/client_python/tree/master
from prometheus_client import Gauge, start_http_server
import mqtt_client as mc


# display debug messages
logging.basicConfig(
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# launch HTTP server, expose metrics
def exporter(mqtt_client, sum_ids_bt_gauge, sum_ids_wifi_gauge, batt_gauge, unsent_ids_gauge, wifi_fp1_gauge, ble_fp1_gauge,event, condition, message_queue):  # pylint: disable=too-many-arguments
    '''updates and exports metrics to http server'''
    logger.info('start http')
    start_http_server(8000)
    while not event.is_set():  # while no event raised
        with condition:
            condition.wait()  # wait to be notified
            logger.debug('exporter notified')
            if mqtt_client.received_wifi_msg:  # flag true if message received
                sum_ids_wifi_gauge.set(message_queue.get())
                logger.debug("wifi gauge set")
                unsent_ids_gauge.set(message_queue.get())
                logger.debug("unsent ids gauge set")
                mqtt_client.received_wifi_msg = False  # reset
            elif mqtt_client.received_bt_msg:
                sum_ids_bt_gauge.set(message_queue.get())
                logger.debug("bt gauge set")
                unsent_ids_gauge.set(message_queue.get())
                logger.debug("unsent ids gauge set")
                mqtt_client.received_bt_msg = False  # reset
            elif mqtt_client.received_msg_fp1:
                wifi_fp1_gauge.set(message_queue.get())
                logger.debug("wifi fp1 gauge set")
                ble_fp1_gauge.set(message_queue.get())
                logger.debug("ble fp1 gauge set")
                mqtt_client.received_msg_fp1 = False # reset
            elif mqtt_client.received_batt_msg:
                batt_gauge.set(message_queue.get())
                logger.debug("batt gauge set")
                mqtt_client.received_batt_msg = False # reset
        logger.debug('exporter waiting')
    logger.debug("break exporter")


def main():
    ''' run pax-exporter'''
    try:
        # Data exchange handling
        message_queue = queue.Queue()  # share data between threads
        condition = threading.Condition()  # synchronize data exchange between threads
        event_terminate = threading.Event()  # flag initially false

        # Metrics
        sum_ids_wifi_gauge = Gauge(
            'paxcounter_sum_wifi_ids_collected_gauge',
            'Sum of all Wifi IDs collected by Paxcounter since the first SENDCYCLE'
        )
        sum_ids_bt_gauge = Gauge(
            'paxcounter_sum_bt_ids_collected_gauge',
            'Sum of all Bluetooth IDs collected by Paxcounter since the first SENDCYCLE'
        )
        batt_gauge = Gauge(
            'paxcounter_battery_voltage_data_gauge',
            'Battery or USB voltage [mV]')
        unsent_ids_gauge = Gauge(
            'paxcounter_number_unsent_ids_gauge',
            'Number of IDs that could not be sent due to buffer size limit'
        )
        wifi_fp1_gauge = Gauge(
            'paxcounter_wifi_count_fp1_gauge',
            'Number of Wifi seen devices collected by Paxcounter after each SENDCYCLE'
        )
        ble_fp1_gauge = Gauge(
            'paxcounter_ble_count_fp1_gauge',
            'Number of Bluetooth seen devices collected by Paxcounter after each SENDCYCLE'
        )
        
        # Threads
        # create instance of Client
        mqtt_client = mc.Client(event_terminate, message_queue, condition)
        mqtt_thread = threading.Thread(
            target=mqtt_client.run, daemon=True, args=())
        exporter_thread = threading.Thread(
            target=exporter, daemon=True,
            args=(mqtt_client, sum_ids_bt_gauge, sum_ids_wifi_gauge, batt_gauge, unsent_ids_gauge,
                  wifi_fp1_gauge, ble_fp1_gauge, event_terminate, condition, message_queue)
        )
        mqtt_thread.start()
        time.sleep(3)
        exporter_thread.start()
        # check if thread(s) are alive
        while True:
            if not mqtt_thread.is_alive() or not exporter_thread.is_alive():
                raise RuntimeError('Thread not alive')
    except:
        event_terminate.set()
        logger.info("Event set")
        exporter_thread.join()
        logger.info("exporter_thread killed")
        mqtt_thread.join()
        logger.info("mqtt_thread killed")
        print("Exiting program...")
        sys.exit(0)


if __name__ == '__main__':
    main()
