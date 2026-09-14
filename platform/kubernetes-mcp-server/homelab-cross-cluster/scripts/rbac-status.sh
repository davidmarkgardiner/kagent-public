#!/usr/bin/env bash

set -euo pipefail

normalize_can_i_result() {
  local output="$1"
  local exit_status="$2"

  case "${exit_status}:${output}" in
    0:yes) printf 'allow\n' ;;
    1:no) printf 'deny\n' ;;
    *) printf 'error\n' ;;
  esac
}

assert_status() {
  local name="$1"
  local output="$2"
  local exit_status="$3"
  local expected="$4"
  local actual

  actual="$(normalize_can_i_result "${output}" "${exit_status}")"
  [[ "${actual}" == "${expected}" ]] || {
    printf 'rbac-status: self-test failed: %s\n' "${name}" >&2
    return 1
  }
}

self_test() {
  assert_status allow-success yes 0 allow
  assert_status deny-documented no 1 deny
  assert_status command-error '' 2 error
  assert_status malformed-output unexpected 0 error
  printf 'rbac-status: PASS\n'
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  [[ "${1:-}" == "--self-test" ]] || {
    printf 'usage: %s --self-test\n' "${0##*/}" >&2
    exit 2
  }
  self_test
fi
