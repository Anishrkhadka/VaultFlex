# VaultFlex

**Chat with your Knowledge** using a hybrid RAG pipeline (Vector + Graph). Built for teams that want full control over their data.

## 🚀 Features

- 📁 **Flexible Knowledge Base Scopes** — create isolated workspaces per domain or project
- 🧠 **Hybrid Retrieval** — combines vector search (FAISS) and knowledge graphs (Neo4j)
- 🔍 **LLM-Augmented Reasoning** — responds only from your ingested content (no hallucinations)
- 🧾 **Document Parsing** — PDF, DOCX, Markdown, TXT support
- 🪄 **Interactive UI** — powered by Streamlit, clean and customisable
- 💾 **Medallion Architecture** — Bronze → Silver → Gold data layers

## 📁 Medallion Architecture

VaultFlex follows a structured **Medallion data pipeline**:

- 🥉 **Bronze**: Raw document storage
- 🥈 **Silver**: Cleaned and chunked JSON text
- 🥇 **Gold**: Embeddings stored in FAISS for semantic search + graphs in Neo4j

Each knowledge base scope maintains its own isolated Bronze/Silver/Gold structure. This enables reproducible, debuggable, and extendable pipelines.

```
VaultFlex/
├── data/
│   └── <dataset_name>/
│       ├── bronze/       # Raw documents (PDF, DOCX, etc.)
│       ├── silver/       # Chunked and cleaned JSON text
│       └── gold/         # FAISS vector store
```

## 🔁 Hybrid Pipeline Workflow

```
          User Upload
               │
           [Bronze]
               │
     Chunking + Cleaning
               ↓
           [Silver]
               │
   Embedding + FAISS Indexing
               ↓
           [Gold]
               │
     + Graph Triples (Neo4j)
```

## 🧪 Technologies

- `Streamlit` — UI
- `FAISS` + `HuggingFace` — Embedding & vector storage
- `Neo4j` — Knowledge graph backend
- `LangChain` — Document parsing and chunking
- `Ollama` / `LLM API` — Model communication

---

## 📦 Project Structure

```
VaultFlex/
├── data/                    # All datasets (Bronze/Silver/Gold)
│   ├── bronze/             # Raw uploaded documents per KB
│   ├── silver/             # Chunked documents as JSON
│   ├── gold/               # FAISS vector indexes
│   └── ingested_hashes.json
├── doc/                    # Docs and branding
│   └── images/vaultFlex_logo.png
├── src/
│   ├── ui/                 # Streamlit UI modules
│   ├── vector/             # Embedding, graph builder, retriever
│   ├── utils/              # Utility tools (e.g. service checks)
│   ├── config.py           # Centralised paths and settings
│   └── __version__.py
├── main.py                 # App entry point
├── environment.yml         # Conda environment setup
├── requirements.txt        # Pip requirements
└── README.md               # You're reading it

```

---

## 🧠 LLM Usage

VaultFlex calls your selected local/remote LLM to:
- Refine vague user questions
- Synthesise answers from graph triples and chunks
- Avoid hallucination by grounding output in source data

Supports: `deepseek-r1`, `gemma3`, or anything via `Ollama`.

---

## 🏁 Quickstart

```bash
# 1. Start backend (Ollama and neo4j)
# 2. Install dependencies
pip install -r requirements.txt

# 3. Update .env
update .env

# 4. Launch the UI
streamlit run app.py
```

---

## 💬 Example Use

- Upload multiple PDFs and DOCXs into `Finance` knowledge base
- Ask: *"what were the key themes discussed in quarterly reports?"*
- VaultFlex retrieves vector data, queries the graph, and answers using both


---

🤝 Made with ❤️ by Anish Khadka - VaultFlex
