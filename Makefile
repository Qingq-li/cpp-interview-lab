UID ?= $(shell id -u)
GID ?= $(shell id -g)
ARCH ?= $(shell uname -m)
LAN_HOST ?= 0.0.0.0
LAN_PORT ?= 8000
HOST_PORT ?= 8000

REMOTE_USER ?= prefor
REMOTE_HOST ?= 172.29.49.234
REMOTE_DIR ?= flashcards
REMOTE_PORT ?= 8000
REMOTE_TMUX_SESSION ?= flashcards_server

KUBECTL ?= kubectl
K8S_NAMESPACE ?= flashcards
K8S_APP ?= cpp-interview-lab
K8S_CONTAINER ?= cpp-interview-lab
K8S_IMAGE ?= cpp-interview-lab:latest
K8S_STORAGE_SIZE ?= 1Gi
K8S_NODE_PORT ?= 30080
K8S_LOCAL_PORT ?= 8000
K8S_DIR ?= k8s
K8S_PLATFORM ?=

COMPOSE_BASE = docker compose -f docker-compose.yml
COMPOSE_PLATFORM = $(if $(filter aarch64 arm64,$(ARCH)),-f docker-compose.arm.yml,-f docker-compose.x86.yml)
COMPOSE_LOCAL = $(COMPOSE_BASE) $(COMPOSE_PLATFORM)

K8S_RENDER = sed \
	-e "s|__K8S_NAMESPACE__|$(K8S_NAMESPACE)|g" \
	-e "s|__K8S_APP__|$(K8S_APP)|g" \
	-e "s|__K8S_CONTAINER__|$(K8S_CONTAINER)|g" \
	-e "s|__K8S_IMAGE__|$(K8S_IMAGE)|g" \
	-e "s|__K8S_STORAGE_SIZE__|$(K8S_STORAGE_SIZE)|g" \
	-e "s|__K8S_NODE_PORT__|$(K8S_NODE_PORT)|g"

.PHONY: help data server docker-build docker-up docker-down docker-logs remote-sync remote-ssh remote-run remote-tmux remote-restart-tmux remote-install-autostart k8s-build k8s-push k8s-apply k8s-deploy k8s-logs k8s-port-forward

help:
	@echo "Targets:"
	@echo "  make server                        Run the notebook server locally on the host"
	@echo "  make docker-build                  Build the local container image"
	@echo "  make docker-up                     Build and run the local container stack"
	@echo "  make docker-down                   Stop the local container stack"
	@echo "  make docker-logs                   Follow local container logs"
	@echo "  make remote-sync                   Rsync the repo to the remote host"
	@echo "  make remote-ssh                    Open an SSH session to the remote host"
	@echo "  make remote-run                    Sync and start Docker Compose on the remote host"
	@echo "  make remote-tmux                   Restart the remote tmux service"
	@echo "  make remote-install-autostart      Install the remote user systemd service"
	@echo "  make k8s-build                     Build the Kubernetes image"
	@echo "  make k8s-push                      Push the Kubernetes image"
	@echo "  make k8s-apply                     Apply the Kubernetes manifests"
	@echo "  make k8s-deploy                    Build, push, apply, and restart the deployment"
	@echo "  make k8s-logs                      Follow Kubernetes pod logs"
	@echo "  make k8s-port-forward              Forward local port to the Kubernetes service"

data:
	mkdir -p data

server: data
	python3 tools/flashcards_app.py --host $(LAN_HOST) --port $(LAN_PORT)

docker-build: data
	UID=$(UID) GID=$(GID) HOST_PORT=$(HOST_PORT) $(COMPOSE_LOCAL) build

docker-up: data
	UID=$(UID) GID=$(GID) HOST_PORT=$(HOST_PORT) $(COMPOSE_LOCAL) up --build

docker-down:
	UID=$(UID) GID=$(GID) HOST_PORT=$(HOST_PORT) $(COMPOSE_LOCAL) down

docker-logs:
	UID=$(UID) GID=$(GID) HOST_PORT=$(HOST_PORT) $(COMPOSE_LOCAL) logs -f

remote-sync:
	rsync -avz --exclude '.git' --exclude 'data' --exclude '__pycache__' --exclude 'build' --exclude 'cpp_awssome_project/example' . $(REMOTE_USER)@$(REMOTE_HOST):$(REMOTE_DIR)

remote-ssh:
	ssh $(REMOTE_USER)@$(REMOTE_HOST)

remote-run: remote-sync
	ssh $(REMOTE_USER)@$(REMOTE_HOST) 'cd $(REMOTE_DIR) && UID=$$(id -u) GID=$$(id -g) HOST_PORT=$${HOST_PORT:-$(REMOTE_PORT)} docker compose -f docker-compose.yml up --build'

remote-tmux: remote-sync
	ssh $(REMOTE_USER)@$(REMOTE_HOST) 'tmux kill-session -t $(REMOTE_TMUX_SESSION) 2>/dev/null || true; cd $(REMOTE_DIR) && tmux new-session -d -s $(REMOTE_TMUX_SESSION) "UID=$$(id -u) GID=$$(id -g) HOST_PORT=$${HOST_PORT:-$(REMOTE_PORT)} docker compose -f docker-compose.yml up --build"'

remote-restart-tmux: remote-tmux

remote-install-autostart: remote-sync
	ssh $(REMOTE_USER)@$(REMOTE_HOST) 'mkdir -p "$$HOME/.config/systemd/user" && printf "%s\n" \
		"[Unit]" \
		"Description=Flashcards Docker Compose server" \
		"After=network-online.target docker.service" \
		"Wants=network-online.target" \
		"" \
		"[Service]" \
		"Type=simple" \
		"WorkingDirectory=%h/$(REMOTE_DIR)" \
		"Environment=HOST_PORT=$(REMOTE_PORT)" \
		"ExecStart=/bin/sh -lc '\''cd %h/$(REMOTE_DIR) && UID=$$(id -u) GID=$$(id -g) HOST_PORT=$$HOST_PORT docker compose -f docker-compose.yml up --build'\''" \
		"ExecStop=/bin/sh -lc '\''cd %h/$(REMOTE_DIR) && UID=$$(id -u) GID=$$(id -g) HOST_PORT=$$HOST_PORT docker compose -f docker-compose.yml down'\''" \
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

k8s-build:
	docker build $(if $(strip $(K8S_PLATFORM)),--platform $(K8S_PLATFORM),) -t $(K8S_IMAGE) .

k8s-push:
	docker push $(K8S_IMAGE)

k8s-apply:
	@set -e; \
	for manifest in $(K8S_DIR)/namespace.yaml.in $(K8S_DIR)/pvc.yaml.in $(K8S_DIR)/deployment.yaml.in $(K8S_DIR)/service.yaml.in; do \
		$(K8S_RENDER) "$$manifest" | $(KUBECTL) apply -f -; \
	done

k8s-deploy: k8s-build k8s-push k8s-apply
	$(KUBECTL) -n $(K8S_NAMESPACE) rollout restart deployment/$(K8S_APP)
	$(KUBECTL) -n $(K8S_NAMESPACE) rollout status deployment/$(K8S_APP)

k8s-logs:
	$(KUBECTL) -n $(K8S_NAMESPACE) logs -f deploy/$(K8S_APP)

k8s-port-forward:
	$(KUBECTL) -n $(K8S_NAMESPACE) port-forward svc/$(K8S_APP) $(K8S_LOCAL_PORT):8000
