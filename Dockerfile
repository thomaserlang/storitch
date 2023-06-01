# Build:
# docker build --rm -t thomaserlang/storitch --no-cache .
# docker push thomaserlang/storitch:latest

FROM python:3.11-slim-bullseye

RUN apt-get update; apt-get upgrade -y; apt-get install libmagickwand-dev curl -y

COPY . .

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

VOLUME /var/storitch
ENTRYPOINT ["python", "storitch/runner.py"]