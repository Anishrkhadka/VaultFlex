"""
Module: graph_builder_llm.py

This module extracts semantic knowledge triples from document chunks using a local LLM (via Ollama)
and inserts them into a Neo4j graph database, scoped by dataset name.

Components:
- LLM-powered triple extraction
- Robust JSON parsing from LLM output
- Neo4j connection and triple insertion
"""

import json
import requests
import re
from neo4j import GraphDatabase
from src.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, LLM_MODEL_EMBEDDING_MODEL
import time


class GraphBuilderLLM:
    """
    Handles LLM-based knowledge triple extraction and insertion into a Neo4j graph.
    """

    def __init__(self, uri=NEO4J_URI, user=NEO4J_USER, password=NEO4J_PASSWORD, model=LLM_MODEL_EMBEDDING_MODEL):
        """
        Initialise GraphBuilder with Neo4j connection and model config.

        Args:
            uri (str): Bolt URI for Neo4j
            user (str): Username for Neo4j auth
            password (str): Password for Neo4j auth
            model (str): Local LLM model name to call via Ollama
        """
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.model = model

    def close(self):
        """Closes the Neo4j connection."""
        self.driver.close()

    def insert_triple(self, subject, predicate, obj, scope):
        subject = subject.strip().lower()
        predicate = predicate.strip().lower()
        obj = obj.strip().lower()

        with self.driver.session() as session:
            session.run(
                """
                MERGE (s:Entity {name: $subject})
                MERGE (o:Entity {name: $object})
                MERGE (s)-[r:RELATION {type: $predicate, scope: $scope}]->(o)
                """,
                subject=subject,
                predicate=predicate,
                object=obj,
                scope=scope
            )

    def extract_triples_with_llm(
        self,
        text: str,
        max_retries: int = 1,
        backoff_secs: float = 1.0
    ) -> list[dict[str, str]]:
        prompt = f"""
    Extract semantic knowledge triples (subject, predicate, object) from the following text.

    Text:
    \"\"\"{text}\"\"\"

    At the end, return only a JSON array like this:
    [
    {{ "subject": "NASA", "predicate": "launched", "object": "Artemis I" }},
    ...
    ]

    Strictly return only the JSON array. No explanations or extra text.
    """
        raw_output = ""
        for attempt in range(1, max_retries + 1):
            try:
                response = requests.post(
                    "http://localhost:11434/api/generate",
                    json={"model": self.model, "prompt": prompt, "stream": False},
                    timeout=30
                )
                print(response)
                response.raise_for_status()
                raw_output = response.json().get("response", "").strip()
                print(raw_output)

                if not raw_output:
                    raise ValueError("Empty response from LLM")

                # Extract JSON array using regex
                match = re.search(r"\[\s*{.*?}\s*\]", raw_output, re.DOTALL)
                if not match:
                    raise ValueError("No valid JSON array found in model output")

                json_str = match.group(0)
                # Clean up any stray newlines or unexpected characters
                json_str = json_str.replace('\n', ' ').replace('+', '').strip()

                triples = json.loads(json_str)
                if not isinstance(triples, list):
                    raise ValueError("Parsed JSON is not a list")

                # Filter to only well-formed triples
                valid_triples = [
                    t for t in triples
                    if all(k in t and isinstance(t[k], str) for k in ("subject", "predicate", "object"))
                ]
                return valid_triples

            except Exception as e:
                print(f"[LLM] Attempt {attempt}/{max_retries} failed: {e}")
                if attempt < max_retries:
                    time.sleep(backoff_secs * attempt)  # simple exponential back-off
                else:
                    print(f"[LLM] All {max_retries} attempts failed. Giving up.")

        # If we reach here, all attempts failed
        return []


    def process_chunks(self, chunks, scope):
        total = 0
        inserted = 0
        print(f"[GRAPH] Building graph for scope: {scope}")
        for chunk in chunks:
            text = chunk.page_content
            triples = self.extract_triples_with_llm(text)
            total += len(triples)
            for triple in triples:
                s = triple.get("subject")
                p = triple.get("predicate")
                o = triple.get("object")
                if s and p and o:
                    self.insert_triple(s, p, o, scope)
                    inserted += 1
        print(f"[GRAPH] Extracted {total} triples, inserted {inserted}")

