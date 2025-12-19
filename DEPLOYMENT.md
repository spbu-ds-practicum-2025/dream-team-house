# Deployment Guide

## Quick Deployment

### Prerequisites
The deployment workflow will automatically install:
- Docker
- Docker Compose

### Required GitHub Secrets

Set these in: Repository → Settings → Secrets and variables → Actions → New repository secret

1. **Server Access**:
   - `DEPLOY_HOST` - Server IP address
   - `DEPLOY_USER` - SSH username
   - `DEPLOY_PASS` - SSH password/key

2. **Database Credentials**:
   - `POSTGRES_TEXT_PASSWORD` - Password for text service PostgreSQL databases
   - `POSTGRES_ANALYTICS_PASSWORD` - Password for analytics service PostgreSQL database

3. **Domains** (without https://):
   - `TEXT_SERVICE_A_DOMAIN` - e.g., `text-service-a.vitasha.ru`
   - `TEXT_SERVICE_B_DOMAIN` - e.g., `text-service-b.vitasha.ru`
   - `TEXT_SERVICE_C_DOMAIN` - e.g., `text-service-c.vitasha.ru`
   - `CHAT_SERVICE_DOMAIN` - e.g., `chat-service.vitasha.ru`
   - `ANALYTICS_SERVICE_DOMAIN` - e.g., `analytics-service.vitasha.ru`
   - `FRONTEND_DOMAIN` - e.g., `orv-frontend.vitasha.ru`

4. **OpenAI**:
   - `OPENAI_API_KEY` - Your OpenAI API key

5. **SSL**:
   - `CERTBOT_EMAIL` - Email for Let's Encrypt notifications

### Deploy

**Automatic**: Push to `main` branch triggers deployment

**Manual**: 
1. Go to Actions tab
2. Select "Deploy to Production"
3. Click "Run workflow"

### After Deployment

Application will be available at: `https://${FRONTEND_DOMAIN}`

Example: `https://orv-frontend.vitasha.ru`

## System Configuration

### Default Limits
- **AI Agents**: 2 replicas
- **Edits per Agent**: 1 maximum
- **API Calls per Edit**: 4 (intent, confirm, generate, review)
- **Total OpenAI Requests**: 8 (2 agents × 1 edit × 4 calls)

**Note**: The full protocol from `multi_agent_editor_demo_Version2.py` requires 4 API calls per edit due to the intent-based workflow with multiple phases.

### Services Architecture

```
                    [Traefik HTTPS Proxy]
                            |
        ┌───────────────────┼───────────────────┐
        |                   |                   |
    [Frontend]      [Load Balancer]      [Services]
        |                   |                   |
   Next.js 15      Nginx Round-Robin    Text/Chat/Analytics
```

### SSL Certificates
- Automatic via Let's Encrypt
- HTTP → HTTPS redirect
- Renewal handled by Traefik

### Data Persistence
Volumes (preserved across restarts):
- `postgres-text-a-data`
- `postgres-text-b-data`
- `postgres-text-c-data`
- `postgres-analytics-data`
- `redis-data`
- `letsencrypt`

## Frontend Features

### Pages

1. **Home (`/`)**
   - Create new documents
   - Specify topic and initial text

2. **Document (`/document`)**
   - View current document version
   - Edit history
   - Real-time updates (3s interval)
   - Auto-refresh toggle

3. **Chat (`/chat`)**
   - Agent communication log
   - Intent and comment annotations
   - Real-time updates (2s interval)
   - Up to 1000 messages

4. **Analytics (`/analytics`)**
   - Total edits
   - Token usage
   - Active agents
   - Edits per minute
   - Time-series graphs
   - Period selection (1h/24h/7d)

## Monitoring

### Check Service Status
```bash
ssh ${DEPLOY_USER}@${DEPLOY_HOST}
cd /opt/dream-team-house
docker-compose -f docker-compose.prod.yml ps
```

### View Logs
```bash
# All services
docker-compose -f docker-compose.prod.yml logs -f

# Specific service
docker-compose -f docker-compose.prod.yml logs -f frontend
docker-compose -f docker-compose.prod.yml logs -f ai-agent
docker-compose -f docker-compose.prod.yml logs -f text-service-a
```

### Restart Services
```bash
docker-compose -f docker-compose.prod.yml restart
```

### Stop All
```bash
docker-compose -f docker-compose.prod.yml down
```

### Rebuild and Restart
```bash
docker-compose -f docker-compose.prod.yml up -d --build
```

## Troubleshooting

### SSL Certificate Issues
```bash
# Check Traefik logs
docker-compose -f docker-compose.prod.yml logs traefik

# Verify domain DNS points to server
nslookup ${FRONTEND_DOMAIN}
```

### Database Connection Errors
```bash
# Check PostgreSQL is running
docker-compose -f docker-compose.prod.yml ps postgres-text-a

# View database logs
docker-compose -f docker-compose.prod.yml logs postgres-text-a
```

### Agent Not Working
```bash
# Check OpenAI API key is set
docker-compose -f docker-compose.prod.yml exec ai-agent env | grep OPENAI

# View agent logs
docker-compose -f docker-compose.prod.yml logs ai-agent
```

### Frontend Not Loading
```bash
# Check frontend build
docker-compose -f docker-compose.prod.yml logs frontend

# Check API URLs are correct
docker-compose -f docker-compose.prod.yml exec frontend env | grep NEXT_PUBLIC
```

## Scaling

### Scale AI Agents
```bash
# Increase to 5 agents
docker-compose -f docker-compose.prod.yml up -d --scale ai-agent=5

# Decrease to 1 agent
docker-compose -f docker-compose.prod.yml up -d --scale ai-agent=1
```

### Resource Usage
- Each agent: ~100MB RAM
- Each text-service: ~150MB RAM
- PostgreSQL: ~50MB RAM each
- Redis: ~10MB RAM
- Frontend: ~100MB RAM

**Total minimum**: ~1.5GB RAM recommended

## Security

### Firewall
Only ports 80 and 443 need to be open:
```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### Database Passwords
Passwords are set via GitHub Secrets (`POSTGRES_TEXT_PASSWORD` and `POSTGRES_ANALYTICS_PASSWORD`) and propagated to the server during deployment. The same passwords are used by both the PostgreSQL containers and the application services that connect to them.

### SSL/TLS
- Automatic via Let's Encrypt
- A+ rating on SSL Labs
- HTTP/2 enabled

## Backup

### Database Backup
```bash
# Backup all databases
docker-compose -f docker-compose.prod.yml exec postgres-text-a pg_dump -U textservice textservice > backup_text_a.sql
docker-compose -f docker-compose.prod.yml exec postgres-analytics pg_dump -U analytics analytics > backup_analytics.sql
```

### Volume Backup
```bash
# Backup Docker volumes
docker run --rm -v postgres-text-a-data:/data -v $(pwd):/backup ubuntu tar czf /backup/postgres-text-a-backup.tar.gz -C /data .
```

## Cost Estimation

### OpenAI Usage
- 2 agents × 1 edit × 4 API calls = 8 API calls total
- Each edit requires 4 calls: intent generation, confirmation, final operation, review
- ~500 tokens per API call average
- Total: ~4,000 tokens per session
- Cost: ~$0.01-0.02 per session (GPT-4o-mini)

### Server Requirements
- 2GB RAM minimum
- 20GB disk space
- 1 CPU core minimum

## Support

For issues:
1. Check logs first
2. Verify all secrets are set correctly
3. Ensure domains point to server IP
4. Check firewall rules

## Updates

### Deploy New Version
```bash
git pull origin main
# Triggers automatic deployment workflow
```

### Manual Update on Server
```bash
ssh ${DEPLOY_USER}@${DEPLOY_HOST}
cd /opt/dream-team-house
git pull
docker-compose -f docker-compose.prod.yml up -d --build
```

## Cleanup

### Remove All Data
```bash
docker-compose -f docker-compose.prod.yml down -v
```

### Remove Images
```bash
docker-compose -f docker-compose.prod.yml down --rmi all
```
