# Running JevGuard on WSL (Windows Subsystem for Linux)

This guide is specific to JevGuard's docker-compose stack running on WSL2.

---

## Step 1 — Verify Your Docker Setup

Open your **WSL terminal** (Ubuntu/Debian) and run:

```bash
docker --version
docker compose version
```

**If both commands work → skip to Step 2.**

If not, you have two options:

### Option A — Docker Desktop (Recommended, easiest)

1. Download [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/)
2. During install, select **"Use WSL 2 based engine"**
3. After install, open Docker Desktop → **Settings → Resources → WSL Integration**
4. Enable your WSL distro (e.g. Ubuntu)
5. Click **Apply & Restart**
6. Open your WSL terminal — `docker --version` should now work

### Option B — Docker Engine directly in WSL (no Docker Desktop)

```bash
# Install Docker Engine in WSL Ubuntu
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add your user to the docker group (avoids sudo every time)
sudo usermod -aG docker $USER
newgrp docker

# Enable Docker to start automatically
# If your WSL has systemd enabled (WSL 2 with systemd):
sudo systemctl enable --now docker

# If systemd is NOT enabled:
sudo service docker start
```

---

## Step 2 — Clone the Project Into WSL Native Filesystem

> ⚠️ **Critical:** Do NOT clone into `/mnt/c/` (Windows drive).
> File I/O through the Windows bridge is ~10x slower and can cause
> permission errors with Docker volumes.
> Always keep your code in the WSL native filesystem: `/home/yourname/`

```bash
# In WSL terminal — your home directory
cd ~
git clone https://github.com/your-username/jevguard.git
cd jevguard
```

---

## Step 3 — Configure Environment

```bash
cp .env.example .env
```

Open `.env` in your preferred editor:

```bash
nano .env          # or: code .env  (if VS Code WSL extension is installed)
```

The only value you need to fill in for Phase 1–2:

```env
GROQ_API_KEY=your_key_here
```

Get your **free** Groq key at [console.groq.com](https://console.groq.com) — no credit card required.

Leave everything else as-is. The database URLs point to Docker service names
(`postgres`, `redis`, `qdrant`, `ollama`) which resolve automatically inside
the Docker network.

---

## Step 4 — Start All Services

```bash
# From the jevguard/ root directory
docker compose up -d
```

This starts: PostgreSQL · Redis · Qdrant · Ollama · the JevGuard API

First run will pull images (~2–3 GB total). Subsequent starts are instant.

Check everything is running:

```bash
docker compose ps
```

Expected output:
```
NAME              STATUS          PORTS
jevguard-api-1    Up              0.0.0.0:8000->8000/tcp
jevguard-postgres-1  Up (healthy) 0.0.0.0:5432->5432/tcp
jevguard-redis-1  Up (healthy)   0.0.0.0:6379->6379/tcp
jevguard-qdrant-1 Up              0.0.0.0:6333->6333/tcp
jevguard-ollama-1 Up              0.0.0.0:11434->11434/tcp
```

---

## Step 5 — Test the API

WSL2 automatically forwards ports to Windows. Open your **Windows browser**:

```
http://localhost:8000/docs        ← Swagger UI
http://localhost:8000/health      ← dependency health check
```

Or test from your WSL terminal:

```bash
# Health check
curl http://localhost:8000/health | python3 -m json.tool

# Routing decision
curl -X POST http://localhost:8000/api/v1/decisions/route \
  -H "Content-Type: application/json" \
  -H "X-Request-Id: my-first-request" \
  -d '{
    "token_count": 512,
    "has_code": true,
    "has_vision": false,
    "requires_reasoning": false,
    "query_complexity_score": 0.4
  }' | python3 -m json.tool
```

Expected response:
```json
{
  "request_id": "my-first-request",
  "model": "code",
  "confidence": 0.88,
  "reason": "Request contains code content — prefer code-specialized model.",
  "provider": "groq",
  "latency_ms": 312
}
```

---

## Step 6 — Pull Ollama Models (Phase 4 prep)

Ollama runs locally but starts with no models. Pull the free open-source models
that JevGuard's router will use:

```bash
# Small model — simple queries
docker compose exec ollama ollama pull llama3.2:3b

# Code model — programming tasks
docker compose exec ollama ollama pull qwen2.5-coder:7b

# Reasoning model — complex tasks
docker compose exec ollama ollama pull deepseek-r1:7b

# Vision model — image input
docker compose exec ollama ollama pull llava:7b

# Large model — long context
docker compose exec ollama ollama pull llama3.1:8b
```

Each model is 2–7 GB. You can pull them on demand as you build each Phase.

Check what's already pulled:
```bash
docker compose exec ollama ollama list
```

---

## Useful Commands

```bash
# View live logs
docker compose logs -f api

# View logs for a specific service
docker compose logs -f ollama

# Restart just the API (after code changes)
docker compose restart api

# Stop everything
docker compose down

# Stop and delete all data (fresh start)
docker compose down -v

# Open a shell inside the API container
docker compose exec api bash

# Run tests inside the container
docker compose exec api python -m pytest tests/ -v

# Check Ollama is serving models
curl http://localhost:11434/api/tags | python3 -m json.tool
```

---

## Common WSL Issues

### Ports not accessible in Windows browser
WSL2 automatically forwards ports since Windows 10 version 2004.
If it doesn't work:
```powershell
# In Windows PowerShell (as admin) — find the WSL IP
wsl hostname -I
# Then access http://<wsl-ip>:8000 directly
```

### Docker daemon not running after reboot
If using Option B (Docker Engine without Docker Desktop):
```bash
# WSL doesn't always start systemd services on login
sudo service docker start
# Or enable systemd in /etc/wsl.conf:
# [boot]
# systemd=true
```

### Ollama running but no GPU
Without a GPU, Ollama runs on CPU — much slower but fully functional.
For the 3B models this is fine (2–5 seconds per response).
Enable GPU after verifying your setup works without it.

### "permission denied" errors on mounted volumes
```bash
# Fix ownership of the project directory
sudo chown -R $USER:$USER ~/jevguard
```

### WSL running out of memory (Ollama + Docker)
Create or edit `C:\Users\YourName\.wslconfig` in Windows:
```ini
[wsl2]
memory=8GB       # limit WSL memory (adjust to your RAM)
processors=4     # limit CPU cores
swap=4GB
```
Then restart WSL: `wsl --shutdown` in PowerShell, then reopen terminal.

---

## Free Resource Summary

| Service | Cost | Where it runs |
|---------|------|--------------|
| PostgreSQL | Free (Docker) | Your machine |
| Redis | Free (Docker) | Your machine |
| Qdrant | Free (Docker) | Your machine |
| Ollama + models | Free (Docker) | Your machine |
| Groq API | Free (14,400 req/day) | groq.com |
| HuggingFace embeddings | Free (local) | Your machine (Phase 6) |

**Total monthly cost: $0.**
