docker compose down
docker compose rm
docker image rm cortensor-image
docker build --no-cache -t cortensor-image .
docker compose up -d