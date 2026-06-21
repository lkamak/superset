#!/bin/bash
#
# Cursor hook: blocks docker exec shell commands only.
# MCP tools (execute_sql, etc.) and other shell commands are allowed.
#
# Used by beforeShellExecution and preToolUse (Shell only). Reads hook event
# JSON from stdin and returns:
#   - {"permission":"deny", ...} when access is blocked
#   - {"permission":"allow"}     otherwise

input=$(cat)

deny() {
  jq -n \
    --arg um "Blocked by project hook: docker exec commands are not allowed." \
    --arg am "A Cursor hook denied this command because it uses docker exec. Do not run commands inside containers via docker exec. Use the Superset MCP server or other approved approaches instead." \
    '{permission: "deny", user_message: $um, agent_message: $am}'
  exit 0
}

allow() {
  echo '{ "permission": "allow" }'
  exit 0
}

matches_docker_exec() {
  echo "$1" | grep -Eiq 'docker[[:space:]]+exec\b'
}

tool_name=$(echo "$input" | jq -r '.tool_name // empty')
command=$(echo "$input" | jq -r '.command // .tool_input.command // empty')

# preToolUse: only inspect Shell commands; allow MCP and all other tools.
if [[ -n "$tool_name" ]]; then
  if [[ "$tool_name" != "Shell" ]]; then
    allow
  fi

  if [[ -z "$command" ]]; then
    allow
  fi

  if matches_docker_exec "$command"; then
    deny
  fi

  allow
fi

# beforeShellExecution: inspect the proposed shell command directly.
if [[ -z "$command" ]]; then
  allow
fi

if matches_docker_exec "$command"; then
  deny
fi

allow
