FROM python:3.8

RUN mkdir /workdir

RUN pip3 install pluploader

WORKDIR /workdir

ENTRYPOINT [ "pluploader" ]%
