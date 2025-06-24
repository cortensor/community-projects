# Deployment Helper Scripts

This script provides helper scripts for deploying Cortensor and enabling people to run cortensor on their own infrastructure in the matter of minutes.

## Features
- Easy Installation for cortensor
- Update cortensor
- Install Cortensor Monitoring (by @beranalpagion (Discord))

## Setup

1. Execute and follow on screen instruction
```
bash -c "$(wget -qLO - https://raw.githubusercontent.com/cortensor/community-projects/refs/heads/main/infras/helper-scripts/src/cortensor.sh)"
```

## Architecture
```
└── cortensor-docker/
   ├── .env
   └── docker-compose.yml
```

## Maintainer
@CryptoNodeRedd (Telegram)

## License
MIT
