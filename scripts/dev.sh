#!/usr/bin/env bash
#
# RAZOR — start / stop the full demo stack with one command.
#
#   ./scripts/dev.sh start                 start Redis + backend + frontend
#   ./scripts/dev.sh start --worker        ... plus the Celery worker
#   ./scripts/dev.sh stop                  stop everything this tool started
#   ./scripts/dev.sh restart [--worker]    stop, then start
#   ./scripts/dev.sh status                show what's running
#
# Requires: a local PostgreSQL (managed service, reachable via DATABASE_URL),
# Node + npm in `web/`, and a Python virtualenv at `.venv/`.
#
# Processes run in the background and are tracked via PIDs under
# `scripts/.dev/`. Logs are written there too:
#   scripts/.dev/backend.log  scripts/.dev/frontend.log  scripts/.dev/worker.log
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# Always operate from the repo root so .env / relative config resolve no matter
# where the script is invoked from.
cd "$ROOT"
DEV_DIR="$ROOT/scripts/.dev"
mkdir -p "$DEV_DIR"

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-3050}"
API_URL="${NEXT_PUBLIC_API_URL:-http://localhost:$BACKEND_PORT}"

VENV_PY="$ROOT/.venv/bin/python"
WEB="$ROOT/web"

RST='\033[0m'; BLUE='\033[1;34m'; GRN='\033[1;32m'; YEL='\033[1;33m'; RED='\033[1;31m'

log(){ echo -e "${BLUE}[dev]${RST} $*"; }
ok(){ echo -e "${GRN}  ✓${RST} $*"; }
warn(){ echo -e "${YEL}  !${RST} $*"; }
err(){ echo -e "${RED}  ✗${RST} $*"; }

pidfile(){ echo "$DEV_DIR/$1.pid"; }
save_pid(){ echo "$2" > "$(pidfile "$1")"; }
read_pid(){ local f; f="$(pidfile "$1")"; [[ -f "$f" ]] && cat "$f" || echo ""; }
is_running(){ local p; p="$(read_pid "$1")"; [[ -n "$p" ]] && kill -0 "$p" 2>/dev/null; }

# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

check_prereqs() {
  [[ -x "$VENV_PY" ]] || { err "venv not found at .venv/. Run: python -m venv .venv"; return 1; }
  [[ -d "$WEB/node_modules" ]] || { err "web deps missing. Run: cd web && npm install"; return 1; }
  command -v redis-server >/dev/null 2>&1 || true
  if ! (command -v redis-cli >/dev/null 2>&1 && timeout 2 redis-cli ping >/dev/null 2>&1); then
    warn "Redis is not running — I'll try to start it."
  fi
  if ! "$VENV_PY" -c "from sqlalchemy import text; from db.database import SessionLocal; s=SessionLocal(); s.execute(text('SELECT 1')); s.close()" 2>"$DEV_DIR/dbcheck.err" >/dev/null; then
    err "PostgreSQL unreachable via DATABASE_URL."
    warn "resolved host: $("$VENV_PY" -c 'from config import settings; print(settings.database_url.split("@")[-1])' 2>/dev/null || echo "unknown")"
    warn "underlying error (last line):"
    tail -1 "$DEV_DIR/dbcheck.err" | sed 's/^/    /'
    return 1
  fi
  ok "prerequisites satisfied"
}

# ---------------------------------------------------------------------------
# Backend / frontend / worker / redis
# ---------------------------------------------------------------------------

start_backend() {
  if is_running backend; then warn "backend already running (pid $(read_pid backend))"; return; fi
  log "starting backend on :$BACKEND_PORT"
  ( cd "$ROOT" && exec "$VENV_PY" -m uvicorn api.main:app --host 0.0.0.0 --port "$BACKEND_PORT" ) \
    >>"$DEV_DIR/backend.log" 2>&1 &
  save_pid backend $!
  ok "backend → http://localhost:$BACKEND_PORT  (log: scripts/.dev/backend.log)"
}

start_frontend() {
  if is_running frontend; then warn "frontend already running (pid $(read_pid frontend))"; return; fi
  log "starting frontend on :$FRONTEND_PORT (API $API_URL)"
  ( cd "$WEB" && exec env NEXT_PUBLIC_API_URL="$API_URL" npm run dev -- -p "$FRONTEND_PORT" ) \
    >>"$DEV_DIR/frontend.log" 2>&1 &
  save_pid frontend $!
  ok "frontend → http://localhost:$FRONTEND_PORT  (log: scripts/.dev/frontend.log)"
}

start_worker() {
  if is_running worker; then warn "worker already running (pid $(read_pid worker))"; return; fi
  log "starting Celery worker"
  ( cd "$ROOT" && exec "$VENV_PY" -m celery -A agents.celery_app worker --loglevel=info ) \
    >>"$DEV_DIR/worker.log" 2>&1 &
  save_pid worker $!
  ok "worker running (log: scripts/.dev/worker.log)"
}

ensure_redis() {
  if command -v redis-cli >/dev/null 2>&1 && timeout 2 redis-cli ping >/dev/null 2>&1; then
    return 0
  fi
  if command -v redis-server >/dev/null 2>&1; then
    log "starting Redis"
    redis-server --daemonize yes >/dev/null 2>&1 || true
    sleep 1
    if timeout 2 redis-cli ping >/dev/null 2>&1; then
      ok "redis running on :6379"
    else
      warn "could not start Redis automatically — start it yourself."
    fi
  else
    warn "redis-server not found — backend cache/worker broker will degrade gracefully."
  fi
}

stop_one() {
  local name="$1" p
  p="$(read_pid "$name")"
  if is_running "$name"; then
    log "stopping $name (pid $p)"
    kill "$p" 2>/dev/null || true
    # Give it a moment, then force.
    for _ in 1 2 3; do is_running "$name" || break; sleep 1; done
    is_running "$name" && kill -9 "$p" 2>/dev/null || true
  fi
  rm -f "$(pidfile "$name")"
}

# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

cmd_start() {
  local with_worker=0
  [[ "${1:-}" == "--worker" ]] && with_worker=1
  check_prereqs
  ensure_redis
  start_backend
  start_frontend
  [[ "$with_worker" == "1" ]] && start_worker
  log "all up. Open ${GRN}http://localhost:$FRONTEND_PORT${RST}"
  if [[ "$with_worker" == "0" ]]; then
    log "tip: add --worker to also run the Celery worker (demo works inline without it)"
  fi
}

cmd_stop() {
  stop_one backend
  stop_one frontend
  stop_one worker
  log "stopped."
}

cmd_status() {
  local any=0
  for name in backend frontend worker; do
    if is_running "$name"; then
      ok "$name running (pid $(read_pid "$name"))"; any=1
    else
      warn "$name not running"
    fi
  done
  if command -v redis-cli >/dev/null 2>&1 && timeout 2 redis-cli ping >/dev/null 2>&1; then
    ok "redis running"
  else
    warn "redis not running"
  fi
  [[ "$any" == "1" ]]
}

cmd_restart() {
  cmd_stop
  cmd_start "${1:-}"
}

case "${1:-}" in
  start)   cmd_start "${2:-}" ;;
  stop)    cmd_stop ;;
  restart) cmd_restart "${2:-}" ;;
  status)  cmd_status ;;
  *)
    echo "usage: $0 {start [--worker]|stop|restart [--worker]|status}" >&2
    exit 2
    ;;
esac
