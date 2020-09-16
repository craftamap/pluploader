FROM python

RUN pip3 install pluploader \
 && apt-get update \
 && apt-get install -y vim \
 && mkdir -p /workdir

WORKDIR /workdir

ENTRYPOINT [ "pluploader" ]%
