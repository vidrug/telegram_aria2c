FROM alpine:3.20 AS builder

RUN apk add --no-cache \
    build-base \
    git \
    autoconf \
    automake \
    libtool \
    pkgconf \
    openssl-dev \
    c-ares-dev \
    libxml2-dev \
    zlib-dev \
    sqlite-dev \
    libssh2-dev

RUN git clone --depth 1 https://github.com/aria2/aria2.git /tmp/aria2 \
    && cd /tmp/aria2 \
    && autoreconf -i \
    && ./configure \
        --prefix=/usr \
        --with-openssl \
        --with-libcares \
        --with-libxml2 \
        --with-libz \
        --with-sqlite3 \
        --with-libssh2 \
        --enable-bittorrent \
        --enable-metalink \
        --enable-websocket \
    && make -j$(nproc) \
    && make install DESTDIR=/out

FROM alpine:3.20

RUN apk add --no-cache \
    openssl \
    c-ares \
    libxml2 \
    zlib \
    sqlite-libs \
    libssh2 \
    libstdc++ \
    curl

COPY --from=builder /out/usr/bin/aria2c /usr/bin/aria2c

RUN mkdir -p /downloads /aria2

COPY aria2.conf /aria2/aria2.conf
COPY entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh

EXPOSE 6800

ENTRYPOINT ["/entrypoint.sh"]
