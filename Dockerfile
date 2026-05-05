FROM ghcr.io/astral-sh/uv:python3.14-trixie AS pybuilder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-workspace --no-dev

COPY . /app

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

ENV JEMALLOC_VERSION=5.3.0

RUN apt-get update && \
    apt-get install -yq wget pwgen gcc make bzip2 && \
    rm -rf /var/lib/apt/lists/* && \
    wget -q https://github.com/jemalloc/jemalloc/releases/download/$JEMALLOC_VERSION/jemalloc-$JEMALLOC_VERSION.tar.bz2 && \
    tar jxf jemalloc-*.tar.bz2 && \
    rm jemalloc-*.tar.bz2 && \
    cd jemalloc-* && \
    ./configure --enable-prof --enable-stats --enable-debug --enable-fill && \
    make && \
    make install && \
    cd - && \
    rm -rf jemalloc-* && \
    apt-get remove -yq wget pwgen gcc make bzip2 && \
    rm -rf /usr/share/doc /usr/share/man && \
    apt-get clean autoclean && \
    apt-get autoremove -y && \
    rm -rf /var/lib/{apt,dpkg,cache,log}/

FROM python:3.14-slim-trixie

# ImageMagick (https://github.com/dooman87/imagemagick-docker)
ARG IM_VERSION=7.1.2-21
ARG LIB_HEIF_VERSION=1.21.2
ARG LIB_AOM_VERSION=3.13.1
ARG LIB_WEBP_VERSION=1.6.0
ARG LIBJXL_VERSION=0.11.2

RUN apt-get -y update && \
    apt-get -y upgrade && \
    apt-get install -y --no-install-recommends git make pkg-config autoconf curl cmake clang libomp-dev ca-certificates automake \
    # libaom
    yasm \
    # libheif
    libde265-0 libde265-dev libjpeg62-turbo libjpeg62-turbo-dev x265 libx265-dev libtool \
    # libwebp
    libsdl1.2-dev libgif-dev \
    # libjxl
    libbrotli-dev \
    # IM
    libpng16-16 libpng-dev libjpeg62-turbo libjpeg62-turbo-dev libgomp1 ghostscript libxml2-dev libxml2-utils libtiff-dev libfontconfig1-dev libfreetype6-dev fonts-dejavu liblcms2-2 liblcms2-dev libtcmalloc-minimal4 \
    # Install manually to prevent deleting with -dev packages
    libxext6 libbrotli1 && \
    export CC=clang CXX=clang++ && \
    # Building libjxl
    git clone -b v${LIBJXL_VERSION} https://github.com/libjxl/libjxl.git --depth 1 --recursive --shallow-submodules && \
    cd libjxl && \
    mkdir build && \
    cd build && \
    cmake -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF .. && \
    cmake --build . -- -j$(nproc) && \
    cmake --install . && \
    cd ../../ && \
    rm -rf libjxl && \
    ldconfig /usr/local/lib && \
    # Building libwebp
    git clone -b v${LIB_WEBP_VERSION} --depth 1 https://chromium.googlesource.com/webm/libwebp && \
    cd libwebp && \
    mkdir build && cd build && cmake -DBUILD_SHARED_LIBS=ON ../ && make && make install && \
    ldconfig /usr/local/lib && \
    cd ../../ && rm -rf libwebp && \
    # Building libaom
    git clone -b v${LIB_AOM_VERSION} --depth 1 https://aomedia.googlesource.com/aom && \
    mkdir build_aom && \
    cd build_aom && \
    cmake ../aom/ -DENABLE_TESTS=0 -DBUILD_SHARED_LIBS=1 && make && make install && \
    ldconfig /usr/local/lib && \
    cd .. && \
    rm -rf aom && \
    rm -rf build_aom && \
    # Building libheif
    git clone -b v${LIB_HEIF_VERSION} --depth 1 https://github.com/strukturag/libheif.git && \
    cd libheif/ && mkdir build && cd build && cmake --preset=release .. && make && make install && cd ../../ && \
    ldconfig /usr/local/lib && \
    rm -rf libheif && \
    # Building ImageMagick
    git clone -b ${IM_VERSION} --depth 1 https://github.com/ImageMagick/ImageMagick.git && \
    cd ImageMagick && \
    ./configure --without-magick-plus-plus --disable-docs --disable-static --with-tiff --with-jxl --with-tcmalloc && \
    make && make install && \
    ldconfig /usr/local/lib && \
    apt-get remove --autoremove --purge -y make cmake clang clang-19 curl yasm git autoconf automake pkg-config libpng-dev libjpeg62-turbo-dev libde265-dev libx265-dev libxml2-dev libtiff-dev libfontconfig1-dev libfreetype6-dev liblcms2-dev libsdl1.2-dev libgif-dev libbrotli-dev && \
    rm -rf /var/lib/apt/lists/* && \
    rm -rf /ImageMagick


COPY --from=pybuilder /usr/local/lib/libjemalloc.so /usr/local/lib/libjemalloc.so
ENV LD_PRELOAD="/usr/local/lib/libjemalloc.so"
ENV MALLOC_CONF="background_thread:true,dirty_decay_ms:5000,muzzy_decay_ms:5000,narenas:2,tcache_max:8192"


COPY --from=pybuilder --chown=app:app /app /app

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="."

ENV UID=1000 \
    GID=1000

RUN mv /app/conf/policy.xml /usr/local/etc/ImageMagick-7/policy.xml
RUN mv /app/conf/mime.types /etc/mime.types

RUN addgroup --gid $GID --system storitch && adduser --uid $UID --gid $GID storitch && \
    mkdir /var/storitch && chown $UID:$GID -R /var/storitch
USER $UID:$GID
RUN mkdir /tmp/imagemagick

WORKDIR /app

VOLUME /var/storitch
ENTRYPOINT ["python", "storitch/runner.py"]
