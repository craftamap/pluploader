ARG PL_VERSION 

FROM python:3.9

RUN mkdir /workdir

RUN pip3 install "pluploader==$PL_VERSION"

WORKDIR /workdir

ENTRYPOINT [ "pluploader" ]
