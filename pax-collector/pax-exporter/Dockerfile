# For more information, please refer to https://aka.ms/vscode-docker-python
FROM python:3.10-slim

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

COPY . /app
WORKDIR /app

# Install poetry
# no virtualenv created, not needed
RUN pip install poetry && \
poetry config virtualenvs.create false && \
poetry install

# Environment variables for MQTT connection
# filled by user when running container
ENV MQTT_BROKER=
ENV MQTT_PORT=
ENV MQTT_TOPIC=
ENV MQTT_USERNAME=
ENV MQTT_PASSWORD=

EXPOSE 8000

# Creates a non-root user with an explicit UID and adds permission to access the /app folder
# For more info, please refer to https://aka.ms/vscode-docker-python-configure-containers
RUN adduser -u 5678 --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser

# During debugging, this entry point will be overridden. For more information, please refer to https://aka.ms/vscode-docker-python-debug
CMD ["python", "prom_client.py"]
