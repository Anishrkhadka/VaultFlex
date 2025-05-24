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
from src.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, LLM_MODEL


class GraphBuilderLLM:
    """
    Handles LLM-based knowledge triple extraction and insertion into a Neo4j graph.
    """

    def __init__(self, uri=NEO4J_URI, user=NEO4J_USER, password=NEO4J_PASSWORD, model=LLM_MODEL):
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
        """
        Inserts a semantic triple into Neo4j with a scope tag.

        Args:
            subject (str): Entity name
            predicate (str): Relationship type
            obj (str): Target entity name
            scope (str): Dataset scope identifier
        """
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

    def extract_triples_with_llm(self, text: str):
        """
        Extracts triples from a block of text using the local LLM via Ollama.

        Args:
            text (str): Chunk of document text

        Returns:
            list[dict]: Extracted triples with keys: subject, predicate, object
        """
        prompt = f"""
Extract semantic knowledge triples (subject, predicate, object) from the following text.

Text:
\"\"\"{text}\"\"\"

Think aloud if needed, but at the end, respond only with a JSON array like:
[
  {{ "subject": "...", "predicate": "...", "object": "..." }},
  ...
]

Ensure the output is valid JSON. Do not use '+' for string concatenation.
"""
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": self.model, "prompt": prompt, "stream": False}
        )
        print(response)

        result = response.json()
        raw_output = result.get("response", "").strip()

        if not raw_output:
            print("[LLM] Empty response.")
            return []

        try:
            # Extract first JSON array from raw output using regex
            match = re.search(r"\[.*?\]", raw_output, re.DOTALL)
            if not match:
                raise ValueError("No JSON array found.")

            json_str = match.group(0)

            # Clean up malformed JSON (common LLM artifacts)
            json_str = json_str.replace('+', '')
            json_str = re.sub(r"\n\s*", " ", json_str)

            triples = json.loads(json_str)
            if not isinstance(triples, list):
                raise ValueError("Expected a list of triples.")

            return triples

        except Exception as e:
            print(f"[LLM] JSON parse error: {e}")
            print(f"[LLM] Raw output was:\n{raw_output}")
            return []

    def process_chunks(self, chunks, scope):
        """
        Extracts and inserts knowledge triples from document chunks for a given scope.

        Args:
            chunks (list): List of LangChain Document objects
            scope (str): Dataset scope to tag inserted relationships
        """
        print(f"[GRAPH] Building graph for scope: {scope}")
        for chunk in chunks:
            text = chunk.page_content
            triples = self.extract_triples_with_llm(text)
            for triple in triples:
                s = triple.get("subject")
                p = triple.get("predicate")
                o = triple.get("object")
                if s and p and o:
                    self.insert_triple(s, p, o, scope)
