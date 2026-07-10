# Makefile for hc_weda

# --- 1. DYNAMISCHE PARAMETER & VARIABLEN ---
PROJECT_NAME = $(notdir $(CURDIR))
FORGEJO_IP   = 10.1.1.19
FORGEJO_PORT = 3143
FORGEJO_USER = peter
FORGEJO_URL  = http://$(FORGEJO_IP):$(FORGEJO_PORT)/$(FORGEJO_USER)/$(PROJECT_NAME).git

.DEFAULT_GOAL := help
.PHONY: build up down restart rebuild logs logs-tail ps stop start shell health run dev install clean help migrate

# ---------------------------------------------------------
# Python interpreter (venv preferred, fallback python3)
# ---------------------------------------------------------
CONTAINER := $(shell basename $(CURDIR))
PYTHON := $(shell if [ -f /dockerapps/apps_v2/.venv/bin/python ]; then echo /dockerapps/apps_v2/.venv/bin/python; else echo python3; fi)

# ---------------------------------------------------------
# Lokales Ausfuehren
# ---------------------------------------------------------
run: ## Startet lokal mit uvicorn
	@$(PYTHON) -m uvicorn app.main:app --host 0.0.0.0 --port 5045

dev: ## Startet lokal mit auto-reload
	@$(PYTHON) -m uvicorn app.main:app --host 0.0.0.0 --port 5045 --reload

apptest: ## Einfacher test ohne datenaubereitung
	@$(PYTHON) -m uvicorn app.main:app --host 0.0.0.0 --port 5049 --reload --lifespan off --no-access-log --reload-exclude "*.db"

# ---------------------------------------------------------
# Docker
# ---------------------------------------------------------
build: ## Build Docker image
	docker compose build

up: ## Start containers
	docker compose up -d

down: ## Stop containers
	docker compose down

restart: ## Restart containers
	docker compose restart

rebuild: ## Rebuild and restart (no cache)
	docker compose down
	docker compose build --no-cache
	docker compose up -d --force-recreate

logs: ## Show logs (follow)
	docker compose logs -f

logs-tail: ## Last 100 log lines
	docker compose logs --tail=100

ps: ## Running containers
	docker compose ps

stop: ## Stop containers
	docker compose stop

start: ## Start stopped containers
	docker compose start

shell: ## Shell into container
	docker compose exec $(CONTAINER) /bin/bash

health: ## Check health endpoint
	@curl -sf http://localhost:5045/api/health | python3 -m json.tool || echo "UNHEALTHY"

# ---------------------------------------------------------
# Development
# ---------------------------------------------------------
install: ## Install dependencies
	@pip install -r requirements.txt

clean: ## Remove cache files
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -name "*.pyc" -delete 2>/dev/null || true

jsbuild: ## Komprimiert CSS über Docker & esbuild
	@echo "📦 Starte JS & CSS Bundling via Docker & esbuild..."
	@cp ../shared/themes/theme.css frontend/static/css/theme.css
	@docker run --rm -v "$$(pwd)":/app -w /app node:20-alpine sh -c "\
		npx esbuild frontend/static/js/dashboard.js --bundle --minify --sourcemap --target=es2020 --outfile=frontend/static/js/dashboard.bundle.js && \
		npx esbuild frontend/static/css/dashboard.css --bundle --minify --sourcemap --outfile=frontend/static/css/dashboard.bundle.css"
	@echo "✅ Fertig!"

# ---------------------------------------------------------
# Database & Migration
# ---------------------------------------------------------
migrate: ## Migrate v1 data to v2 (history.db -> weather.db)
	@echo "=== Migrating v1 → v2 ==="
	@$(PYTHON) scripts/migrate_v1_to_v2.py

migrate-check: ## Check migration status
	@echo "=== v1 Database (history.db) ==="
	@if [ -f /dockerapps/apps_v1/hc_weda/data/history.db ]; then \
		echo "✓ v1 DB exists"; \
		sqlite3 /dockerapps/apps_v1/hc_weda/data/history.db "SELECT COUNT(*) || ' measurements' FROM measurements"; \
		sqlite3 /dockerapps/apps_v1/hc_weda/data/history.db "SELECT 'Range: ' || MIN(dateutc) || ' to ' || MAX(dateutc) FROM measurements"; \
	else \
		echo "✗ v1 DB not found"; \
	fi
	@echo ""
	@echo "=== v2 Database (weather.db) ==="
	@if [ -f data/weather.db ]; then \
		echo "✓ v2 DB exists"; \
		sqlite3 data/weather.db "SELECT COUNT(*) || ' measurements' FROM measurements"; \
		sqlite3 data/weather.db "SELECT 'Range: ' || MIN(dateutc) || ' to ' || MAX(dateutc) FROM measurements"; \
	else \
		echo "✗ v2 DB not found (run 'make migrate')"; \
	fi

backup: ## Create backup of data and logs
	@mkdir -p ~/backups
	@tar -czf ~/backups/hc_weda_$(shell date +%Y%m%d_%H%M%S).tar.gz data/ logs/
	@echo "Backup created in ~/backups/"

db-schema: ## Schema als SQL ins Repo exportieren (ohne Daten)
	@sqlite3 data/weather.db ".schema" > data/schema.sql
	@echo "✓ Schema exportiert: data/schema.sql"

backup-v1: ## Backup v1 database before migration
	@if [ -f /dockerapps/apps_v1/hc_weda/data/history.db ]; then \
		cp /dockerapps/apps_v1/hc_weda/data/history.db \
		   /dockerapps/apps_v1/hc_weda/data/history.db.backup_$(shell date +%Y%m%d_%H%M%S); \
		echo "✓ v1 backup created"; \
	else \
		echo "✗ v1 DB not found"; \
	fi

db-check: ## Check database integrity
	@sqlite3 data/weather.db "PRAGMA integrity_check;"

db-stats: ## Show database statistics
	@echo "=== Database Statistics ==="
	@echo "Measurements count:"
	@sqlite3 data/weather.db "SELECT COUNT(*) FROM measurements;"
	@echo "Date range:"
	@sqlite3 data/weather.db "SELECT MIN(dateutc), MAX(dateutc) FROM measurements;"
	@echo "Database size:"
	@ls -lh data/weather.db | awk '{print $$5}'

db-vacuum: ## Vacuum database (optimize)
	@sqlite3 data/weather.db "VACUUM;"
	@echo "Database vacuumed"

db-latest: ## Show latest weather reading
	@sqlite3 data/weather.db "SELECT dateutc, temp_c, humidity, windspeed_kmh, pressure_hpa FROM measurements ORDER BY dateutc DESC LIMIT 1"

# ---------------------------------------------------------
# Testing
# ---------------------------------------------------------
test-receiver: ## Test weather receiver endpoint (simulate weather station)
	@echo "=== Testing Weather Receiver ==="
	@echo "Sending test data to http://localhost:5045/weatherstation"
	@curl -X GET "http://localhost:5045/weatherstation?tempf=68.5&humidity=65&windspeedmph=5.2&winddir=180&baromin=29.92&dailyrainin=0.5&solarradiation=450&uv=3&indoortempf=72&indoorhumidity=55&dateutc=2026-05-09+14:30:00" | python3 -m json.tool

test-device: ## Test weather station connectivity
	@echo "=== Weather Station Test ==="
	@echo "Device: Sainlogic WS3500"
	@echo "Receiver: http://localhost:8089/weatherstation"
	@echo ""
	@echo "Waiting for data from weather station..."
	@echo "(Station sends data every 60 seconds)"

stop-app: ## Stop running app (manual: Ctrl+C or kill PID)
	@if lsof -ti:5045 >/dev/null 2>&1; then \
		echo "App is running on port 5045 (PID: $$(lsof -ti:5045))"; \
		echo "Stop manually: kill $$(lsof -ti:5045)"; \
	else \
		echo "ℹ️  App not running"; \
	fi

status-app: ## Check if app is running
	@if lsof -ti:5045 >/dev/null 2>&1; then \
		echo "✓ App is running on port 5045 (PID: $$(lsof -ti:5045))"; \
		echo "✓ Dashboard: http://localhost:5045"; \
		echo "✓ Weather Receiver: http://localhost:8089/weatherstation"; \
	else \
		echo "✗ App not running"; \
		echo "  Start: make dev / make run"; \
	fi

graph:
	pyreverse app -o png

git-status: ## Zeigt die aktuelle Forgejo Server-Verbindung (Remote URL) an
	@echo "🔍 Überprüfe Git-Remote-Konfiguration..."
	@if ! git remote get-url origin >/dev/null 2>&1; then \
		echo "❌ Fehler: 'origin' ist noch nicht eingerichtet!"; \
		echo "👉 Bitte führe aus: make git-setup"; \
		exit 1; \
	fi
	@URL=$$(git remote get-url origin); \
	echo "🍏 Forgejo-Server ist aktiv verbunden!" ; \
	echo "🔗 Aktuelle URL: $$URL"

git-setup: ## Git-Verbindung zum Forgejo-Server automatisch einrichten oder korrigieren
	@echo "🛠️ Initialisiere Forgejo Server-Verbindung für '$(PROJECT_NAME)'..."
	@if ! git remote get-url origin >/dev/null 2>&1; then \
		git remote add origin $(FORGEJO_URL); \
		echo "🎉 Server-URL erfolgreich neu angelegt!"; \
	else \
		git remote set-url origin $(FORGEJO_URL); \
		echo "🔄 Bestehende Server-URL erfolgreich korrigiert!"; \
	fi
	@echo "🔗 Ziel-Adresse: $(FORGEJO_URL)"

git-update: git-status ## Git Forgejo Update durchführen (Normaler Zwischenstand)
	git add -A
	git commit -m "Update am $$(date +'%Y-%m-%d %H:%M')" || true
	git push -u origin main

git-release: git-status ## Neues Versions-Tag automatisch berechnen, erstellen und zu Forgejo pushen
	git add -A
	git commit -m "Release-Vorbereitung am $$(date +'%Y-%m-%d %H:%M')" || true
	git push origin main
	@LAST_TAG=$$(git describe --tags --abbrev=0 2>/dev/null || echo "v2.1.0"); \
	NEXT_TAG=$$(echo $$LAST_TAG | awk -F. '{print $$1"."$$2"."$$3+1}'); \
	echo "🍏 Letzte Version war: $$LAST_TAG"; \
	echo "⚡ Berechnete neue Version: $$NEXT_TAG"; \
	echo "📦 Erstelle Git-Tag $$NEXT_TAG mit aktuellem Zeitstempel..."; \
	git tag -a $$NEXT_TAG -m "Automatisches Release $$NEXT_TAG am $$(date +'%Y-%m-%d %H:%M') via Makefile"; \
	git push origin $$NEXT_TAG; \
	echo "🎉 Version $$NEXT_TAG erfolgreich an Forgejo übermittelt!"


# ---------------------------------------------------------
# Help
# ---------------------------------------------------------
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'
