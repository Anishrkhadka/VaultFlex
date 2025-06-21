"""
retriever.py

This module defines the `KnowledgeBaseRetriever` class, which is responsible for:
- Rewriting user queries via LLM for clarity and specificity
- Retrieving semantically relevant chunks using FAISS (dense retrieval)
- Extracting keywords for graph queries
- Running Cypher queries over scoped Neo4j subgraphs
- Generating answers using a local LLM based on retrieved text and triples
"""

import requests
import json
import time
import re
from typing import List, Dict

from neo4j import GraphDatabase
from sklearn.feature_extraction.text import TfidfVectorizer
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
import streamlit as st

from src.config import (
    LLM_MODEL,
    EMBEDDING_MODEL,
    NEO4J_URI,
    NEO4J_USER,
    NEO4J_PASSWORD,
)


class KnowledgeBaseRetriever:
    """
    Retrieves information from FAISS and Neo4j based on user questions.
    Enhances queries using LLM and returns factual answers.
    """

    def __init__(self, neo4j_uri=NEO4J_URI, neo4j_user=NEO4J_USER, neo4j_password=NEO4J_PASSWORD):
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))

    def _get_model_no_memory(self, prompt: str, model: str = LLM_MODEL, system_prompt: str = None) -> str:
        """
        Sends a prompt to the LLM endpoint (stateless mode).

        Args:
            prompt: User message.
            model: Model name to query (Ollama).
            system_prompt: Optional system instructions.

        Returns:
            str: Model's plain response.
        """
        url = "http://localhost:11434/api/generate"
        headers = {"Content-Type": "application/json"}
        full_prompt = f"{system_prompt.strip()}\n\n{prompt.strip()}" if system_prompt else prompt

        payload = {"model": model, "prompt": full_prompt, "stream": False}

        for attempt in range(3):
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=30)
                resp.raise_for_status()
                return resp.json().get("response", "").strip()
            except Exception as e:
                print(f"[LLM Error] Attempt {attempt + 1}: {e}")
                time.sleep((attempt + 1) * 1.5)

        return ""

    def _get_model(self, prompt: str = None, model: str = LLM_MODEL,
                   system_prompt: str = None, history: list = None) -> str:
        """
        Sends a prompt to the LLM in chat mode, optionally with memory.

        Args:
            prompt: Current user message.
            model: Model name (Ollama).
            system_prompt: Initial system instructions.
            history: List of prior messages in OpenAI chat format.

        Returns:
            Tuple[str, List[dict]]: (response, updated chat history)
        """
        url = "http://localhost:11434/api/chat"
        headers = {"Content-Type": "application/json"}

        messages = history[:] if history else []
        if system_prompt and not any(m["role"] == "system" for m in messages):
            messages.insert(0, {"role": "system", "content": system_prompt})

        if prompt:
            messages.append({"role": "user", "content": prompt})

        payload = {"model": model, "messages": messages, "stream": False}

        for attempt in range(3):
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=30)
                resp.raise_for_status()
                reply = resp.json()["message"]["content"].strip()
                return reply, messages + [{"role": "assistant", "content": reply}]
            except Exception as e:
                print(f"[LLM Error] Attempt {attempt + 1}: {e}")
                time.sleep((attempt + 1) * 1.5)

        return "", messages

    def _run_cypher(self, query: str, params: dict = None) -> List[Dict]:
        """
        Executes a Cypher query on Neo4j.

        Args:
            query: Cypher string.
            params: Optional dictionary of query parameters.

        Returns:
            List of results as dictionaries.
        """
        with self.driver.session() as session:
            return session.run(query, params or {}).data()

    def retrieve_docs(self, question: str, scope: str) -> List[str]:
        """
        Uses FAISS to retrieve top-k documents relevant to the question.

        Args:
            question: The query string.
            scope: The knowledge base scope.

        Returns:
            List of relevant text chunks.
        """
        vector_path = f"data/gold/{scope}"
        embedder = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
        db = FAISS.load_local(vector_path, embedder, allow_dangerous_deserialization=True)
        docs = db.similarity_search(question, k=3)
        return [doc.page_content for doc in docs]

    def extract_keywords(self, texts: List[str], top_k: int = 5) -> List[str]:
        """
        Extracts top-k keywords from a list of documents using TF-IDF.

        Args:
            texts: Document strings.
            top_k: Number of keywords to extract.

        Returns:
            List of keywords.
        """
        vectorizer = TfidfVectorizer(stop_words="english", max_features=1000)
        X = vectorizer.fit_transform(texts)
        scores = zip(vectorizer.get_feature_names_out(), X.toarray().sum(axis=0))
        sorted_terms = sorted(scores, key=lambda x: x[1], reverse=True)
        return [term.lower() for term, _ in sorted_terms[:top_k]]

    def rewrite_question(self, question: str, model_name: str) -> str:
        """
        Rewrites a user query for clarity using the LLM.

        Args:
            question: The original question.
            model_name: LLM model to use.

        Returns:
            Rewritten question as plain text.
        """
        system_prompt = (
            "You are an AI assistant that rewrites vague or informal user questions "
            "into clearer, more specific ones suitable for knowledge base search. "
            "Do not add any comments, explanations, or labels — return only the improved question."
        )

        user_prompt = f"""
        Original Question:
        {question}

        Improved Question (return only the question, no other text):
        """

        return self._get_model_no_memory(user_prompt, model=model_name, system_prompt=system_prompt).strip()

    def answer_with_keywords_and_chunks(self, question: str, scope: str, model_name: str) -> str:
        """
        Full RAG pipeline: Rewrites question, retrieves chunks, queries graph, and generates an answer.

        Args:
            question: The user input.
            scope: The knowledge base scope.
            model_name: Which LLM to use.

        Returns:
            Final assistant answer string.
        """
        rewritten_question = self.rewrite_question(question, model_name)
        print(f"Rewritten Question: {rewritten_question}")

        text_chunks = self.retrieve_docs(rewritten_question, scope)
        keywords = self.extract_keywords(text_chunks)
        print(f"Keywords: {keywords}")

        # Graph query
        cypher = """
            UNWIND $keywords AS kw
            MATCH (s:Entity)-[r:RELATION {scope: $scope}]->(o:Entity)
            WHERE toLower(s.name) CONTAINS kw OR toLower(o.name) CONTAINS kw
            RETURN s.name AS Subject, r.type AS Predicate, o.name AS Object
            LIMIT 25
        """
        graph_triples = self._run_cypher(cypher, {"keywords": keywords, "scope": scope})
        print(json.dumps(graph_triples, indent=2))

        if not graph_triples and not text_chunks:
            return "Sorry, I couldn’t find any relevant information."

        def clean_text_chunk(text: str) -> str:
            text = text.encode().decode('unicode_escape')
            text = re.sub(r"[^\w\s.,:;()\-\'\"%]", "", text)
            text = re.sub(r'\n+', '\n', text)
            text = re.sub(r'\s{2,}', ' ', text)
            return text.strip()

        cleaned_chunks = [clean_text_chunk(chunk) for chunk in text_chunks]

        system_prompt = """
        You are a helpful assistant called Local-First AI, developed by Anish Khadka.

        Your primary role is to help users answer questions based on:
        - A list of structured triples from a graph database
        - A list of retrieved text documents

        If the user's message is a greeting, respond accordingly.

        Otherwise, use ONLY the provided data to answer. Never guess or hallucinate.
        """

        user_prompt = f"""
        Question:
        {rewritten_question}

        Graph Triples:
        {graph_triples}

        Text Chunks:
        {cleaned_chunks}

        Answer:
        """
        print(user_prompt)

        answer, updated_history = self._get_model(
            prompt=user_prompt,
            model=model_name,
            system_prompt=system_prompt,
            history=st.session_state.get("chat_history", [])
        )
        st.session_state["chat_history"] = updated_history

        return answer.strip()


if __name__ == "__main__":
    retriever = KnowledgeBaseRetriever()
    question = "What is the capital of France?"
    scope = "France"
    answer = retriever.answer_with_keywords_and_chunks(question, scope, model_name=LLM_MODEL)
    print(answer)
