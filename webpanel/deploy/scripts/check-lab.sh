#!/usr/bin/env bash
set -euo pipefail

PASS_COUNT=0
FAIL_COUNT=0

pass() {
  PASS_COUNT=$((PASS_COUNT + 1))
  printf '[PASS] %s\n' "$1"
}

fail() {
  FAIL_COUNT=$((FAIL_COUNT + 1))
  printf '[FAIL] %s\n' "$1"
}

check_service() {
  local service="$1"
  if systemctl is-active --quiet "${service}"; then
    pass "${service} is active"
  else
    fail "${service} is not active"
  fi
}

check_curl() {
  local name="$1"
  local url="$2"
  local expected="$3"
  local status
  status="$(curl -fsS -o /tmp/hostpilot-check.out -w '%{http_code}' "${url}" || true)"
  if [ "${status}" = "${expected}" ]; then
    pass "${name} returned HTTP ${expected}"
  else
    fail "${name} returned HTTP ${status:-curl_error}, expected ${expected}"
  fi
}

check_loopback_binding() {
  local name="$1"
  local port="$2"
  if ss -ltn | awk '{print $4}' | grep -qx "127.0.0.1:${port}"; then
    pass "${name} is bound to 127.0.0.1:${port}"
  else
    fail "${name} is not bound to 127.0.0.1:${port}"
  fi
}

main() {
  check_service hostpilot-core.service
  check_service hostpilot-agent.service
  check_service nginx.service
  check_loopback_binding "Core" 8000
  check_loopback_binding "Agent" 8765
  check_curl "Core health" "http://127.0.0.1:8000/health" "200"
  check_curl "Agent health" "http://127.0.0.1:8765/health" "200"
  check_curl "Lab UI" "http://127.0.0.1:8080/" "200"

  printf '\nSummary: %s passed, %s failed\n' "${PASS_COUNT}" "${FAIL_COUNT}"
  if [ "${FAIL_COUNT}" -ne 0 ]; then
    exit 1
  fi
}

main "$@"
