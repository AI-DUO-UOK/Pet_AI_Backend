# Docker Development Environment Setup

This guide shows you how to use Docker as your Python development environment instead of a local virtual environment.

## Your Setup

- ✅ Code stays on your Mac
- ✅ Python + packages run inside Docker
- ✅ Both FastAPI and CLI chatbot work seamlessly
- ✅ No rebuilds needed for code changes
- ✅ No dependency conflicts on your Mac

## Project Structure

```
Pet_AI_Backend/
├── app/                    (FastAPI backend)
├── chatbot/                (CLI chatbot)
├── weights/
├── requirements.txt
├── Dockerfile             ← Provides Python environment
└── .dockerignore
```

## Step 1: Build the Docker Image

Open terminal in your project root and run:

```bash
docker build -t pet-ai-env .
```

**What this does:**
- Creates a Linux container with Python 3.11
- Installs all packages from requirements.txt inside container
- First build takes ~5-10 minutes (torch, transformers, etc. are large)
- Subsequent builds are faster due to Docker layer caching

**Expected output:**
```
Successfully tagged pet-ai-env:latest
```

## Step 2: Run Container with Volume Mount

This is the key step. The `-v` flag mounts your code:

```bash
docker run -it -v $(pwd):/app -p 8000:8000 --name pet-ai pet-ai-env
```

**What this command does:**

| Flag | Purpose |
|------|---------|
| `-it` | Interactive terminal |
| `-v $(pwd):/app` | **Magic:** Mount your Mac code into container at `/app` |
| `-p 8000:8000` | Expose FastAPI port |
| `--name pet-ai` | Give container a friendly name |

**Important:** You're now inside the container. Everything you see is Linux with Python installed.

## Step 3a: Run FastAPI Backend

Inside the container terminal:

```bash
uvicorn app.main:app --host 0.0.0.0 --reload
```

**Output should show:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

**Access from your Mac:**
- Open browser: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`

## Step 3b: Run CLI Chatbot (in separate terminal)

While the first container is running, open a NEW terminal on your Mac:

```bash
# Get the container ID
docker ps

# Enter the running container in a new shell
docker exec -it pet-ai bash
```

Now inside this second terminal:

```bash
python chatbot/main.py
```

Your CLI chatbot runs with all the same packages installed.

## Better Workflow: Using Named Container

**Terminal 1 - Start container:**
```bash
docker run -it -v $(pwd):/app -p 8000:8000 --name pet-ai pet-ai-env
```

Inside this terminal:
```bash
uvicorn app.main:app --host 0.0.0.0 --reload
```

**Terminal 2 - Access running container:**
```bash
docker exec -it pet-ai bash
```

Then run:
```bash
python chatbot/main.py
```

**Terminal 3+ - Can add more terminals as needed:**
```bash
docker exec -it pet-ai bash
```

## Code Changes: No Rebuild Needed ✅

Because of volume mounting (`-v $(pwd):/app`):

- Edit code on Mac
- Changes instantly appear in container
- Just like using a local virtual environment
- No rebuild needed for code changes

Example:
1. Edit `chatbot/main.py` on Mac
2. Restart chatbot in Terminal 2
3. Changes apply instantly (no Docker rebuild)

## When You NEED to Rebuild

Only rebuild image when:

```bash
docker build -t pet-ai-env .
```

In these cases:
- ✅ `requirements.txt` changed
- ✅ `Dockerfile` changed
- ✅ Python version changed
- ❌ Code changed (no rebuild needed)
- ❌ You just want to run the app (no rebuild needed)

## Cleanup & Management

### Stop running container:
```bash
docker stop pet-ai
```

### Remove container:
```bash
docker rm pet-ai
```

### Remove image:
```bash
docker rmi pet-ai-env
```

### See running containers:
```bash
docker ps
```

### See all containers (including stopped):
```bash
docker ps -a
```

## Advantages Over Local Virtual Environment

| Aspect | Local venv | Docker |
|--------|-----------|--------|
| Install on Mac | ✓ (messy) | ✗ (clean) |
| Works first try | Maybe | Yes |
| Dependency conflicts | Possible | No |
| Team consistency | Maybe | Guaranteed |
| Big ML libraries | Slow | Managed |
| PyTorch, OpenCV | Often breaks | Always works |

## Troubleshooting

### Port 8000 already in use:
```bash
# Use different port
docker run -it -v $(pwd):/app -p 8001:8000 pet-ai-env
```
Then access: `http://localhost:8001`

### Container exits immediately:
Make sure you use `-it` flags:
```bash
docker run -it -v $(pwd):/app -p 8000:8000 pet-ai-env
```

### Can't see code changes:
Check volume mount is correct:
```bash
docker exec -it pet-ai ls -la /app
```
Should show your project files.

### Permission denied errors:
Add `--user $(id -u):$(id -g)` to run command (if needed):
```bash
docker run -it --user $(id -u):$(id -g) -v $(pwd):/app -p 8000:8000 pet-ai-env
```

## Quick Reference

```bash
# First time setup
docker build -t pet-ai-env .

# Every development session
docker run -it -v $(pwd):/app -p 8000:8000 --name pet-ai pet-ai-env

# Inside container - FastAPI
uvicorn app.main:app --host 0.0.0.0 --reload

# New terminal - Enter running container
docker exec -it pet-ai bash

# Inside second terminal - CLI chatbot
python chatbot/main.py
```

---

**Remember:** This is basically a "Docker virtual environment" for your Mac. Your code stays on Mac, Python runs in Docker. Best of both worlds! 🚀
