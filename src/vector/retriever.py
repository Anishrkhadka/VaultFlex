import requests
import json
import time
from typing import List, Dict
from neo4j import GraphDatabase
from sklearn.feature_extraction.text import TfidfVectorizer
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
import re
import html
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
    A class to retrieve information and answer questions based on knowledge base.
    """

    def __init__(self, neo4j_uri=NEO4J_URI, neo4j_user=NEO4J_USER, neo4j_password=NEO4J_PASSWORD):
        """
        Initializes the KnowledgeBaseRetriever.

        Args:
            neo4j_uri: The URI of the Neo4j database.
            neo4j_user: The username for the Neo4j database.
            neo4j_password: The password for the Neo4j database.
        """
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))

    def _get_model_no_memory(self, prompt: str, model: str = LLM_MODEL, system_prompt: str = None) -> str:
        url = "http://localhost:11434/api/generate"
        headers = {"Content-Type": "application/json"}

        # Combine system prompt + user prompt
        full_prompt = f"{system_prompt.strip()}\n\n{prompt.strip()}" if system_prompt else prompt

        payload = {
            "model": model,
            "prompt": full_prompt,
            "stream": False
        }

        for attempt in range(3):
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=30)
                resp.raise_for_status()
                return resp.json().get("response", "").strip()
            except Exception as e:
                print(f"[LLM Error] Attempt {attempt + 1}: {e}")
                time.sleep((attempt + 1) * 1.5)

        return ""

    
    def _get_model(
        self,
        prompt: str = None,
        model: str = LLM_MODEL,
        system_prompt: str = None,
        history: list = None
    ) -> str:
        url = "http://localhost:11434/api/chat"
        headers = {"Content-Type": "application/json"}

        # Use history or start fresh
        messages = history[:] if history else []

        # Add system prompt only once (if not already in history)
        if system_prompt and not any(m["role"] == "system" for m in messages):
            messages.insert(0, {"role": "system", "content": system_prompt})

        # Append current prompt
        if prompt:
            messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "stream": False
        }

        for attempt in range(3):
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=30)
                resp.raise_for_status()
                reply = resp.json()["message"]["content"].strip()

                # Optional: return both reply and messages for future continuation
                return reply, messages + [{"role": "assistant", "content": reply}]
            except Exception as e:
                print(f"[LLM Error] Attempt {attempt + 1}: {e}")
                time.sleep((attempt + 1) * 1.5)

        return "", messages


    def _run_cypher(self, query: str, params: dict = None) -> List[Dict]:
        """
        Executes a Cypher query against the Neo4j database.

        Args:
            query: The Cypher query to execute.
            params: Optional parameters for the query.

        Returns:
            A list of dictionaries representing the results of the query.
        """
        with self.driver.session() as session:
            return session.run(query, params or {}).data()

    def retrieve_docs(self, question: str, scope: str) -> List[str]:
        """
        Retrieves relevant documents from the vector database.

        Args:
            question: The question to use for the search.
            scope: The scope of the knowledge base.

        Returns:
            A list of strings, where each string is a document.
        """
        vector_path = f"data/gold/{scope}"
        embedder = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
        db = FAISS.load_local(vector_path, embedder, allow_dangerous_deserialization=True)
        docs = db.similarity_search(question, k=3)
        return [doc.page_content for doc in docs]

    def extract_keywords(self, texts: List[str], top_k: int = 5) -> List[str]:
        """
        Extracts keywords from a list of texts.

        Args:
            texts: A list of strings, where each string is a text.
            top_k: The number of top keywords to extract.

        Returns:
            A list of strings, where each string is a keyword.
        """
        vectorizer = TfidfVectorizer(stop_words="english", max_features=1000)
        X = vectorizer.fit_transform(texts)
        scores = zip(vectorizer.get_feature_names_out(), X.toarray().sum(axis=0))  # sum across all docs
        sorted_terms = sorted(scores, key=lambda x: x[1], reverse=True)
        return [term.lower() for term, _ in sorted_terms[:top_k]]

    def rewrite_question(self, question: str, model_name: str) -> str:
        system_prompt = (
            "You are an AI assistant that rewrites vague or informal user questions "
            "into clearer, more specific ones suitable for knowledge base search. "
            "Do not add any comments, explanations, or labels — return only the improved question as a single plain sentence."
            )

        
        user_prompt = f"""
        Original Question:
        {question}

        Improved Question (return only the question, no other text):
        """

        return self._get_model_no_memory(user_prompt, model=model_name, system_prompt=system_prompt).strip()


    def answer_with_keywords_and_chunks(self, question: str, scope: str, model_name:str) -> str:
        """
        Answers a question based on the knowledge base.

        Args:
            question: The question to answer.
            scope: The scope of the knowledge base.

        Returns:
            The answer to the question.
        """
        #Step 1, rewrite the question 
        rewritten_question = self.rewrite_question(question, model_name)
        print(f"Rewritten Question: {rewritten_question}")

        # Step 2: FAISS retrieval
        text_chunks = self.retrieve_docs(rewritten_question, scope)

        # Step 3: Extract keywords from FAISS chunks, not the question
        keywords = self.extract_keywords(text_chunks)  # Pass text_chunks directly
        print(f"keywords: {keywords}")

        # Step 4: Graph query using extracted keywords
        cypher = """
            UNWIND $keywords AS kw
            MATCH (s:Entity)-[r:RELATION {scope: $scope}]->(o:Entity)
            WHERE toLower(s.name) CONTAINS kw OR toLower(o.name) CONTAINS kw
            RETURN s.name AS Subject, r.type AS Predicate, o.name AS Object
            LIMIT 25
            """
        graph_triples = self._run_cypher(cypher, {"keywords": keywords, "scope": scope})
        print(json.dumps(graph_triples, indent=2))

        # Step 4: Combine and answer
        if not graph_triples and not text_chunks:
            return "Sorry, I couldn’t find any relevant information."

        def clean_text_chunk(text: str) -> str:
            # Convert escaped unicode to readable characters
            text = text.encode().decode('unicode_escape')

            # Remove emojis and other unicode symbols
            text = re.sub(r"[^\w\s.,:;()\-\'\"%]", "", text)

            # Replace multiple newlines or spaces with a single newline or space
            text = re.sub(r'\n+', '\n', text)
            text = re.sub(r'\s{2,}', ' ', text)

            # Strip leading/trailing whitespace
            return text.strip()

        def clean_text_chunks(chunks: list[str]) -> list[str]:
            return [clean_text_chunk(chunk) for chunk in chunks]

        cleaned_chunks = clean_text_chunks(text_chunks)

        system_prompt = """
        You are a helpful assistant called Local-First AI, developed by Anish Khadka.

        Your primary role is to help users answer questions based on:
        - A list of structured triples from a graph database
        - A list of retrieved text documents

        If the user's message is a greeting (e.g., "hello", "hi", "hey"), respond with a friendly greeting back.

        Otherwise, use ONLY the provided information (triples and text) to answer their question factually. 
        Do NOT make things up or guess beyond the given data.

        If there's not enough information to answer, say so politely.
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
        history=st.session_state.get("chat_history", []))
        
        st.session_state["chat_history"] = updated_history

        return answer.strip()




if __name__ == "__main__":
    retriever = KnowledgeBaseRetriever()
    question = "What is the capital of France?"
    scope = "France"
    answer = retriever.answer_with_keywords_and_chunks(question, scope)
    print(answer)