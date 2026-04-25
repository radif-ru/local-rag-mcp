# Configuration for Company Knowledge Base Assistant

# Document directory - update this to point to your company documentation
DOCUMENTS_DIR = "./docs"

# Chunking configuration
CHUNK_SIZE = 700
CHUNK_OVERLAP = 100

# Embedding model
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# FAISS index paths (relative to src directory)
FAISS_INDEX_PATH = "index.faiss"
CHUNKS_PATH = "chunks.pkl"

# Ollama configuration
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen3:0.6b"

# RAG retrieval configuration
TOP_K = 5

# Advanced search pipeline (sprint 01)
# Hybrid search: BM25 + Vector merged via Reciprocal Rank Fusion (RRF).
HYBRID_ENABLED = True
TOP_K_HYBRID = 20         # candidates kept after hybrid merge (input to reranker)
RRF_K = 60                # canonical Cormack & Clarke (2009) constant
