"""
service_status.py

Health-check utilities for VaultFlex backend services.

Responsibilities:
- Verify availability of the Ollama LLM server
- Test connectivity to the Neo4j graph database
- Report status of configured LLM model
"""

import requests
from neo4j import GraphDatabase
from src.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, LLM_MODEL


def check_ollama() -> bool:
    """
    Check whether the local Ollama API is reachable and responding.

    Returns:
        bool: True if Ollama is reachable, False otherwise.
    """
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=2)
        return r.status_code == 200
    except Exception:
        return False


def check_neo4j() -> bool:
    """
    Test connectivity to the Neo4j graph database.

    Returns:
        bool: True if the connection is successful, False otherwise.
    """
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        with driver.session() as session:
            session.run("RETURN 1")
        driver.close()
        return True
    except Exception:
        return False


def get_backend_status() -> dict:
    """
    Return the health status of critical backend services.

    Returns:
        dict: Dictionary containing:
            - 'ollama': True/False for Ollama status
            - 'neo4j' : True/False for Neo4j status
            - 'model' : Name of the active LLM model (from config)
    """
    return {
        "ollama": check_ollama(),
        "neo4j": check_neo4j(),
        "model": LLM_MODEL
    }
