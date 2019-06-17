# Build:
# docker build --rm -t storitch .
# Run:
# docker run -d --name=storitch -p 3000:80 -v /var/storitch:/var/storitch storitch
# Start:
# docker start storitch

FROM python:3-slim

RUN apt-get update --fix-missing && apt-get install supervisor nginx libmagickwand-dev -y

RUN pip install https://github.com/thomaserlang/storitch/archive/master.zip

RUN useradd -r storitch -s /bin/false

COPY nginx.conf /etc/nginx/nginx.conf
COPY storitch.yaml /etc/storitch.yaml
COPY supervisor.conf /etc/supervisor/supervisord.conf

RUN mkdir /var/log/storitch && chown storitch:storitch /var/log/storitch
RUN mkdir /var/storitch && chown storitch:storitch /var/storitch

EXPOSE 80
VOLUME /var/storitch
CMD /usr/bin/supervisord -c /etc/supervisor/supervisord.conf