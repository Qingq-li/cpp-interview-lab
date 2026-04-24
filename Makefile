UID ?= $(shell id -u)
GID ?= $(shell id -g)
ARCH ?= $(shell uname -m)
LAN_HOST ?= 0.0.0.0
LAN_PORT ?= 8000

COMPOSE_BASE = docker compose -f docker-compose.yml
COMPOSE_X86 = $(COMPOSE_BASE) -f docker-compose.x86.yml
COMPOSE_ARM = $(COMPOSE_BASE) -f docker-compose.arm.yml

ifeq ($(filter aarch64 arm64,$(ARCH)),)
COMPOSE_AUTO = $(COMPOSE_X86)
else
COMPOSE_AUTO = $(COMPOSE_ARM)
endif

.PHONY: help data server docker-build docker-up docker-down docker-up-x86 docker-up-arm docker-up-lan docker-logs

help:
	@echo "Targets:"
	@echo "  make server        Run the notebook server locally on the host (binds 0.0.0.0)"
	@echo "  make docker-up     Build and run the container with auto-detected platform"
	@echo "  make docker-up-x86 Force amd64 container"
	@echo "  make docker-up-arm Force arm64 container"
	@echo "  make docker-up-lan Same as docker-up, explicit LAN-accessible entrypoint"
	@echo "  make docker-down   Stop the container stack"
	@echo "  make docker-build  Build the container image"

data:
	mkdir -p data

server: data
	python3 tools/flashcards_app.py --host $(LAN_HOST) --port $(LAN_PORT)

docker-build: data
	UID=$(UID) GID=$(GID) $(COMPOSE_AUTO) build

docker-up: data
	UID=$(UID) GID=$(GID) $(COMPOSE_AUTO) up --build

docker-up-lan: docker-up

docker-up-x86: data
	UID=$(UID) GID=$(GID) $(COMPOSE_X86) up --build

docker-up-arm: data
	UID=$(UID) GID=$(GID) $(COMPOSE_ARM) up --build

docker-down:
	UID=$(UID) GID=$(GID) $(COMPOSE_AUTO) down

docker-logs:
	UID=$(UID) GID=$(GID) $(COMPOSE_AUTO) logs -f
