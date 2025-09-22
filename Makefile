.PHONY: all help start stop restart run clean

COMPOSE ?= docker compose
SYS_PYTHON ?= python
VENV ?= .venv
VENV_BIN ?= $(VENV)/bin
VENV_PYTHON ?= $(VENV_BIN)/python
PIP ?= $(VENV_BIN)/pip
REQUIREMENTS ?= res/engine/requirements.txt res/dashboard/requirements.txt
VENV_STAMP ?= $(VENV)/.requirements.stamp

all: help

help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "Targets:"
	@echo "  start    Build and start the docker stack"
	@echo "  stop     Stop the docker stack and remove orphans"
	@echo "  restart  Restart the docker stack"
	@echo "  run      Execute the trading bot without docker"
	@echo "  venv     Update the local virtualenv with project deps"
	@echo "  clean    Remove python build artifacts"

start:
	$(COMPOSE) up --detach --build --force-recreate

stop:
	$(COMPOSE) down --remove-orphans --volumes

restart: stop start

run: $(VENV_PYTHON)
	$(VENV_PYTHON) src/engine.py


$(VENV_PYTHON): $(VENV_STAMP)

venv: $(VENV_STAMP)

$(VENV_STAMP): $(REQUIREMENTS)
	$(SYS_PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r res/engine/requirements.txt -r res/dashboard/requirements.txt
	touch $(VENV_STAMP)

clean:
	@find . -name '__pycache__' -type d -prune -exec rm -rf {} +
	@find . -name '*.pyc' -delete
