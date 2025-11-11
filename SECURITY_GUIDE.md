# GreenFrog RAG - Security Guide

## 🔴 IMMEDIATE ACTION REQUIRED

### Exposed Credentials Detected

The following credential file was found in the repository:
- `ANYTHINGLLM_CREDENTIALS.txt` - Contains AnythingLLM API key

**Status:** ⚠️ Now added to .gitignore, but still exists in git history

---

## Step 1: Rotate Compromised Credentials

### AnythingLLM API Key Rotation

1. **Access AnythingLLM Admin Panel:**
   ```bash
   # On NAS or local machine
   http://localhost:3001
   # or
   http://192.168.50.171:3001
   ```

2. **Generate New API Key:**
   - Navigate to: Settings → API Keys
   - Delete the old key: `sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA`
   - Generate a new API key
   - Copy the new key

3. **Update Environment Variables:**
   ```bash
   # Edit .env file (never commit this!)
   nano .env

   # Update the line:
   ANYTHINGLLM_API_KEY=sk-YOUR_NEW_API_KEY_HERE
   ```

4. **Restart Services:**
   ```bash
   docker-compose down
   docker-compose up -d
   ```

---

## Step 2: Remove Credentials from Git History

⚠️ **WARNING:** This rewrites git history. Coordinate with team before running.

```bash
# Navigate to repository
cd /home/user/greenfrog-rag

# Remove file from all commits
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch ANYTHINGLLM_CREDENTIALS.txt" \
  --prune-empty --tag-name-filter cat -- --all

# Remove backup refs
rm -rf .git/refs/original/

# Force garbage collection
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# Force push to remote (requires coordination!)
git push origin --force --all
git push origin --force --tags
```

**Alternative (if force push not allowed):**
Create a new repository and migrate:
```bash
# Clone without history
git clone --depth 1 https://github.com/YOUR_REPO.git greenfrog-clean
cd greenfrog-clean

# Ensure .gitignore is correct
cat .gitignore | grep CREDENTIALS

# Push to new repository
git remote set-url origin https://github.com/YOUR_NEW_REPO.git
git push -u origin main
```

---

## Step 3: Prevent Future Credential Leaks

### Use `.env` for All Secrets

```bash
# Create .env from example (never commit .env!)
cp .env.example .env

# Edit with your actual credentials
nano .env
```

### Example `.env` structure:
```env
# AnythingLLM
ANYTHINGLLM_API_KEY=sk-YOUR_ACTUAL_KEY_HERE
ANYTHINGLLM_URL=http://anythingllm:3001

# Ollama
OLLAMA_BASE_URL=http://host.docker.internal:11434

# Redis
REDIS_URL=redis://greenfrog-redis:6379

# ChromaDB
CHROMADB_URL=http://chromadb:8000

# Backend
CORS_ORIGINS=http://localhost:3000
SECRET_KEY=GENERATE_RANDOM_SECRET_KEY_HERE

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Install Pre-commit Hook (Optional)

```bash
# Install git-secrets to scan for credentials
brew install git-secrets  # macOS
# or
sudo apt-get install git-secrets  # Linux

# Set up hooks
cd /home/user/greenfrog-rag
git secrets --install
git secrets --register-aws  # Prevents AWS keys
git secrets --add 'sk-[a-zA-Z0-9]{40,}'  # Prevents API keys
```

---

## Step 4: Implement API Authentication

### Add API Key Middleware (See Implementation Below)

The system currently has **no authentication** on API endpoints. This allows anyone to query your RAG system.

**File: `/backend/app/middleware/auth.py`** (to be created)

```python
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
import os

API_KEY = os.getenv("API_KEY", "")

async def api_key_middleware(request: Request, call_next):
    """Validate API key for protected endpoints."""

    # Skip auth for health checks
    if request.url.path in ["/health", "/", "/docs", "/openapi.json"]:
        return await call_next(request)

    # Check for API key
    api_key = request.headers.get("X-API-Key")

    if not api_key or api_key != API_KEY:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Invalid or missing API key"}
        )

    return await call_next(request)
```

### Enable in `main.py`:
```python
from app.middleware.auth import api_key_middleware

app = FastAPI()

# Add middleware
app.middleware("http")(api_key_middleware)
```

### Add to `.env`:
```env
API_KEY=your-secure-random-api-key-here
```

Generate secure API key:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## Step 5: Restrict CORS

### Current Configuration (Insecure):
```yaml
# docker-compose.yml
CORS_ORIGINS=http://localhost:3000,http://192.168.50.171:3000,http://greenfrog.v4value.ai
```

### Recommended Configuration:
```yaml
# docker-compose.yml
CORS_ORIGINS=${FRONTEND_URL:-http://localhost:3000}
```

Then in `.env`:
```env
FRONTEND_URL=http://localhost:3000
```

For production:
```env
FRONTEND_URL=https://greenfrog.yourdomain.com
```

---

## Step 6: Enable HTTPS (Production)

### Using Let's Encrypt with nginx

1. **Install certbot:**
   ```bash
   sudo apt-get update
   sudo apt-get install certbot python3-certbot-nginx
   ```

2. **Configure nginx reverse proxy:**
   ```nginx
   # /etc/nginx/sites-available/greenfrog
   server {
       listen 80;
       server_name greenfrog.yourdomain.com;

       location / {
           proxy_pass http://localhost:3000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }

       location /api {
           proxy_pass http://localhost:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

3. **Obtain certificate:**
   ```bash
   sudo certbot --nginx -d greenfrog.yourdomain.com
   ```

4. **Auto-renewal:**
   ```bash
   sudo certbot renew --dry-run
   ```

---

## Step 7: Security Checklist

### Before Production Deployment:

- [ ] All credentials rotated
- [ ] No credentials in git history
- [ ] `.env` file never committed
- [ ] API key authentication enabled
- [ ] CORS restricted to frontend domain
- [ ] HTTPS enabled with valid certificate
- [ ] Rate limiting configured
- [ ] Firewall rules configured (allow only 80/443)
- [ ] Docker containers run as non-root users
- [ ] Regular security updates scheduled
- [ ] Backup encryption enabled
- [ ] Access logs monitored
- [ ] Intrusion detection configured

### Monitoring & Alerts:

- [ ] Set up log monitoring (e.g., Grafana, ELK)
- [ ] Configure alerts for failed auth attempts
- [ ] Monitor unusual API usage patterns
- [ ] Track response times and errors
- [ ] Set up health check monitoring

---

## Step 8: Incident Response Plan

### If Credentials Are Compromised:

1. **Immediate Actions** (within 5 minutes):
   - Rotate all API keys
   - Change database passwords
   - Restart all services
   - Review access logs

2. **Short-term Actions** (within 1 hour):
   - Audit all recent API calls
   - Check for data exfiltration
   - Notify relevant stakeholders
   - Document the incident

3. **Long-term Actions** (within 1 week):
   - Review and update security policies
   - Implement additional monitoring
   - Conduct security training
   - Perform security audit

### Emergency Contacts:

```
Security Team: security@yourdomain.com
On-call Admin: +1-XXX-XXX-XXXX
Backup Admin: +1-XXX-XXX-XXXX
```

---

## Additional Security Recommendations

### 1. Regular Security Audits

```bash
# Run security scan (monthly)
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image greenfrog-backend:latest

# Check for outdated dependencies
pip list --outdated
npm audit
```

### 2. Principle of Least Privilege

- Run Docker containers as non-root
- Use read-only file systems where possible
- Limit network access between containers
- Use secrets management (Docker secrets, Vault)

### 3. Data Protection

- Encrypt data at rest (enable disk encryption)
- Encrypt data in transit (HTTPS, TLS for inter-service)
- Implement data retention policies
- Regular automated backups
- Test backup restoration

### 4. Network Security

```bash
# Configure firewall (ufw example)
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp   # SSH (restrict to specific IPs)
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable

# Restrict SSH to specific IPs
sudo ufw delete allow 22/tcp
sudo ufw allow from YOUR_IP_ADDRESS to any port 22
```

### 5. Container Security

```dockerfile
# Use non-root user in Dockerfile
FROM python:3.11-slim
RUN useradd -m -u 1000 appuser
USER appuser

# Read-only filesystem
docker run --read-only --tmpfs /tmp greenfrog-backend
```

---

## Questions or Concerns?

For security-related issues, please:
1. **Do NOT** create public GitHub issues
2. Email: security@yourdomain.com
3. Use encrypted communication if possible (PGP key available)

---

**Last Updated:** 2025-11-11
**Next Review:** 2025-12-11
**Document Owner:** DevOps/Security Team
