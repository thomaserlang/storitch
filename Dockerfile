FROM python:3.12-slim-bookworm AS pybuilder
COPY . .
RUN pip wheel . --wheel-dir=/wheels

FROM dpokidov/imagemagick:7.1.1-41-bullseye AS imagemagick

FROM python:3.12-slim-bookworm

RUN apt-get update && apt-get upgrade -y && apt-get install -y wget


# ImageMagick (https://github.com/dooman87/imagemagick-docker) 
ARG IM_VERSION=7.1.1-44
ARG LIB_HEIF_VERSION=1.19.5
ARG LIB_AOM_VERSION=3.11.0
ARG LIB_WEBP_VERSION=1.4.0
ARG LIBJXL_VERSION=0.11.0

RUN apt-get install -y --no-install-recommends git make pkg-config autoconf curl cmake clang libomp-dev ca-certificates automake \
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
    # Building libwebp
    git clone -b v${LIB_WEBP_VERSION} --depth 1 https://chromium.googlesource.com/webm/libwebp && \
    cd libwebp && \
    mkdir build && cd build && cmake -DBUILD_SHARED_LIBS=ON ../ && make && make install && \
    ldconfig /usr/local/lib && \
    cd ../../ && rm -rf libwebp && \
    # Building libjxl
    git clone -b v${LIBJXL_VERSION} https://github.com/libjxl/libjxl.git --depth 1 --recursive --shallow-submodules && \
    cd libjxl && \
    mkdir build && \
    cd build && \
    cmake -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF -DJPEGXL_FORCE_SYSTEM_BROTLI=ON -DJPEGXL_FORCE_SYSTEM_LCMS2=ON .. && \
    cmake --build . -- -j$(nproc) && \
    cmake --install . && \
    cd ../../ && \
    rm -rf libjxl && \
    ldconfig /usr/local/lib && \
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
    cd libheif/ && \
    mkdir build && cd build && cmake --preset=release .. && make && make install && cd ../../ && \
    ldconfig /usr/local/lib && \
    rm -rf libheif && \
    # Building ImageMagick
    git clone -b ${IM_VERSION} --depth 1 https://github.com/ImageMagick/ImageMagick.git && \
    cd ImageMagick && \
    LIBS="-lsharpyuv" ./configure --without-magick-plus-plus --disable-docs --disable-static --with-tiff --with-jxl --with-tcmalloc && \
    make && make install && \
    ldconfig /usr/local/lib && \
    apt-get remove --autoremove --purge -y make cmake clang clang-14 curl yasm git autoconf automake pkg-config libpng-dev libjpeg62-turbo-dev libde265-dev libx265-dev libxml2-dev libtiff-dev libfontconfig1-dev libfreetype6-dev liblcms2-dev libsdl1.2-dev libgif-dev libbrotli-dev && \
    rm -rf /var/lib/apt/lists/* && \
    rm -rf /ImageMagick


ENV \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH="${PYTHONPATH}:." \
    UID=1000 \
    GID=1000

RUN mkdir /app
WORKDIR /app
COPY . .
COPY --from=pybuilder /wheels /wheels

RUN mv conf/policy.xml /usr/local/etc/ImageMagick-7/policy.xml
RUN mv conf/mime.types /etc/mime.types

RUN pip install --find-links=/wheels -e .
RUN rm -rf /wheels

RUN addgroup --gid $GID --system storitch && adduser --uid $UID --gid $GID storitch && \
    mkdir /var/storitch && chown $UID:$GID -R /var/storitch
USER $UID:$GID
RUN mkdir /tmp/imagemagick

VOLUME /var/storitch
ENTRYPOINT ["python", "storitch/runner.py"]