BOARD ?= hackrf
STAGE ?= present
export BOARD
PYTHON ?= python3
ifneq ($(wildcard .venv/bin/python),)
PYTHON := .venv/bin/python
endif

IMAGE ?= rad-lab-sdr
export PYTHONPATH := $(CURDIR)/scripts:$(PYTHONPATH)

.PHONY: archive archive-image image stage sim hil check venv

venv:
	$(PYTHON) -m venv .venv
	.venv/bin/pip install -U pip
	.venv/bin/pip install -r requirements.txt

archive:
	$(PYTHON) scripts/archive.py

image:
	docker build -t $(IMAGE) -f docker/sdr/Dockerfile .

archive-image: image
	$(PYTHON) scripts/archive.py --save-image

stage:
	$(PYTHON) scripts/stage.py --board $(BOARD) --stage $(STAGE)

sim:
	RAD_LAB_HIL_SIM=1 $(PYTHON) -c "from radboards import load_board; from fixture import run_fixture; print(run_fixture(load_board('$(BOARD)')))"

build:
	@echo "SDR boards have no bitstream build; use make hil after present/workflow."

hil:
	$(PYTHON) scripts/stage.py --board $(BOARD) --stage image

check:
	$(PYTHON) -m pytest -q
	$(MAKE) sim BOARD=hackrf
