# eTabib Platform

This repository contains the source code and configuration for the eTabib platform.

## 📂 Project Structure

- **etabib_source/**: Main Django application source code (extracted from deployment container).
- **medica-ai/**: AI services and backend.
- **offline_deployment_package/**: Deployment configuration (docker-compose, settings).

## 🚀 Deployment

This project uses a containerized deployment.

### Offline Deployment
The current deployment runs on a dedicated server using the configuration in `offline_deployment_package`.

**Key Commands:**
```bash
# Start services
cd offline_deployment_package
docker-compose -f docker-compose.prod.yml up -d

# Restart web service
docker restart etabib_web
```

### Development
To run locally or for development:
1. Use the `etabib_source` directory as your working directory.
2. Update `docker-compose.yml` to mount `etabib_source:/app`.

## ⚠️ Important Note
This repository contains the **source code** and **configuration**.
Sensitive data (database, media files, trained models) and build artifacts (static files) are **excluded** via `.gitignore`.
