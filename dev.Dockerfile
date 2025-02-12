FROM qgis/qgis-server:3.40.2-jammy

RUN apt-get update -y && apt-get upgrade -y
RUN apt-get install -y python3 python3-venv python3-pip python3-qgis
RUN apt install git -y

WORKDIR /app

COPY requirements.txt ./

RUN python3 -m venv --system-site-packages venv
