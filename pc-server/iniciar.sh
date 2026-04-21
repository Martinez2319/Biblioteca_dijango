#!/bin/bash
# pc-server/iniciar.sh

cd "$(dirname "$0")"

echo "🚇 Iniciando Cloudflared Tunnel..."
cloudflared tunnel --url http://localhost:3001 > /tmp/cloudflared.log 2>&1 &
CLOUDFLARED_PID=$!

# Esperar a que aparezca la URL
echo "⏳ Esperando URL pública..."
for i in {1..30}; do
  TUNNEL_URL=$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' /tmp/cloudflared.log | head -1)
  if [ -n "$TUNNEL_URL" ]; then
    break
  fi
  sleep 1
done

if [ -z "$TUNNEL_URL" ]; then
  echo "❌ No se pudo obtener URL del tunnel"
  kill $CLOUDFLARED_PID
  exit 1
fi

echo "✅ URL del tunnel: $TUNNEL_URL"
echo ""

# Cleanup al salir
trap "echo '🛑 Deteniendo...'; kill $CLOUDFLARED_PID 2>/dev/null; exit 0" INT TERM

# Iniciar pc-server
TUNNEL_URL="$TUNNEL_URL" npm start