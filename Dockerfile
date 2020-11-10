FROM python:3.8

ARG PL_VERSION 

RUN mkdir /workdir

RUN pip3 install pluploader==$PL_VERSION

WORKDIR /workdir

ENTRYPOINT [ "pluploader" ]
