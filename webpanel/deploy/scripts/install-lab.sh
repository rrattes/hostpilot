#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="/opt/hostpilot"
APP_DIR="${APP_ROOT}/webpanel"
PYTHON_ROOT="${APP_ROOT}/python"
PYTHON_BIN="${PYTHON_ROOT}/cpython-3.13-linux-x86_64-gnu/bin/python3.13"
HOSTPILOT_USER="hostpilot"
HOSTPILOT_GROUP="hostpilot"
CORE_UNIT="/etc/systemd/system/hostpilot-core.service"
AGENT_UNIT="/etc/systemd/system/hostpilot-agent.service"
NGINX_CONF="/etc/nginx/conf.d/hostpilot-lab.conf"
CORE_ENV="/etc/hostpilot/core.env"
AGENT_ENV="/etc/hostpilot/agent.env"

log() {
  printf '[hostpilot-lab] %s\n' "$1"
}

fail() {
  printf '[hostpilot-lab] ERROR: %s\n' "$1" >&2
  exit 1
}

require_root() {
  if [ "$(id -u)" -ne 0 ]; then
    fail "install-lab.sh must run as root on the Ubuntu lab host."
  fi
}

require_project_root() {
  if [ ! -f "backend/requirements.txt" ] || [ ! -f "frontend/package.json" ] || [ ! -f "agent/requirements.txt" ]; then
    fail "Run this script from the webpanel/ project root."
  fi
}

require_ubuntu_lab() {
  if [ ! -r /etc/os-release ]; then
    fail "/etc/os-release not found."
  fi
  . /etc/os-release
  if [ "${ID:-}" != "ubuntu" ] || [ "${VERSION_ID:-}" != "26.04" ]; then
    fail "This lab installer targets Ubuntu 26.04 only. Found ${PRETTY_NAME:-unknown}."
  fi
}

install_packages() {
  log "Installing required Ubuntu packages."
  export DEBIAN_FRONTEND=noninteractive
  apt-get update
  apt-get install -y python3 python3-venv python3-pip nodejs npm nginx git curl

  if ! command -v uv >/dev/null 2>&1; then
    log "Installing uv to /usr/local/bin."
    curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/usr/local/bin sh
  fi
}

ensure_runtime_user() {
  if ! id "${HOSTPILOT_USER}" >/dev/null 2>&1; then
    log "Creating runtime user ${HOSTPILOT_USER}."
    useradd --system --create-home --home-dir /var/lib/hostpilot --shell /usr/sbin/nologin "${HOSTPILOT_USER}"
  fi
  mkdir -p "${APP_ROOT}" /etc/hostpilot /var/lib/hostpilot
  chmod 750 /etc/hostpilot
}

ensure_python_runtime() {
  if [ ! -x "${PYTHON_BIN}" ]; then
    log "Installing isolated Python 3.13 runtime under ${PYTHON_ROOT}."
    mkdir -p "${PYTHON_ROOT}"
    UV_PYTHON_INSTALL_DIR="${PYTHON_ROOT}" uv python install 3.13
  fi
}

preserve_runtime_state() {
  local state_dir="$1"
  mkdir -p "${state_dir}"
  if [ -f "${APP_DIR}/backend/hostpilot.db" ]; then
    cp "${APP_DIR}/backend/hostpilot.db" "${state_dir}/hostpilot.db"
  fi
}

restore_runtime_state() {
  local state_dir="$1"
  if [ -f "${state_dir}/hostpilot.db" ]; then
    mkdir -p "${APP_DIR}/backend"
    cp "${state_dir}/hostpilot.db" "${APP_DIR}/backend/hostpilot.db"
  fi
}

deploy_app() {
  local source_dir
  local state_dir
  source_dir="$(pwd -P)"
  state_dir="$(mktemp -d)"

  if [ "${source_dir}" = "${APP_DIR}" ]; then
    log "Source is already ${APP_DIR}; skipping file copy."
    rm -rf "${state_dir}"
    return
  fi

  log "Deploying current webpanel/ tree to ${APP_DIR}."
  preserve_runtime_state "${state_dir}"
  systemctl stop hostpilot-core.service hostpilot-agent.service 2>/dev/null || true

  mkdir -p "${APP_DIR}"
  find "${APP_DIR}" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
  tar \
    --exclude='./backend/.venv' \
    --exclude='./agent/.venv' \
    --exclude='./frontend/node_modules' \
    --exclude='./frontend/dist' \
    --exclude='./backend/hostpilot.db' \
    --exclude='./.dev' \
    -C "${source_dir}" -cf - . | tar -C "${APP_DIR}" -xf -
  restore_runtime_state "${state_dir}"
  rm -rf "${state_dir}"
}

ensure_env_files() {
  log "Ensuring lab environment files outside git."
  if [ ! -f "${CORE_ENV}" ]; then
    local secret
    secret="$("${PYTHON_BIN}" -c 'import secrets; print(secrets.token_urlsafe(48))')"
    cat > "${CORE_ENV}" <<EOF
HOSTPILOT_SECRET_KEY=${secret}
HOSTPILOT_ACCESS_TOKEN_MINUTES=60
HOSTPILOT_AGENT_TIMEOUT_SECONDS=2
EOF
  fi
  touch "${AGENT_ENV}"
  chmod 600 "${CORE_ENV}" "${AGENT_ENV}"
}

build_backend() {
  log "Creating backend venv, installing dependencies, and running migrations."
  cd "${APP_DIR}/backend"
  rm -rf .venv
  "${PYTHON_BIN}" -m venv .venv
  . .venv/bin/activate
  pip install --upgrade pip
  pip install -r requirements.txt
  alembic upgrade head
  deactivate
}

build_agent() {
  log "Creating agent venv and installing dependencies."
  cd "${APP_DIR}/agent"
  rm -rf .venv
  "${PYTHON_BIN}" -m venv .venv
  . .venv/bin/activate
  pip install --upgrade pip
  pip install -r requirements.txt
  deactivate
}

build_frontend() {
  log "Installing frontend dependencies and building production assets."
  cd "${APP_DIR}/frontend"
  rm -rf node_modules dist
  npm ci
  npm run build
}

install_hostpilot_templates() {
  log "Installing HostPilot-only systemd and Nginx templates."
  install -m 0644 "${APP_DIR}/deploy/systemd/hostpilot-core.service" "${CORE_UNIT}"
  install -m 0644 "${APP_DIR}/deploy/systemd/hostpilot-agent.service" "${AGENT_UNIT}"
  install -m 0644 "${APP_DIR}/deploy/nginx/hostpilot-lab.conf" "${NGINX_CONF}"

  if grep -R "127.0.0.1:8000" "${NGINX_CONF}" >/dev/null && grep -R "listen 8080" "${NGINX_CONF}" >/dev/null; then
    log "Nginx lab config safety check passed."
  else
    fail "Nginx lab config does not match expected HostPilot lab bindings."
  fi
}

start_services() {
  log "Starting HostPilot services."
  chown -R "${HOSTPILOT_USER}:${HOSTPILOT_GROUP}" "${APP_ROOT}" /var/lib/hostpilot
  systemctl daemon-reload
  nginx -t
  systemctl enable --now nginx.service
  systemctl enable --now hostpilot-agent.service
  systemctl enable --now hostpilot-core.service
  systemctl restart hostpilot-agent.service hostpilot-core.service
  systemctl reload nginx.service
}

print_summary() {
  log "Install complete."
  printf '\nHealth checks:\n'
  printf '  Agent:    http://127.0.0.1:8765/health\n'
  printf '  Core:     http://127.0.0.1:8000/health\n'
  printf '  UI local: http://127.0.0.1:8080/\n'
  printf '  UI LAN:   http://<lab-host>:8080/\n\n'
  printf 'Run: %s/deploy/scripts/check-lab.sh\n' "${APP_DIR}"
}

main() {
  require_root
  require_project_root
  require_ubuntu_lab
  install_packages
  ensure_runtime_user
  ensure_python_runtime
  deploy_app
  ensure_env_files
  build_backend
  build_agent
  build_frontend
  install_hostpilot_templates
  start_services
  print_summary
}

main "$@"
