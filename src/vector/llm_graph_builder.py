"""
llm_graph_builder.py

This module defines `GraphBuilderLLM`, a class responsible for extracting
semantic triples (subject–predicate–object) from text using an LLM, and
inserting them into a scoped Neo4j graph.

The class supports:
- Querying a local LLM (e.g., via Ollama) for triple extraction
- Inserting nodes and relationships with scope tagging into Neo4j
- Processing batches of text chunks from a knowledge base
"""

import json
import requests
import re
import time
from neo4j import GraphDatabase
from src.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, LLM_MODEL_EMBEDDING_MODEL


class GraphBuilderLLM:
    """
    Handles LLM-based semantic triple extraction and inserts them into a Neo4j graph.
    """

    def __init__(self, uri=NEO4J_URI, user=NEO4J_USER, password=NEO4J_PASSWORD, model=LLM_MODEL_EMBEDDING_MODEL):
        """
        Initialise the GraphBuilderLLM with Neo4j connection and LLM model config.

        Args:
            uri (str): Bolt URI for Neo4j.
            user (str): Neo4j username.
            password (str): Neo4j password.
            model (str): LLM model name to call via Ollama.
        """
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.model = model

    def close(self):
        """
        Closes the Neo4j database connection.
        """
        self.driver.close()

    def insert_triple(self, subject: str, predicate: str, obj: str, scope: str):
        """
        Inserts a semantic triple into Neo4j with scope tagging.

        Args:
            subject (str): Triple subject.
            predicate (str): Triple predicate.
            obj (str): Triple object.
            scope (str): Knowledge base scope to isolate data.
        """
        subject = subject.strip().lower()
        predicate = predicate.strip().lower()
        obj = obj.strip().lower()

        with self.driver.session() as session:
            session.run(
                """
                MERGE (s:Entity {name: $subject})
                ON CREATE SET s.scope = $scope
                MERGE (o:Entity {name: $object})
                ON CREATE SET o.scope = $scope
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
        """
        Sends a text block to an LLM and extracts semantic triples.

        Args:
            text (str): Input text to analyse.
            max_retries (int): Number of retry attempts on failure.
            backoff_secs (float): Delay multiplier between retries.

        Returns:
            list[dict[str, str]]: List of valid triples in dict form.
        """
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

                # Extract JSON array from output
                match = re.search(r"\[\s*{.*?}\s*\]", raw_output, re.DOTALL)
                if not match:
                    raise ValueError("No valid JSON array found in model output")

                json_str = match.group(0)
                json_str = json_str.replace('\n', ' ').replace('+', '').strip()
                triples = json.loads(json_str)

                if not isinstance(triples, list):
                    raise ValueError("Parsed JSON is not a list")

                valid_triples = [
                    t for t in triples
                    if all(k in t and isinstance(t[k], str) for k in ("subject", "predicate", "object"))
                ]
                return valid_triples

            except Exception as e:
                print(f"[LLM] Attempt {attempt}/{max_retries} failed: {e}")
                if attempt < max_retries:
                    time.sleep(backoff_secs * attempt)
                else:
                    print(f"[LLM] All {max_retries} attempts failed. Giving up.")

        return []

    def process_chunks(self, chunks, scope: str):
        """
        Processes a list of text chunks:
        - Sends each chunk to the LLM to extract triples
        - Inserts all valid triples into the Neo4j graph

        Args:
            chunks (list): List of LangChain Document objects with `.page_content`.
            scope (str): The current knowledge base scope.
        """
        total_triples = 0
        inserted_triples = 0
        skipped_triples = 0

        print(f"[GRAPH] Building graph for scope: {scope}")

        for chunk in chunks:
            text = chunk.page_content.strip()
            if not text:
                continue

            triples = self.extract_triples_with_llm(text)
            total_triples += len(triples)

            for triple in triples:
                s = triple.get("subject", "").strip()
                p = triple.get("predicate", "").strip()
                o = triple.get("object", "").strip()

                if all([s, p, o]):
                    self.insert_triple(s, p, o, scope)
                    inserted_triples += 1
                else:
                    skipped_triples += 1
                    print(f"[WARN] Skipped malformed triple: {triple}")

        print(f"[GRAPH] Extracted {total_triples} triples")
        print(f"[GRAPH] Inserted  {inserted_triples} triples")
        if skipped_triples:
            print(f"[GRAPH] Skipped   {skipped_triples} malformed triples")
