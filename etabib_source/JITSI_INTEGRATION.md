# Jitsi Meet Integration Guide

This guide explains how to run and maintain the local Jitsi Meet Docker integration for the `etabibstore` project.

## Overview

The Jitsi integration allows you to run a full Jitsi Meet stack locally, enabling video consultation features in the development environment. It uses the official Jitsi Docker images (`stable` tag) and is configured to work with the `etabibstore` Django application.

## Prerequisites

- Docker and Docker Compose
- The `etabib_network_dev` network (created by the main `docker-compose.dev.yml`)

## Configuration

### Files

- **`docker-compose.jitsi.yml`**: Defines the Jitsi services (`jitsi-web`, `jitsi-prosody`, `jitsi-jicofo`, `jitsi-jvb`).
- **`.env.jitsi`**: Contains environment variables for Jitsi, including ports and JWT configuration.
- **`jitsi_config/`**: Directory where Jitsi configuration and data are persisted locally.

### Key Settings

- **URL**: `https://localhost:8443`
- **HTTP Port**: `8001`
- **HTTPS Port**: `8443`
- **Authentication**: JWT (Secret matches the one in the backup and should match the main app).

## Running Jitsi

To start the Jitsi services, run the following command:

```bash
docker-compose -f docker-compose.jitsi.yml --env-file .env.jitsi up -d
```

To view logs:

```bash
docker-compose -f docker-compose.jitsi.yml logs -f
```

To stop services:

```bash
docker-compose -f docker-compose.jitsi.yml down
```

## Integration with Django

The Django application is configured to use the local Jitsi instance when in `DEV` mode.

In `etabibWebsite/settings.py`:
```python
if ENVIRONMENT == Environment.DEV:
    ECONSULTATION_JITSI_DOMAIN_NAME = 'localhost:8443'
```

## Troubleshooting

### Certificate Warnings
Since the local setup uses self-signed certificates, browsers will block the Jitsi script (`external_api.js`) by default, causing the error: `Uncaught ReferenceError: JitsiMeetExternalAPI is not defined`.

**To fix this:**
1. Open [https://localhost:8443/external_api.js](https://localhost:8443/external_api.js) in a new browser tab.
2. You will see a "Your connection is not private" warning.
3. Click **Advanced** -> **Proceed to localhost (unsafe)**.
4. Once the script text loads, close the tab and refresh the teleconsultation page.

### Network Issues
Ensure that the `etabib_network_dev` network exists. It is usually created when you start the main application stack (`docker-compose.dev.yml`). If Jitsi fails to start because the network is missing, start the main app first.

### Data Persistence
All configuration is stored in the `jitsi_config` directory. If you want to reset the Jitsi installation completely, you can delete this directory (warning: this will delete all Jitsi data):

```bash
sudo rm -rf jitsi_config
```
