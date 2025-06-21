"""
config.py

Configuration module for global constants, environment variables,
and directory paths used throughout the VaultFlex RAG system.

Includes:
- Medallion architecture paths (Bronze / Silver / Gold)
- LLM and embedding model configuration
- Neo4j connection details
- Chunking parameters for text splitting
"""

from pathlib import Path
import os
from dotenv import load_dotenv

# --- Load environment variables from `.env` file (if present) ---
load_dotenv()

# --- Medallion Architecture Directory Paths ---
BASE_DIR = Path("data")

BRONZE_DIR = BASE_DIR / "bronze"  # Raw uploaded documents
SILVER_DIR = BASE_DIR / "silver"  # Cleaned + chunked JSON
GOLD_DIR = BASE_DIR / "gold"      # FAISS index / graph output
HASH_TRACK_FILE = BASE_DIR / "ingested_hashes.json"  # Tracks SHA-256 per ingested file

def get_scope_paths(scope_name: str) -> dict:
    """
    Returns all layer paths for a given dataset scope.

    Args:
        scope_name (str): Name of the dataset (e.g. "climate_docs")

    Returns:
        dict[str, Path]: Paths for 'bronze', 'silver', and 'gold'
    """
    return {
        "bronze": BRONZE_DIR / scope_name,
        "silver": SILVER_DIR / f"{scope_name}_chunks.json",
        "gold": GOLD_DIR / scope_name,
    }

# --- LLM Configuration ---
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-r1:7b")  # Used for answering queries
LLM_MODEL_EMBEDDING_MODEL = os.getenv("LLM_MODEL_EMBEDDING_MODEL", "gemma3:4b")  # Used for graph extraction
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

# --- Text Chunking Parameters ---
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 1000))        # Number of characters per chunk
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 200))   # Overlap between chunks

# --- Neo4j Graph Database Credentials ---
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
