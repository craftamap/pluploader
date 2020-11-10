FROM python:3.8

ARG PL_VERSION=">=0.3"

RUN mkdir /workdir

RUN pip3 install "pluploader==$PL_VERSION"

WORKDIR /workdir

ENTRYPOINT [ "pluploader" ]
