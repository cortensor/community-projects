# Hello World Infrastructure

A template infrastructure project for deploying Cortensor nodes and services with automated scaling and monitoring.

## Features
- Terraform templates for cloud deployment (AWS/GCP)
- Docker Compose setup for local development
- Prometheus/Grafana monitoring stack
- Auto-scaling configuration for node clusters

## Setup

1. Clone the repo
2. Set environment variables:
   - `CLOUD_API_KEY`
   - `CORTENSOR_NODE_KEY`
3. Run `./deploy.sh`

## Architecture
```
├── terraform/   # Infrastructure as code
├── docker/      # Container definitions
├── monitoring/  # Prometheus configs
└── scripts/     # Deployment helpers
```

## Maintainer
@cortensor-infra-admin (Discord)

## License
MIT
