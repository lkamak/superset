#!/bin/bash
#
# Cursor beforeShellExecution hook: blocks docker exec commands.

input=$(cat)
command=$(echo "$input" | jq -r '.command // empty')

deny() {
  jq -n \
    --arg um "Blocked by project hook: docker exec commands are not allowed." \
    --arg am "A Cursor hook denied this command because it uses docker exec. Do not run commands inside containers via docker exec. Use other approved approaches instead." \
    '{permission: "deny", user_message: $um, agent_message: $am}'
  exit 0
}

if [[ -z "$command" ]]; then
  echo '{ "permission": "allow" }'
  exit 0
fi

if echo "$command" | grep -Eiq 'docker[[:space:]]+exec\b'; then
  deny
fi

echo '{ "permission": "allow" }'
exit 0
