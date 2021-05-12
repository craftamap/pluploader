FROM python:3.8

ARG PL_VERSION=">=0.3"

RUN mkdir /workdir \
 && pip3 install --no-cache-dir "pluploader==$PL_VERSION"

WORKDIR /workdir

ENTRYPOINT [ "pluploader" ]
