# LangSmith Setup Guide

LangSmith is integrated into this project to enable tracing, debugging, and monitoring of LLM operations. It helps you track all LangChain calls, see detailed logs, and debug issues.

## Quick Setup

### 1. Get Your LangSmith API Key

1. Go to [LangSmith](https://smith.langchain.com/)
2. Sign up or log in to your account
3. Navigate to **Settings** → **API Keys**
4. Create a new API key (or copy an existing one)
5. Copy the API key to clipboard

### 2. Configure Your Project

#### Option A: Using `.env` File (Recommended)

1. Create a `.env` file in the project root:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your LangSmith API key:
   ```
   LANGCHAIN_API_KEY=your_api_key_here
   LANGCHAIN_TRACING_V2=true
   LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
   LANGCHAIN_PROJECT=Pet_AI
   ```

3. **Never commit `.env` file** (it's already in `.gitignore`)

#### Option B: Interactive Prompt

If you don't set `LANGCHAIN_API_KEY` in `.env`, the chatbot will prompt you to enter it when starting:

```bash
python -m chatbot.main
Enter LangSmith API Key (or press Enter to skip):
```

### 3. Start the Application

#### Start the Chatbot with LangSmith Tracing:
```bash
python -m chatbot.main
```

#### Start the FastAPI Backend with LangSmith Tracing:
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Monitoring Your Traces

Once the application is running with LangSmith enabled:

1. Go to [LangSmith](https://smith.langchain.com/)
2. Navigate to your **Pet_AI** project
3. You'll see all LLM operations, tool calls, and memory interactions
4. Each trace shows:
   - Input and output of each operation
   - Token usage
   - Latency
   - Any errors or exceptions

## Disabling LangSmith

If you want to disable tracing (e.g., during development):

### Option 1: Set environment variable to false
```bash
export LANGCHAIN_TRACING_V2=false
python -m chatbot.main
```

### Option 2: Modify `.env` file
```
LANGCHAIN_TRACING_V2=false
```

## Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `LANGCHAIN_API_KEY` | None | Your LangSmith API key |
| `LANGCHAIN_TRACING_V2` | `false` | Enable/disable tracing |
| `LANGCHAIN_ENDPOINT` | `https://api.smith.langchain.com` | LangSmith API endpoint |
| `LANGCHAIN_PROJECT` | `Pet_AI` | Project name for organizing traces |

## File Structure

- `chatbot/langsmith_config.py` - LangSmith configuration module
- `.env.example` - Example environment variables
- `.env` - Your actual environment variables (not committed)

## Troubleshooting

**Problem: "LangSmith tracing disabled - API key not provided"**
- Solution: Add `LANGCHAIN_API_KEY` to your `.env` file or enter it when prompted

**Problem: Traces not appearing in LangSmith**
- Check that `LANGCHAIN_TRACING_V2=true` in your `.env` file
- Verify your `LANGCHAIN_API_KEY` is correct
- Check your LangSmith project name matches the `LANGCHAIN_PROJECT` setting

**Problem: Import Error for dotenv**
- Install: `pip install python-dotenv`

## More Information

- [LangSmith Documentation](https://docs.smith.langchain.com/)
- [LangChain Tracing Guide](https://python.langchain.com/docs/guides/tracing)
