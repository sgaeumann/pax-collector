# Pax Collector

The Pax Collector has multiple containers, and each of them has a different job. Together, they form a chain that collects data received from a MQTT Topic, and display it in a Dashboard with Grafana. 

This folder contains two folders :

1. `docker-compose`
2. `pax-exporter`


## 1. docker-compose

This folder is taken from <a href="https://github.com/ninadingole/docker-compose-stacks">this repository</a>, and within the folder called  `prometheus-grafana`, a `docker-compose.yml` file is found. It contains all images used to create the containers needed to create the Pax Collector :

- **Prometheus** : monitoring service
- **Grafana** : display metrics in graphs
- *Pax-exporter* : MQTT client and Prometheus exporter

### Environment variables

The *Pax-exporter* container needs the following environment variables to run :

`mqtt.env` : credentials to connect to MQTT Broker
    
     `MQTT_BROKER`, `MQTT_PORT`, `MQTT_TOPIC`, `MQTT_USERNAME`,`MQTT_PASSWORD`

### Run the docker-compose

Command to run the docker-compose:

    docker compose up

Command to kill the docker-compose:

    docker compose down

## 2. pax-exporter

The *Pax-exporter* is responsible for recepting MQTT messages, parsing them and then exposing them as Prometheus metrics to an endpoint (HTTP server).<br>
The folder contains the Dockerfile of the *Pax-exporter* container, as well as all code files it needs to run. <br>

The code does the following:

- connect to a MQTT Broker
- parse received messages to retrieve different values (*counters, sum of IDs, battery voltage, number of IDs that couldn't be sent*)
- expose those metrics to an HTTP server

To run the container, it needs the following Environment variables:<br> `MQTT_BROKER`, `MQTT_PORT`, `MQTT_TOPIC`, `MQTT_USERNAME`, `MQTT_PASSWORD`
<br>
Here's the whole command to run the container: <br>

    docker run -d -p 8000:8000 --env MQTT_BROKER=<hostname/IP> --env MQTT_PORT=<> --env MQTT_TOPIC=<> --env MQTT_USERNAME=<> --env MQTT_PASSWORD=<>
<br>

To be able to add the image to the `docker-compose.yml` file, it was necessary to create a <a href="https://hub.docker.com/r/snowflakeinthesnow/client-mqtt-prometheus-paxcounter">Dockerhub repository</a> and push the image.<br>
To pull the image: 

    docker pull snowflakeinthesnow/client-mqtt-prometheus-paxcounter

## Portainer Stack

To deploy the application in Portainer, you need to make some adjustment. Only one single `stack.env` file can be loaded. The format must look like that :

    env_file:
        - stack.env

Link : <a href="https://docs.portainer.io/user/docker/stacks/add#option-2-upload">https://docs.portainer.io/user/docker/stacks/add#option-2-upload</a>