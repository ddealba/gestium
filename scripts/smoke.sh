#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://api:5000}"
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
  local content_type="${5:-application/json}"

  local response
  if [[ -n "$data" ]]; then
    response=$(curl -sS -X "$method" -H "Content-Type: $content_type" ${auth_header:+-H "$auth_header"} -d "$data" "$url" -w "\n%{http_code}")
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
  local password="$2"
  local payload
  payload=$(printf '{"email":"%s","password":"%s"}' "$email" "$password")
  local result
  result=$(request "POST" "$BASE_URL/auth/login" "$payload")
  local status body
  status="${result%%$'\n'*}"
  body="${result#*$'\n'}"
  assert_status 200 "$status" "Login $email"
  echo "$body" | json_get 'data["access_token"]'
}

get_auth_me() {
  local token="$1"
  local result
  result=$(request "GET" "$BASE_URL/auth/me" "" "Authorization: Bearer $token")
  local status body
  status="${result%%$'\n'*}"
  body="${result#*$'\n'}"
  assert_status 200 "$status" "GET /auth/me"
  echo "$body"
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

list_cases() {
  local token="$1"
  local company_id="$2"
  local result
  result=$(request "GET" "$BASE_URL/companies/$company_id/cases" "" "Authorization: Bearer $token")
  local status body
  status="${result%%$'\n'*}"
  body="${result#*$'\n'}"
  assert_status 200 "$status" "GET /companies/$company_id/cases"
  echo "$body"
}

create_case() {
  local token="$1"
  local company_id="$2"
  local payload
  payload=$(printf '{"type":"labor","title":"Smoke case %s"}' "$(date +%s)")
  local result
  result=$(request "POST" "$BASE_URL/companies/$company_id/cases" "$payload" "Authorization: Bearer $token")
  local status body
  status="${result%%$'\n'*}"
  body="${result#*$'\n'}"
  assert_status 201 "$status" "POST /companies/$company_id/cases"
  echo "$body"
}

list_documents() {
  local token="$1"
  local company_id="$2"
  local case_id="$3"
  local result
  result=$(request "GET" "$BASE_URL/companies/$company_id/cases/$case_id/documents" "" "Authorization: Bearer $token")
  local status body
  status="${result%%$'\n'*}"
  body="${result#*$'\n'}"
  assert_status 200 "$status" "GET /companies/$company_id/cases/$case_id/documents"
  echo "$body"
}

health_result=$(request "GET" "$BASE_URL/health")
health_status="${health_result%%$'\n'*}"
assert_status 200 "$health_status" "GET /health"

admin_a_token=$(login "$ADMIN_A_EMAIL" "$ADMIN_A_PASSWORD")
admin_a_me=$(get_auth_me "$admin_a_token")
CLIENT_ID=$(echo "$admin_a_me" | json_get 'data["client_id"]')
ok "Resolved client_id from /auth/me: $CLIENT_ID"

companies_admin_a=$(get_companies "$admin_a_token")

company_names=$(echo "$companies_admin_a" | json_get '[c["name"] for c in data["companies"]]')
if ! echo "$company_names" | grep -q "A1"; then
  fail "AdminA companies missing A1"
fi
if ! echo "$company_names" | grep -q "A2"; then
  fail "AdminA companies missing A2"
fi
ok "AdminA sees A1 and A2"

A1_ID=$(echo "$companies_admin_a" | json_get 'next((c["id"] for c in data["companies"] if c.get("tax_id") == "A1"), data["companies"][0]["id"])')
ok "Using company_id: $A1_ID"

cases_admin_a=$(list_cases "$admin_a_token" "$A1_ID")
case_count=$(echo "$cases_admin_a" | json_get 'len(data.get("cases", []))')
if [[ "$case_count" -gt 0 ]]; then
  CASE_ID=$(echo "$cases_admin_a" | json_get 'data["cases"][0]["id"]')
  ok "Using existing case_id: $CASE_ID"
else
  created_case=$(create_case "$admin_a_token" "$A1_ID")
  CASE_ID=$(echo "$created_case" | json_get 'data["case"]["id"]')
  ok "Created case_id: $CASE_ID"
fi

list_documents "$admin_a_token" "$A1_ID" "$CASE_ID" >/dev/null
ok "Document listing is reachable for discovered company/case"

viewer_a_token=$(login "$VIEWER_A_EMAIL" "$VIEWER_A_PASSWORD")
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

admin_b_token=$(login "$ADMIN_B_EMAIL" "$ADMIN_B_PASSWORD")
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
