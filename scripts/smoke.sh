#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://api:5000}"
CLIENT_A_ID="${CLIENT_A_ID:-1a8b9d30-7c7c-4c05-9e1c-2c7a7a96c1a1}"
CLIENT_B_ID="${CLIENT_B_ID:-2b9c0e41-8d8d-4d16-af2d-3d8b8bb7d2b2}"
ADMIN_A_EMAIL="${ADMIN_A_EMAIL:-adminA@test.com}"
ADMIN_A_PASSWORD="${ADMIN_A_PASSWORD:-Passw0rd!}"
VIEWER_A_EMAIL="${VIEWER_A_EMAIL:-viewerA@test.com}"
VIEWER_A_PASSWORD="${VIEWER_A_PASSWORD:-Passw0rd!}"
ADMIN_B_EMAIL="${ADMIN_B_EMAIL:-adminB@test.com}"
ADMIN_B_PASSWORD="${ADMIN_B_PASSWORD:-Passw0rd!}"

ok() {
  echo "OK: $*"
}

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

request() {
  local method="$1"
  local url="$2"
  local data="${3:-}"
  local auth_header="${4:-}"

  local response
  if [[ -n "$data" ]]; then
    response=$(curl -sS -X "$method" -H "Content-Type: application/json" ${auth_header:+-H "$auth_header"} -d "$data" "$url" -w "\n%{http_code}")
  else
    response=$(curl -sS -X "$method" ${auth_header:+-H "$auth_header"} "$url" -w "\n%{http_code}")
  fi

  local body
  local status
  body="${response%$'\n'*}"
  status="${response##*$'\n'}"

  printf '%s\n%s' "$status" "$body"
}

assert_status() {
  local expected="$1"
  local actual="$2"
  local message="$3"
  if [[ "$expected" != "$actual" ]]; then
    fail "$message (expected $expected, got $actual)"
  fi
  ok "$message"
}

json_get() {
  local expr="$1"
  python - <<PY
import json
import sys

data = json.load(sys.stdin)
print($expr)
PY
}

login() {
  local email="$1"
  local client_id="$2"
  local password="$3"
  local payload
  payload=$(printf '{"email":"%s","password":"%s","client_id":"%s"}' "$email" "$password" "$client_id")
  local result
  result=$(request "POST" "$BASE_URL/auth/login" "$payload")
  local status body
  status="${result%%$'\n'*}"
  body="${result#*$'\n'}"
  assert_status 200 "$status" "Login $email"
  echo "$body" | json_get 'data["access_token"]'
}

get_companies() {
  local token="$1"
  local result
  result=$(request "GET" "$BASE_URL/companies" "" "Authorization: Bearer $token")
  local status body
  status="${result%%$'\n'*}"
  body="${result#*$'\n'}"
  assert_status 200 "$status" "GET /companies"
  echo "$body"
}

health_result=$(request "GET" "$BASE_URL/health")
health_status="${health_result%%$'\n'*}"
assert_status 200 "$health_status" "GET /health"

admin_a_token=$(login "$ADMIN_A_EMAIL" "$CLIENT_A_ID" "$ADMIN_A_PASSWORD")
companies_admin_a=$(get_companies "$admin_a_token")

company_names=$(echo "$companies_admin_a" | json_get '[c["name"] for c in data["companies"]]')
if ! echo "$company_names" | grep -q "A1"; then
  fail "AdminA companies missing A1"
fi
if ! echo "$company_names" | grep -q "A2"; then
  fail "AdminA companies missing A2"
fi
ok "AdminA sees A1 and A2"

A1_ID=$(echo "$companies_admin_a" | json_get 'next(c["id"] for c in data["companies"] if c["tax_id"] == "A1" or c["name"] == "A1")')

viewer_a_token=$(login "$VIEWER_A_EMAIL" "$CLIENT_A_ID" "$VIEWER_A_PASSWORD")
companies_viewer_a=$(get_companies "$viewer_a_token")

viewer_only_a1=$(echo "$companies_viewer_a" | python - <<'PY'
import json
import sys

data = json.load(sys.stdin)
names = [company["name"] for company in data.get("companies", [])]
print("true" if names == ["A1"] else "false")
PY
)
if [[ "$viewer_only_a1" != "true" ]]; then
  viewer_names=$(echo "$companies_viewer_a" | json_get '[c["name"] for c in data["companies"]]')
  fail "ViewerA should see only A1 (got $viewer_names)"
fi
ok "ViewerA sees only A1"

admin_b_token=$(login "$ADMIN_B_EMAIL" "$CLIENT_B_ID" "$ADMIN_B_PASSWORD")
company_a1_result=$(request "GET" "$BASE_URL/companies/$A1_ID" "" "Authorization: Bearer $admin_b_token")
company_a1_status="${company_a1_result%%$'\n'*}"
if [[ "$company_a1_status" != "404" ]]; then
  fail "AdminB access to A1 should be 404 (got $company_a1_status)"
fi
ok "AdminB cannot access A1"

employee_payload='{"full_name":"Smoke Employee","start_date":"2024-01-01","status":"active"}'
viewer_employee_result=$(request "POST" "$BASE_URL/companies/$A1_ID/employees" "$employee_payload" "Authorization: Bearer $viewer_a_token")
viewer_employee_status="${viewer_employee_result%%$'\n'*}"
if [[ "$viewer_employee_status" != "403" && "$viewer_employee_status" != "404" ]]; then
  fail "ViewerA employee create should be 403/404 (got $viewer_employee_status)"
fi
ok "ViewerA cannot create employee"

admin_employee_result=$(request "POST" "$BASE_URL/companies/$A1_ID/employees" "$employee_payload" "Authorization: Bearer $admin_a_token")
admin_employee_status="${admin_employee_result%%$'\n'*}"
assert_status 201 "$admin_employee_status" "AdminA creates employee"

ok "Smoke checks completed"
