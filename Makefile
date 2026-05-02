UID ?= $(shell id -u)
GID ?= $(shell id -g)
ARCH ?= $(shell uname -m)
LAN_HOST ?= 0.0.0.0
LAN_PORT ?= 8000
HOST_PORT ?= 8000
Raspberry_Pi_5_ip ?=172.29.49.234


COMPOSE_BASE = docker compose -f docker-compose.yml
COMPOSE_X86 = $(COMPOSE_BASE) -f docker-compose.x86.yml
COMPOSE_ARM = $(COMPOSE_BASE) -f docker-compose.arm.yml

ifeq ($(filter aarch64 arm64,$(ARCH)),)
COMPOSE_AUTO = $(COMPOSE_X86)
else
COMPOSE_AUTO = $(COMPOSE_ARM)
endif

.PHONY: help data server docker-build docker-up docker-down docker-up-x86 docker-up-arm docker-up-lan docker-logs rspi5-sync rspi5-ssh rspi5-run-server-test rspi5-run-server-tmux rspi5-install-autostart

help:
	@echo "Targets:"
	@echo "  make server        Run the notebook server locally on the host (binds 0.0.0.0)"
	@echo "  make docker-up     Build and run the container with auto-detected platform"
	@echo "  make docker-up-x86 Force amd64 container"
	@echo "  make docker-up-arm Force arm64 container"
	@echo "  make docker-up-lan Same as docker-up, explicit LAN-accessible entrypoint"
	@echo "  make docker-up-arm HOST_PORT=8001  Use a different host port if 8000 is busy"
	@echo "  make docker-down   Stop the container stack"
	@echo "  make docker-build  Build the container image"
	@echo "  make rspi5-install-autostart  Install and start the Raspberry Pi 5 boot service"

data:
	mkdir -p data

server: data
	python3 tools/flashcards_app.py --host $(LAN_HOST) --port $(LAN_PORT)

docker-build: data
	UID=$(UID) GID=$(GID) HOST_PORT=$(HOST_PORT) $(COMPOSE_AUTO) build

docker-up: data
	UID=$(UID) GID=$(GID) HOST_PORT=$(HOST_PORT) $(COMPOSE_AUTO) up --build

docker-up-lan: docker-up

docker-up-x86: data
	UID=$(UID) GID=$(GID) HOST_PORT=$(HOST_PORT) $(COMPOSE_X86) up --build

docker-up-arm: data
	UID=$(UID) GID=$(GID) HOST_PORT=$(HOST_PORT) $(COMPOSE_ARM) up --build

docker-down:
	UID=$(UID) GID=$(GID) HOST_PORT=$(HOST_PORT) $(COMPOSE_AUTO) down

docker-logs:
	UID=$(UID) GID=$(GID) HOST_PORT=$(HOST_PORT) $(COMPOSE_AUTO) logs -f

rspi5-sync: # rsync the current directory to the Raspberry Pi 5, excluding the data directory and any __pycache__ directories
	rsync -avz --exclude 'data' --exclude '__pycache__' --exclude 'build' --exclude 'cpp_awssome_project/example' . prefor@$(Raspberry_Pi_5_ip):~/flashcards

rspi5-ssh:
	ssh prefor@$(Raspberry_Pi_5_ip)  

# ssh to Raspberry Pi 5 and run the architecture-appropriate docker-compose command to start the server
rspi5-run-server-test: rspi5-sync
	ssh prefor@$(Raspberry_Pi_5_ip) 'cd flashcards && HOST_PORT=$${HOST_PORT:-8000} docker compose -f docker-compose.yml -f docker-compose.arm.yml up --build'

rspi5-run-server-tmux: rspi5-sync
	ssh prefor@$(Raspberry_Pi_5_ip) 'cd flashcards && tmux new-session -d -s flashcards_server "HOST_PORT=$${HOST_PORT:-8000} docker compose -f docker-compose.yml -f docker-compose.arm.yml up --build" || tmux send-keys -t flashcards_server "HOST_PORT=$${HOST_PORT:-8000} docker compose -f docker-compose.yml -f docker-compose.arm.yml up --build" C-m'

rspi5-install-autostart: rspi5-sync
	ssh prefor@$(Raspberry_Pi_5_ip) 'mkdir -p "$$HOME/.config/systemd/user" && printf "%s\n" \
		"[Unit]" \
		"Description=Flashcards Docker Compose server" \
		"After=network-online.target docker.service" \
		"Wants=network-online.target" \
		"" \
		"[Service]" \
		"Type=simple" \
		"WorkingDirectory=%h/flashcards" \
		"Environment=HOST_PORT=$${HOST_PORT:-8000}" \
		"ExecStart=/bin/sh -lc '\''UID=$$(id -u) GID=$$(id -g) HOST_PORT=$${HOST_PORT:-8000} docker compose -f docker-compose.yml -f docker-compose.arm.yml up --build'\''" \
		"ExecStop=/bin/sh -lc '\''UID=$$(id -u) GID=$$(id -g) HOST_PORT=$${HOST_PORT:-8000} docker compose -f docker-compose.yml -f docker-compose.arm.yml down'\''" \
		"Restart=always" \
		"RestartSec=10" \
		"" \
		"[Install]" \
		"WantedBy=default.target" \
		> "$$HOME/.config/systemd/user/flashcards.service" && \
		loginctl enable-linger "$$(whoami)" && \
		systemctl --user daemon-reload && \
		systemctl --user enable --now flashcards.service && \
		systemctl --user --no-pager status flashcards.service'
