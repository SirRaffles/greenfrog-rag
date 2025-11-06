#!/bin/bash

# Fix Ollama to listen on all network interfaces
# This allows Docker containers to access Ollama

echo "🔧 Fixing Ollama Network Configuration"
echo "======================================="
echo ""

# Check current Ollama listening address
echo "Current Ollama listening address:"
ss -tlnp | grep 11434
echo ""

# Create systemd service override directory
echo "Creating systemd override directory..."
sudo mkdir -p /etc/systemd/system/ollama.service.d/

# Create override configuration to bind to all interfaces
echo "Creating ollama.service override..."
cat << 'EOF' | sudo tee /etc/systemd/system/ollama.service.d/override.conf
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
EOF

echo ""
echo "Override configuration created:"
cat /etc/systemd/system/ollama.service.d/override.conf
echo ""

# Reload systemd daemon
echo "Reloading systemd daemon..."
sudo systemctl daemon-reload

# Restart Ollama service
echo "Restarting Ollama service..."
sudo systemctl restart ollama

# Wait a moment for service to start
sleep 3

# Check new listening address
echo ""
echo "✅ New Ollama listening address:"
ss -tlnp | grep 11434
echo ""

# Test connectivity
echo "Testing Ollama connectivity..."
curl -s http://127.0.0.1:11434/api/tags | jq -r '.models[].name' | head -5
echo ""

# Test from Docker network
echo "Testing from Docker network..."
docker exec greenfrog-anythingllm curl -s http://192.168.50.171:11434/api/tags 2>&1 | head -5
echo ""

echo "✅ Ollama network configuration fixed!"
echo ""
echo "Now you can:"
echo "1. Go back to AnythingLLM UI"
echo "2. Refresh the LLM Preference page"
echo "3. Try changing the Ollama Base URL to: http://192.168.50.171:11434"
echo "4. The dropdown should now populate with models"
echo ""
