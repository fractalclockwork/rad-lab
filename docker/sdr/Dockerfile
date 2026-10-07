# SDR toolchain with HackRF host tools matching firmware release 2026.01.3.
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    HACKRF_VERSION=2026.01.3

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        xz-utils \
        build-essential \
        cmake \
        pkg-config \
        libusb-1.0-0-dev \
        libfftw3-dev \
        python3 \
        python3-pip \
        python3-numpy \
        python3-scipy \
        python3-yaml \
        python3-soapysdr \
        soapysdr-tools \
        soapysdr-module-hackrf \
        libiio-utils \
        usbutils \
        dfu-util \
    && rm -rf /var/lib/apt/lists/*

# Build libhackrf + hackrf-tools from the archived release (not Ubuntu 2023.01.1).
COPY archive/cache/sdk/hackrf-${HACKRF_VERSION}.tar.xz /tmp/hackrf.tar.xz
RUN mkdir -p /tmp/hackrf-src \
    && tar -xJf /tmp/hackrf.tar.xz -C /tmp/hackrf-src --strip-components=1 \
    && cmake -S /tmp/hackrf-src/host -B /tmp/hackrf-build \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_INSTALL_PREFIX=/usr/local \
    && cmake --build /tmp/hackrf-build -j"$(nproc)" \
    && cmake --install /tmp/hackrf-build \
    && ldconfig \
    && rm -rf /tmp/hackrf.tar.xz /tmp/hackrf-src /tmp/hackrf-build \
    && hackrf_info 2>&1 | head -5 || true

# Firmware images live on the mounted repo at runtime:
# archive/cache/sdk/hackrf-2026.01.3/firmware-bin/hackrf_one_usb.bin

WORKDIR /work
COPY docker/sdr/entrypoint.sh /usr/local/bin/rad-lab-entrypoint
RUN chmod +x /usr/local/bin/rad-lab-entrypoint

ENTRYPOINT ["/usr/local/bin/rad-lab-entrypoint"]
CMD ["bash"]
