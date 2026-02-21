FROM alpine:3.20

RUN apk add --no-cache aria2 curl

RUN mkdir -p /downloads /aria2

COPY aria2.conf /aria2/aria2.conf
COPY entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh

EXPOSE 6800

ENTRYPOINT ["/entrypoint.sh"]
