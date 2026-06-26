# Start proxy-in-a-box via Docker (recommended)
# Docs: https://github.com/naiba/proxy-in-a-box

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "Starting proxy-in-a-box on ports 8080 (HTTP), 8081 (HTTPS), 8083 (API)..."
docker run -d --name business-research-proxy `
  -p 8080:8080 -p 8081:8081 -p 8083:8083 `
  -v "${Root}\proxy-pool\data:/app/data" `
  --restart unless-stopped `
  ghcr.io/naiba/proxy-in-a-box:latest

Write-Host "Proxy dashboard: http://127.0.0.1:8083"
Write-Host "Configure app: PROXY_POOL_HTTP=http://127.0.0.1:8080"
