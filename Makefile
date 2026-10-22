BOARD ?= hackrf
STAGE ?= present
LAB ?= 01
export BOARD
PYTHON ?= python3
ifneq ($(wildcard .venv/bin/python),)
PYTHON := .venv/bin/python
endif

IMAGE ?= rad-lab-sdr
export PYTHONPATH := $(CURDIR):$(PYTHONPATH)

.PHONY: archive archive-image image stage sim hwil firmware check venv sdr lesson

venv:
	$(PYTHON) -m venv .venv
	.venv/bin/pip install -U pip
	.venv/bin/pip install -r requirements.txt

archive:
	$(PYTHON) -m environment.archive

image: archive
	docker build -t $(IMAGE) -f docker/sdr/Dockerfile .

archive-image: image
	$(PYTHON) -m environment.archive --save-image

sdr:
	$(PYTHON) -m environment.sdr_run $(SRC) $(ARGS)

stage:
	$(PYTHON) -m hardware.stages --board $(BOARD) --stage $(STAGE)

sim:
	RAD_LAB_HWIL_SIM=1 $(PYTHON) -c "from harness.radboards import load_board; from software.fixture import run_fixture; print(run_fixture(load_board('$(BOARD)')))"

build:
	@echo "SDR boards have no bitstream build; use make hwil after present/workflow."

hwil:
	$(PYTHON) -m hardware.stages --board $(BOARD) --stage image

firmware:
	$(PYTHON) -m hardware.firmware --board $(BOARD)

lesson:
	$(PYTHON) $$(ls lesson/labs/$(LAB)_*.py | head -1)

check:
	$(PYTHON) -m pytest -q
	$(MAKE) sim BOARD=hackrf
