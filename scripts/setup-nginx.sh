#!/bin/bash
#
# Setup nginx reverse proxy for greenfrog.v4value.ai
#

set -e

echo "🐸 Setting up nginx reverse proxy for GreenFrog"
echo "==============================================="
echo ""

# Configuration
DOMAIN="greenfrog.v4value.ai"
NGINX_CONF_DIR="/home/Davrine/docker/nginx-proxy/conf.d"
NGINX_CONF_FILE="$NGINX_CONF_DIR/greenfrog.conf"

# Create nginx configuration
echo "Creating nginx configuration..."
cat > "$NGINX_CONF_FILE" << 'EOF'
server {
    listen 80;
    server_name greenfrog.v4value.ai;

    # Frontend (Next.js)
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Backend API
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Increase timeout for avatar generation
        proxy_read_timeout 300s;
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
    }

    # Health check endpoint
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        proxy_http_version 1.1;
    }

    # AnythingLLM (optional, for admin access)
    location /anythingllm {
        proxy_pass http://127.0.0.1:3001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
    }
}
EOF

echo "✓ nginx configuration created at $NGINX_CONF_FILE"
echo ""

# Add to /etc/hosts (NAS)
echo "Adding $DOMAIN to /etc/hosts..."
if ! grep -q "$DOMAIN" /etc/hosts; then
    echo "127.0.0.1 $DOMAIN" | sudo tee -a /etc/hosts
    echo "✓ Added $DOMAIN to /etc/hosts"
else
    echo "✓ $DOMAIN already in /etc/hosts"
fi
echo ""

# Test nginx configuration
echo "Testing nginx configuration..."
cd /home/Davrine/docker/nginx-proxy
docker exec nginx-proxy nginx -t

if [ $? -eq 0 ]; then
    echo "✓ nginx configuration is valid"
    echo ""

    # Reload nginx
    echo "Reloading nginx..."
    docker exec nginx-proxy nginx -s reload

    if [ $? -eq 0 ]; then
        echo "✓ nginx reloaded successfully"
    else
        echo "✗ Failed to reload nginx"
        exit 1
    fi
else
    echo "✗ nginx configuration has errors"
    exit 1
fi

echo ""
echo "==============================================="
echo "✓ nginx setup complete!"
echo ""
echo "Next steps:"
echo "  1. Test locally: http://greenfrog.v4value.ai"
echo "  2. Add to Mac /etc/hosts: 192.168.50.171 greenfrog.v4value.ai"
echo "  3. Add DNS record on Namecheap:"
echo "     Type: CNAME"
echo "     Host: greenfrog"
echo "     Value: v4value.ai"
echo ""
