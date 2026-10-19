BOARD ?= hackrf
STAGE ?= present
export BOARD
PYTHON ?= python3
ifneq ($(wildcard .venv/bin/python),)
PYTHON := .venv/bin/python
endif

IMAGE ?= rad-lab-sdr
export PYTHONPATH := $(CURDIR)/hil/scripts:$(PYTHONPATH)

.PHONY: archive archive-image image stage sim hil firmware check venv sdr

venv:
	$(PYTHON) -m venv .venv
	.venv/bin/pip install -U pip
	.venv/bin/pip install -r requirements.txt

archive:
	$(PYTHON) hil/scripts/archive.py

image: archive
	docker build -t $(IMAGE) -f docker/sdr/Dockerfile .

archive-image: image
	$(PYTHON) hil/scripts/archive.py --save-image

# Container-only SDR dev-run. Every SDR binary (hackrf_info / hackrf_transfer /
# SoapySDRUtil / iio_info / dfu-util, plus the bring-up labs) executes inside
# rad-lab-sdr; the dev-host never exercises RF hardware. `lsusb` and report-file
# writes remain host-side informational operations.
sdr:
	$(PYTHON) hil/scripts/sdr_run.py $(SRC) $(ARGS)

stage:
	$(PYTHON) hil/scripts/stage.py --board $(BOARD) --stage $(STAGE)

sim:
	RAD_LAB_HIL_SIM=1 $(PYTHON) -c "from radboards import load_board; from fixture import run_fixture; print(run_fixture(load_board('$(BOARD)')))"

build:
	@echo "SDR boards have no bitstream build; use make hil after present/workflow."

hil:
	$(PYTHON) hil/scripts/stage.py --board $(BOARD) --stage image

firmware:
	$(PYTHON) hil/scripts/firmware.py --board $(BOARD)

check:
	$(PYTHON) -m pytest -q
	$(MAKE) sim BOARD=hackrf
