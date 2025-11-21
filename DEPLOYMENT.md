# Deployment Guide - AI Agent System

## Overview

This document describes the deployment process for the AI Agent system of the Dream Team House distributed document editing platform.

## Architecture

The system consists of:
- **3 Text Service nodes** (Moscow, Saint Petersburg, Novosibirsk) - distributed document storage with replication
- **Chat Service** - agent coordination via Redis Streams
- **Analytics Service** - metrics and telemetry collection
- **Load Balancer** (Nginx) - distributes requests across Text Service nodes
- **AI Agents** (5-50) - autonomous agents that edit documents using OpenAI API

## Deployment Methods

### 1. Automatic Deployment via GitHub Actions

Deployment happens automatically when code is pushed to `main` branch.

**Workflow file**: `.github/workflows/deploy-ai-agent.yml`

**Triggers**:
- Push to `main` branch (paths: `services/ai-agent/**`, `services/text-service/**`, `services/chat-service/**`)
- Manual workflow dispatch (can specify number of agents)

**Process**:
1. Packages entire repository into tar archive
2. Copies to remote server via SCP
3. Extracts and builds Docker images
4. Starts infrastructure (PostgreSQL, Redis)
5. Starts backend services (Text Service x3, Chat Service, Analytics Service)
6. Starts Load Balancer
7. Starts N AI agents with different roles

### 2. Manual Script-based Management

Use the `scripts/manage-agents.sh` script for manual control:

```bash
# Start 10 agents
./scripts/manage-agents.sh start 10

# Stop all agents
./scripts/manage-agents.sh stop

# Restart with 5 agents
./scripts/manage-agents.sh restart 5

# Check status
./scripts/manage-agents.sh status
```

## Required GitHub Secrets

Add these secrets in repository Settings → Secrets and variables → Actions:

### 1. OPENAI_API_KEY ✅ (Already added)
- **Description**: API key for OpenAI via ProxyAPI
- **Source**: https://api.proxyapi.ru/
- **Used by**: AI agents to generate document edits
- **Format**: String

### 2. API_TOKEN
- **Description**: Authentication token for agents to access services
- **Recommendation**: Generate a strong random string (e.g., `openssl rand -hex 32`)
- **Used by**: AI agents for Bearer authentication with Text Service and Chat Service
- **Format**: String
- **Example**: `a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6`

### 3. DEPLOY_HOST
- **Description**: SSH hostname or IP address of deployment server
- **Used by**: GitHub Actions to connect to remote server
- **Format**: Hostname or IP
- **Example**: `example.com` or `192.168.1.100`

### 4. DEPLOY_USER
- **Description**: SSH username for deployment
- **Used by**: GitHub Actions SSH authentication
- **Format**: String
- **Example**: `deploy` or `ubuntu`

### 5. DEPLOY_PASS
- **Description**: SSH password for deployment
- **Security Note**: Consider using SSH keys instead for production
- **Used by**: GitHub Actions SSH authentication
- **Format**: String

## Agent Configuration

### Agent Roles

The system automatically assigns these roles to agents in rotation:

1. general editor
2. expert in quantum physics
3. style corrector
4. fact checker
5. grammar expert
6. technical writer
7. copyeditor
8. content strategist
9. research specialist
10. documentation expert

### Agent Count by Stage

According to TR.md:

- **MVP (Stage 1)**: 5-10 agents
- **Extended Testing (Stage 2)**: up to 50 agents
- **Final Stress Test (Stage 3)**: 50 agents

### Environment Variables

Each agent receives:

```bash
AGENT_ID=agent-1                    # Unique identifier
AGENT_ROLE="general editor"         # Role/specialization
API_TOKEN=<from-github-secret>      # Auth token
TEXT_SERVICE_URL=http://load-balancer
CHAT_SERVICE_URL=http://load-balancer
OPENAI_API_KEY=<from-github-secret>
PROXY_API_ENDPOINT=https://api.proxyapi.ru/openai/v1
CYCLE_DELAY_MS=2000                 # 2 seconds between cycles
```

## ProxyAPI Configuration

**Important**: The system uses ProxyAPI instead of direct OpenAI API.

- **Endpoint**: `https://api.proxyapi.ru/openai/v1`
- **Reason**: As specified in TODO.md - "у нас не напрямую в OpenAI"
- **Configuration**: Hardcoded in deployment scripts, customizable via `PROXY_API_ENDPOINT`

## Deployment Process Details

### Infrastructure Startup Sequence

1. **Databases** (wait 10s for initialization)
   - postgres-text-a, postgres-text-b, postgres-text-c
   - postgres-analytics
   - redis

2. **Backend Services** (wait 10s for startup)
   - text-service-a, text-service-b, text-service-c
   - chat-service
   - analytics-service

3. **Load Balancer**
   - Nginx with health checks
   - Round-robin distribution

4. **AI Agents**
   - Started one by one with 2s delay
   - Each gets unique ID and role
   - Restart policy: unless-stopped

### Network Configuration

All services run on Docker network: `dream-team-house_dream-team-network`

## Monitoring

### View Agent Logs

```bash
# All agents (on deployment server)
docker logs -f ai-agent-1
docker logs -f ai-agent-2

# Or using docker-compose (local dev)
docker-compose logs -f ai-agent
```

### Check Running Agents

```bash
# On deployment server
docker ps | grep ai-agent

# Or use management script
./scripts/manage-agents.sh status
```

### Agent Log Format

```
[agent-1] Fetching current document...
[agent-1] Document version: 42
[agent-1] Reading chat messages...
[agent-1] Found 3 new messages
[agent-1] Generating edit proposal...
[agent-1] Generated edit (245 tokens used)
[agent-1] Submitting edit...
[agent-1] Edit accepted: edit-uuid-123
[agent-1] Posting to chat...
```

## Troubleshooting

### Agents Not Starting

1. Check secrets are configured:
   ```bash
   # In GitHub repo: Settings → Secrets and variables → Actions
   ```

2. Check SSH connectivity:
   ```bash
   ssh DEPLOY_USER@DEPLOY_HOST
   ```

3. Check logs in GitHub Actions

### Agents Stopping Immediately

1. **Budget Exceeded**: Check if 429 errors in logs
   - Solution: Increase token budget or restart with new budget

2. **Service Unavailable**: Check if backend services are running
   ```bash
   docker ps | grep -E "(text-service|chat-service|load-balancer)"
   ```

3. **Invalid API Key**: Check OPENAI_API_KEY is correct
   ```bash
   # Logs will show: "Error in agent cycle"
   ```

### Network Issues

Check Docker network exists:
```bash
docker network ls | grep dream-team
```

If missing, recreate:
```bash
docker network create dream-team-house_dream-team-network
```

## Security Considerations

1. **API Keys**: Never commit to repository, use GitHub Secrets
2. **SSH Credentials**: Consider using SSH keys instead of passwords for production
3. **Token Budget**: Monitor to prevent excessive API costs
4. **Rate Limiting**: Agents implement 10 requests/minute per TR.md requirements
5. **Network Isolation**: All services on private Docker network

## Cost Management

According to TR.md:
- **Token Budget**: 15,000,000 tokens (~15,000 rubles)
- **Test Budget**: 500 rubles for CI/CD tests
- **Final Test Budget**: 10,000 rubles

Agents automatically stop when receiving 429 (budget exceeded) response.

## Production Checklist

- [ ] All GitHub Secrets configured
- [ ] Deployment server accessible via SSH
- [ ] Docker and Docker Compose installed on server
- [ ] Firewall configured (port 80 for Load Balancer)
- [ ] Token budget set appropriately
- [ ] Monitoring/logging configured
- [ ] Backup strategy for databases

## Support

For issues or questions:
1. Check deployment logs in GitHub Actions
2. Check agent logs: `docker logs ai-agent-N`
3. Review TR.md for requirements
4. Check this deployment guide

## Additional Resources

- **TR.md**: Technical requirements and architecture
- **TODO.md**: Implementation checklist
- **services/ai-agent/README.md**: Agent service documentation
- **.env.example**: Environment variable reference
