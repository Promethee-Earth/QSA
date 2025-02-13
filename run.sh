path=$(pwd)
cd sandbox || exit
docker compose up -d
cd "$path" || exit
