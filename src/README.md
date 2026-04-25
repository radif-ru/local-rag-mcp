# Company Knowledge Base Assistant

Локальный Q&A-ассистент по корпоративной документации на базе RAG (Retrieval-Augmented Generation) и MCP-инструментов (Model Context Protocol).

## Возможности

- **Advanced retrieval**: hybrid search (BM25 + Vector с RRF) + cross-encoder reranker + query expansion
- **MCP-инструменты**: динамическое чтение и поиск документов
- **Локальная LLM** (Ollama): ответы без утечки данных

## Установка

### 1. Зависимости

```bash
pip install -r requirements.txt
```

Пакет `rank_bm25` (для гибридного поиска) и `sentence-transformers` (для cross-encoder реранкера) уже включены в `requirements.txt`.

### 2. Документы

Создайте каталог `docs/` и положите туда файлы документации (`.txt`, `.md`, `.pdf`, `.docx`):

```bash
mkdir docs
# Положить сюда корпоративные документы
```

### 3. Конфигурация

Отредактируйте `config.py`. Ключевые параметры:

- `DOCUMENTS_DIR` — путь к каталогу документации.
- `OLLAMA_MODEL` — локальная LLM (по умолчанию `qwen3:0.6b`, должна быть установлена через `ollama pull`).
- `EMBEDDING_MODEL` — модель эмбеддингов (по умолчанию `all-MiniLM-L6-v2`).
- Advanced pipeline (спринт 01): `HYBRID_ENABLED`, `TOP_K_HYBRID`, `RRF_K`, `RERANK_ENABLED`, `RERANKER_MODEL`, `QUERY_EXPANSION_ENABLED`, `QUERY_EXPANSION_MIN_TOKENS` — полная таблица в `../_docs/configuration.md`.

### 4. Сборка индекса (опционально)

Индекс соберётся автоматически при первом запуске. Вручную:

```bash
python main.py build-index
```

Или напрямую:

```bash
python -m rag.build_index
```

## Использование

### Интерактивный CLI

```bash
python main.py
```

После запуска можно задавать вопросы по документации. Для коротких/аббревиатурных запросов (`sqli`, `403`, `RBAC`) автоматически срабатывает query expansion, для всех — hybrid retrieve + cross-encoder rerank.

## Структура проекта

```
src/
├── config.py               # Конфигурация (вкл. advanced-pipeline параметры)
├── main.py                 # CLI entry point
├── assistant.py            # Оркестратор (CompanyKBAssistant)
├── rag/                    # RAG-компоненты
│   ├── ingest.py           # Загрузка документов
│   ├── chunk.py            # Разбиение на чанки
│   ├── embed.py            # Эмбеддинги
│   ├── build_index.py      # Сборка FAISS-индекса
│   ├── query.py            # Низкоуровневый retrieve + build_prompt + ask_llm
│   └── search_engine.py    # Фасад search() (спринт 01):
│                           # expand → hybrid (BM25+Vector+RRF) → rerank
├── mcp/                    # MCP-компоненты
│   ├── server.py           # FastMCP-сервер с read/list/search инструментами
│   └── client.py           # Клиент над subprocess + JSON-RPC stdio
├── requirements.txt        # Зависимости
└── README.md               # Этот файл
```

## Как это работает

**Build-time** (раз на корпус):

1. **Document Ingestion**: загружает документы из `docs/`
2. **Chunking**: режет на чанки c перехлёстом (`tiktoken cl100k_base`, `CHUNK_SIZE` токенов)
3. **Embedding**: SentenceTransformers (`all-MiniLM-L6-v2`)
4. **Indexing**: FAISS `IndexFlatIP` + L2-нормализация → cosine

**Runtime** (на каждый запрос, advanced pipeline спринта 01):

5. **Query expansion** (`maybe_expand_query`): для коротких/аббревиатурных запросов LLM-переформулирует
6. **Hybrid retrieve** (`hybrid_retrieve`): параллельно FAISS и BM25, слияние через **Reciprocal Rank Fusion**, top-`TOP_K_HYBRID`
7. **Reranker** (`rerank`): cross-encoder `BAAI/bge-reranker-base` оставляет top-`TOP_K`
8. **MCP-decision**: LLM решает, нужен ли MCP-инструмент (`assistant.py::_llm_decide_mcp_usage`)
9. **Prompt + LLM**: `build_prompt` + `ask_llm` (Ollama, `qwen3:0.6b`)

Всё это упаковано в один публичный фасад `rag.search_engine.search(query)`, который вызывает `CompanyKBAssistant.query`.

## MCP Tools

MCP-сервер предоставляет три инструмента (контракт не менялся в спринте 01):

- `read_document` — прочитать конкретный документ
- `list_documents` — перечислить доступные документы
- `search_documents` — найти документ по имени файла

## Решение проблем

**Индекс не найден**: выполните `python main.py build-index`.

**Ollama не отвечает**: убедитесь, что Ollama запущена и модель установлена:
```bash
ollama pull qwen3:0.6b
```

**Документов не найдено**: проверьте, что `DOCUMENTS_DIR` в `config.py` указывает на ваш каталог документов.

**Реранкер скачивает ~278 МБ при первом запуске**: это нормально, модель `BAAI/bge-reranker-base` кэшируется в `~/.cache/huggingface/`. Чтобы временно отключить — `RERANK_ENABLED = False` в `config.py`.

## Лицензия

MIT
