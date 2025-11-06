# GreenFrog Domain Setup - greenfrog.v4value.ai

## Current Status
- ✅ Hosts entry added: `192.168.50.171 greenfrog.v4value.ai`
- ⚠️ Nginx configuration needs manual insertion
- ✅ Service accessible at: http://192.168.50.171:3000

## Manual Nginx Configuration Required

The nginx configuration file `/home/Davrine/docker/nginx-proxy/nginx.conf` was partially corrupted during automated setup. Follow these steps to complete the configuration:

### Step 1: Fix nginx.conf

```bash
# Remove broken lines (restore to line 1088)
head -n 1088 /home/Davrine/docker/nginx-proxy/nginx.conf > /tmp/nginx.conf.tmp
mv /tmp/nginx.conf.tmp /home/Davrine/docker/nginx-proxy/nginx.conf
```

### Step 2: Add GreenFrog Server Block

Add this configuration **before the final closing brace** of the http block in `/home/Davrine/docker/nginx-proxy/nginx.conf`:

```nginx
    # greenfrog.v4value.ai -> 127.0.0.1:3000 (GreenFrog RAG Avatar)
    server {
        listen 80;
        server_name greenfrog.v4value.ai;

        location / {
            proxy_pass http://127.0.0.1:3000;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection 'upgrade';
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_cache_bypass $http_upgrade;
        }
    }
```

### Step 3: Test and Reload

```bash
# Test configuration
docker exec nginx-proxy nginx -t

# Reload if test passes
docker exec nginx-proxy nginx -s reload
```

### Step 4: Add DNS (Namecheap)

In Namecheap DNS settings for v4value.ai:
- Type: **CNAME**
- Host: **greenfrog**
- Value: **v4value.ai**
- TTL: Automatic

### Step 5: Verify

```bash
# Test local access
curl -I http://greenfrog.v4value.ai

# From Mac (after DNS propagation)
open http://greenfrog.v4value.ai
```

## Alternative: Direct Access

The service is already accessible via:
- **Local:** http://192.168.50.171:3000
- **With hosts entry:** http://greenfrog.v4value.ai (once nginx configured)

## Notes

- Hosts entry already added to NAS `/etc/hosts`
- For Mac access, add to Mac's `/etc/hosts`:
  ```
  192.168.50.171 greenfrog.v4value.ai
  ```
- External access requires DNS CNAME record (Step 4)
