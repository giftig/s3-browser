#!/bin/bash

cd "$(dirname "$0")/.."

RED=$(tput setaf 1)
GREEN=$(tput setaf 2)
RESET=$(tput sgr0)

MINIO_TEST_BUCKET='minio-test-bucket'

# Wait for a service to be up by polling docker logs for presence of a search string
await_service() {
  local container_name="$1"
  local log_search="$2"
  local count=0

  echo -n "Waiting for $container_name..."
  while ! docker compose logs "$container_name" | grep -F "$log_search" > /dev/null; do
    echo -n "."
    sleep 2
    ((++count))

    if [[ "$count" -gt 20 ]]; then
      echo " [ ${RED}FAILED${RESET} ]"
      docker compose logs "$container_name" >&2
      return 1
    fi
  done

  echo " [ ${GREEN}OK${RESET} ]"
  return 0
}

create_bucket() {
  echo -n "Creating minio bucket $1... "
  docker compose exec -T minio mc alias set local http://localhost:9000 minio minio123 || return 1
  docker compose exec -T minio mc mb "local/$1"
  echo ''
}

docker compose up -d
await_service minio 'S3-API:' || exit 2
create_bucket "$MINIO_TEST_BUCKET" || exit 3
