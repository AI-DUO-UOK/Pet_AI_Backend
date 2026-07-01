import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

# Verify API key is loaded
api_key = os.getenv("OPENROUTER_API_KEY")
if not api_key:
    raise ValueError("OPENROUTER_API_KEY not found in .env file")

# Initialize LLM with OpenRouter
llm = ChatOpenAI(
    temperature=0.0,  # Low temperature for more consistent medical advice
    model="mistralai/mistral-large-2512",
    openai_api_key=api_key,
    openai_api_base="https://openrouter.ai/api/v1",
    max_tokens=1000,  # Reduced to fit within available credits
    request_timeout=30,
    streaming=True
)