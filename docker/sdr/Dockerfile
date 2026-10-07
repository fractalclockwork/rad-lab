# Slim SDR toolchain image for rad-lab. Host-gated HIL prefers host Soapy/hackrf
# when available; this image is the reproducible lab/tool environment.
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        python3 \
        python3-pip \
        python3-numpy \
        python3-scipy \
        python3-yaml \
        python3-soapysdr \
        soapysdr-tools \
        soapysdr-module-hackrf \
        hackrf \
        libhackrf0 \
        libiio-utils \
        usbutils \
    && rm -rf /var/lib/apt/lists/*

# Ubuntu 24.04 has no soapysdr-module-plutosdr package. Pluto bring-up uses
# host IIO / a later image layer. GNU Radio is omitted to keep this image lean.


WORKDIR /work
COPY docker/sdr/entrypoint.sh /usr/local/bin/rad-lab-entrypoint
RUN chmod +x /usr/local/bin/rad-lab-entrypoint

ENTRYPOINT ["/usr/local/bin/rad-lab-entrypoint"]
CMD ["bash"]
