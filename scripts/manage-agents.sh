#!/bin/bash
# Agent management script for remote deployment
# Usage: 
#   ./manage-agents.sh start 10    # Start 10 agents
#   ./manage-agents.sh stop         # Stop all agents
#   ./manage-agents.sh restart 5   # Restart with 5 agents
#   ./manage-agents.sh status       # Show running agents

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Agent roles
AGENT_ROLES=(
  "general editor"
  "expert in quantum physics"
  "style corrector"
  "fact checker"
  "grammar expert"
  "technical writer"
  "copyeditor"
  "content strategist"
  "research specialist"
  "documentation expert"
)

# Load environment variables safely
if [ -f "$PROJECT_ROOT/.env" ]; then
  set -a
  source "$PROJECT_ROOT/.env"
  set +a
fi

start_agents() {
  local count=$1

  if [ -z "$count" ]; then
    echo "Error: Please specify number of agents to start"
    exit 1
  fi

  if [ -z "$OPENAI_API_KEY" ]; then
    echo "Error: OPENAI_API_KEY not set"
    exit 1
  fi

  echo "Starting $count AI agents..."

  for i in $(seq 1 "$count"); do
    ROLE_INDEX=$(((i - 1) % ${#AGENT_ROLES[@]}))
    ROLE="${AGENT_ROLES[$ROLE_INDEX]}"
    AGENT_NAME="ai-agent-$i"

    echo "[$i/$count] Starting agent with role: $ROLE"

    # Stop old agent if exists
    docker stop "$AGENT_NAME" 2>/dev/null || true
    docker rm "$AGENT_NAME" 2>/dev/null || true

    # Start new agent
    docker run -d \
      --name="$AGENT_NAME" \
      --restart=unless-stopped \
      --network=dream-team-house_dream-team-network \
      -e AGENT_ID="agent-$i" \
      -e AGENT_ROLE="$ROLE" \
      -e API_TOKEN="${API_TOKEN:-test-token-123}" \
      -e TEXT_SERVICE_URL="http://load-balancer" \
      -e CHAT_SERVICE_URL="http://load-balancer" \
      -e OPENAI_API_KEY="$OPENAI_API_KEY" \
      -e PROXY_API_ENDPOINT="${PROXY_API_ENDPOINT:-https://api.proxyapi.ru/openai/v1}" \
      -e CYCLE_DELAY_MS="${CYCLE_DELAY_MS:-2000}" \
      dream-team-house_ai-agent:latest

    sleep 1
  done

  echo "✅ $count agents started successfully"
}

stop_agents() {
  echo "Stopping all AI agents..."

  # Get list of running agent containers
  AGENTS=$(docker ps --filter "name=ai-agent-" --format "{{.Names}}" | sort)

  if [ -z "$AGENTS" ]; then
    echo "No running agents found"
    return
  fi

  for agent in $AGENTS; do
    echo "Stopping $agent..."
    docker stop "$agent" 2>/dev/null || true
    docker rm "$agent" 2>/dev/null || true
  done

  echo "✅ All agents stopped"
}

restart_agents() {
  local count=$1

  if [ -z "$count" ]; then
    # Count currently running agents
    count=$(docker ps --filter "name=ai-agent-" --format "{{.Names}}" | wc -l)

    if [ "$count" -eq 0 ]; then
      count=5  # Default
    fi
  fi

  echo "Restarting with $count agents..."
  stop_agents
  sleep 2
  start_agents "$count"
}

show_status() {
  echo "AI Agent Status:"
  echo "================"
  
  AGENTS=$(docker ps --filter "name=ai-agent-" --format "table {{.Names}}\t{{.Status}}\t{{.RunningFor}}" | sort)
  
  if [ -z "$AGENTS" ]; then
    echo "No running agents"
  else
    echo "$AGENTS"
    echo ""
    COUNT=$(docker ps --filter "name=ai-agent-" --format "{{.Names}}" | wc -l)
    echo "Total: $COUNT running agents"
  fi
}

case "$1" in
  start)
    start_agents "$2"
    ;;
  stop)
    stop_agents
    ;;
  restart)
    restart_agents "$2"
    ;;
  status)
    show_status
    ;;
  *)
    echo "Usage: $0 {start|stop|restart|status} [count]"
    echo ""
    echo "Commands:"
    echo "  start N    - Start N agents"
    echo "  stop       - Stop all agents"
    echo "  restart [N] - Restart agents (with N agents, or same count)"
    echo "  status     - Show running agents status"
    exit 1
    ;;
esac
