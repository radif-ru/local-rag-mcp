# Внешние ссылки

Каталог ссылок на документацию используемых в проекте библиотек, моделей, протоколов и стандартов. Цель — не искать одно и то же повторно при работе над задачей. **Это не справочник по проекту**, а только указатели наружу.

При добавлении новой зависимости в `src/requirements.txt` или новой внешней системы — допишите сюда строку с краткой пометкой «зачем нужно в проекте» (модуль / функция / константа `config.py`).

## 1. LLM-слой

| Что                     | Ссылка                                                                 | Где в проекте                                                                              |
|-------------------------|------------------------------------------------------------------------|--------------------------------------------------------------------------------------------|
| Ollama                  | https://ollama.com/                                                    | LLM-рантайм, REST на `localhost:11434`, см. `stack.md` § 3                                 |
| Ollama REST API         | https://github.com/ollama/ollama/blob/main/docs/api.md                 | `src/rag/query.py::ask_llm` — `/api/generate`                                              |
| Ollama Python SDK       | https://github.com/ollama/ollama-python                                | `src/assistant.py::_llm_decide_mcp_usage`, `src/rag/search_engine.py::maybe_expand_query`  |
| Модель `qwen3:0.6b`     | https://ollama.com/library/qwen3                                       | `OLLAMA_MODEL` в `src/config.py`                                                           |

## 2. Эмбеддинги и поиск

| Что                                | Ссылка                                                                                | Где в проекте                                                                              |
|------------------------------------|---------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------|
| sentence-transformers              | https://www.sbert.net/                                                                | `src/rag/embed.py::embed_chunks`, `src/rag/search_engine.py::rerank` (CrossEncoder)        |
| Модель `all-MiniLM-L6-v2`          | https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2                         | `EMBEDDING_MODEL` в `src/config.py` (384-dim, MiniLM)                                      |
| Модель `BAAI/bge-reranker-base`    | https://huggingface.co/BAAI/bge-reranker-base                                         | `RERANKER_MODEL` в `src/config.py` (cross-encoder, спринт 01.3.2)                          |
| FAISS                              | https://faiss.ai/                                                                     | `src/rag/build_index.py`, `src/rag/query.py` — `IndexFlatIP` + `faiss.normalize_L2`        |
| FAISS Python wiki                  | https://github.com/facebookresearch/faiss/wiki/Getting-started                        | референс по `add` / `search` / `IndexFlatIP`                                               |
| numpy                              | https://numpy.org/doc/stable/                                                         | базовые операции с массивами эмбеддингов                                                   |
| tiktoken                           | https://github.com/openai/tiktoken                                                    | `src/rag/chunk.py` — токенайзер `cl100k_base` (см. оговорку в `current-state.md` § 2.2)    |
| `rank_bm25`                        | https://github.com/dorianbrown/rank_bm25                                              | `src/rag/search_engine.py::hybrid_retrieve` — `BM25Okapi` (спринт 01.3.1)                  |
| Reciprocal Rank Fusion (Cormack)   | https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf                             | формула RRF, константа `RRF_K = 60` в `src/config.py`                                      |

## 3. MCP

| Что                              | Ссылка                                                                | Где в проекте                                                                  |
|----------------------------------|------------------------------------------------------------------------|--------------------------------------------------------------------------------|
| Model Context Protocol (spec)    | https://modelcontextprotocol.io/                                       | референс по транспорту, формату tool/resource/prompt                           |
| MCP — спецификация (GitHub)      | https://github.com/modelcontextprotocol/specification                  | детальная спецификация JSON-RPC сообщений MCP                                  |
| FastMCP                          | https://github.com/jlowin/fastmcp                                      | `src/mcp/server.py` — `FastMCP("doc-tools")`, декоратор `@mcp.tool`            |
| JSON-RPC 2.0                     | https://www.jsonrpc.org/specification                                  | `src/mcp/client.py` — формат сообщений по stdio                                |

## 4. Парсинг документов

| Что              | Ссылка                                                | Где в проекте                       |
|------------------|--------------------------------------------------------|-------------------------------------|
| pypdf            | https://pypdf.readthedocs.io/                          | `src/rag/ingest.py::load_document` (`.pdf`) |
| python-docx      | https://python-docx.readthedocs.io/                    | `src/rag/ingest.py::load_document` (`.docx`) |

## 5. CLI / UI / HTTP

| Что              | Ссылка                                                 | Где в проекте                                              |
|------------------|---------------------------------------------------------|------------------------------------------------------------|
| rich             | https://rich.readthedocs.io/                            | `src/assistant.py::__main__` — markdown-вывод              |
| requests         | https://requests.readthedocs.io/                        | `src/rag/query.py::ask_llm` — синхронный POST в Ollama     |

## 6. Стандарты разработки

| Что                          | Ссылка                                                       | Где в проекте                                              |
|------------------------------|---------------------------------------------------------------|------------------------------------------------------------|
| Conventional Commits         | https://www.conventionalcommits.org/                          | формат коммитов, см. `_docs/instructions.md` § 4.1         |
| Python typing                | https://docs.python.org/3/library/typing.html                 | type hints обязательны в публичных API (instructions § 3.1) |
| pytest                       | https://docs.pytest.org/                                      | целевой test-runner (см. `roadmap.md` Phase 2, спринт 02.2.4) |
| Python `logging`             | https://docs.python.org/3/library/logging.html                | целевой логгер (см. спринт 02.2.2)                         |
| Python `logging.handlers`    | https://docs.python.org/3/library/logging.handlers.html       | `RotatingFileHandler` для лог-файла                        |
