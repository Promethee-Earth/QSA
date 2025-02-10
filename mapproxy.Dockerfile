ARG IMAGE_VERSION=3.11.5
FROM python:${IMAGE_VERSION}

#-------------Application Specific Stuff ----------------------------------------------------
ARG MAPPROXY_VERSION=''

RUN apt-get -y update && \
    apt-get install -y \
    gettext \
    python3-yaml \
    libgeos-dev \
    python3-lxml \
    libgdal-dev \
    build-essential \
    python3-dev \
    libjpeg-dev \
    zlib1g-dev \
    libfreetype6-dev \
    python3-virtualenv \
    figlet \
    gosu awscli; \
# verify that the binary works
	gosu nobody true
RUN pip3 --disable-pip-version-check install Shapely Pillow uwsgi pyproj boto3 s3cmd \
    requests riak==2.4.2 redis numpy uwsgitop

# master 14/12/2023
ADD https://api.github.com/repos/Promethee-Earth/QSA/git/refs/heads/filter_attributs version.json
RUN git clone https://github.com/pblottiere/mapproxy \
    && cd mapproxy \
    && git checkout 2.0.2_pbl_quickfix \
    && python setup.py install

RUN ln -s /usr/lib/libgdal.a /usr/lib/liblibgdal.a

# Cleanup resources
RUN apt-get -y --purge autoremove  \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
EXPOSE 8080

ADD build_data/uwsgi.ini /settings/uwsgi.default.ini
ADD build_data/multi_mapproxy.py /multi_mapproxy.py
ADD scripts /scripts
RUN chmod +x /scripts/*.sh

RUN echo 'figlet -t "Kartoza Docker MapProxy"' >> ~/.bashrc

ENTRYPOINT [ "/scripts/start.sh" ]
CMD [ "/scripts/run_develop_server.sh" ]
