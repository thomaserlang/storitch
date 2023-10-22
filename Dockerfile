# Build:
# docker build -t thomaserlang/storitch .
# docker push thomaserlang/storitch:latest

FROM python:3.12-slim-bookworm

RUN apt-get update; apt-get upgrade -y; apt-get install wget -y

RUN wget https://www.deb-multimedia.org/pool/main/d/deb-multimedia-keyring/deb-multimedia-keyring_2016.8.1_all.deb
RUN apt-get purge wget -y
RUN dpkg -i deb-multimedia-keyring_2016.8.1_all.deb
RUN rm deb-multimedia-keyring_2016.8.1_all.deb
RUN echo "deb https://www.deb-multimedia.org bookworm main non-free" >> /etc/apt/sources.list
RUN apt-get update; apt-get install imagemagick-7 libmagickwand-7-dev -y; apt-get clean

COPY . .
RUN mv conf/policy.xml /etc/ImageMagick-7/policy.xml

ENV \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH="${PYTHONPATH}:." \
    UID=10000 \
    GID=10001

RUN pip install -r requirements.txt

RUN addgroup --gid $GID --system storitch; adduser --uid $UID --system --gid $GID storitch; \
    mkdir /var/storitch && chown storitch:storitch /var/storitch
USER $UID:$GID
RUN mkdir /tmp/imagemagick

VOLUME /var/storitch
ENTRYPOINT ["python", "storitch/runner.py"]