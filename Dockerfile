FROM python:3.12-slim-bookworm as pybuilder
COPY . .
RUN pip wheel . --wheel-dir=/wheels


FROM python:3.12-slim-bookworm

RUN apt-get update && apt-get upgrade -y && apt-get install wget -y

RUN wget https://www.deb-multimedia.org/pool/main/d/deb-multimedia-keyring/deb-multimedia-keyring_2016.8.1_all.deb
RUN apt-get purge wget -y
RUN dpkg -i deb-multimedia-keyring_2016.8.1_all.deb
RUN rm deb-multimedia-keyring_2016.8.1_all.deb
RUN echo "deb https://www.deb-multimedia.org bookworm main non-free" >> /etc/apt/sources.list
RUN apt-get update && apt-get install imagemagick-7 -y && apt-get clean


ENV \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH="${PYTHONPATH}:." \
    UID=1000 \
    GID=1000

RUN mkdir /app
WORKDIR /app
COPY . .
COPY --from=pybuilder /wheels /wheels
RUN mv conf/policy.xml /etc/ImageMagick-7/policy.xml
RUN mv conf/mime.types /etc/mime.types
RUN pip install --find-links=/wheels -e .
RUN rm -rf /wheels

RUN addgroup --gid $GID --system storitch && adduser --uid $UID --gid $GID storitch && \
    mkdir /var/storitch && chown $UID:$GID -R /var/storitch
USER $UID:$GID
RUN mkdir /tmp/imagemagick

VOLUME /var/storitch
ENTRYPOINT ["python", "storitch/runner.py"]