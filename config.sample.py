"""
GitMind — Central Configuration

Loads environment variables and provides factory functions for
LLM models, embedding models, and project-wide settings.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env
# Search for .env in project root, then in tests/ (dev fallback)
_project_root = Path(__file__).resolve().parent
_env_paths = [
    _project_root / ".env",
    _project_root / "tests" / ".env",
]

for _env_path in _env_paths:
    if _env_path.exists():
        load_dotenv(_env_path)
        break

# Note: Tests have been performed with Gemini. Hence, cannot guarantee the working of the code with OpenAI LLM provider.

LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gemini").lower()
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "enter your api key")
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "enter your api key")
GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "enter your token") #go to https://github.com/settings/tokens and generate a token (generate a classic token - with permissions like read org and repo)

GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash") # default models - switch as per your need
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

EMBEDDING_PROVIDER: str = os.getenv("EMBEDDING_PROVIDER", LLM_PROVIDER).lower()

# Data directories
GITMIND_HOME = Path.home() / ".gitmind"
GITMIND_HOME.mkdir(parents=True, exist_ok=True)

DB_PATH = GITMIND_HOME / "gitmind.db"
CHROMA_PATH = GITMIND_HOME / "chroma"


def get_llm(temperature: float = 0, streaming: bool = False):
    """
    Factory: returns a LangChain ChatModel based on LLM_PROVIDER.

    Supports:
        - "gemini"  → ChatGoogleGenerativeAI
        - "openai"  → ChatOpenAI
    """
    if LLM_PROVIDER == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=GEMINI_MODEL,
            google_api_key=GEMINI_API_KEY,
            temperature=temperature,
            streaming=streaming,
        )

    elif LLM_PROVIDER == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=OPENAI_MODEL,
            api_key=OPENAI_API_KEY,
            temperature=temperature,
            streaming=streaming,
        )

    else:
        raise ValueError(
            f"Unknown LLM_PROVIDER: '{LLM_PROVIDER}'. "
            "Set LLM_PROVIDER to 'gemini' or 'openai' in your .env file."
        )


def get_embeddings():
    """
    Factory: returns a LangChain Embeddings model based on EMBEDDING_PROVIDER.
    """
    if EMBEDDING_PROVIDER == "gemini":
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        return GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-001",
            google_api_key=GEMINI_API_KEY,
        )

    elif EMBEDDING_PROVIDER == "openai":
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=OPENAI_API_KEY,
        )

    else:
        raise ValueError(
            f"Unknown EMBEDDING_PROVIDER: '{EMBEDDING_PROVIDER}'. "
            "Set EMBEDDING_PROVIDER to 'gemini' or 'openai' in your .env file."
        )


def has_github_token() -> bool:
    """Check if a GitHub token is configured."""
    return bool(GITHUB_TOKEN and GITHUB_TOKEN != "your-github-token")
