# Local RAG/MCP Knowledge Base Assistant

# 📋 Проблема

- **Растущая документация**: знания разбросаны по файлам
- **Поиск информации**: сложно найти ответ без точных ключевых слов
- **Приватность**: облачные решения могут не соответствовать политикам компании

```
Пользователь → Поиск → Ответ = 😫
```

# ✨ Решение

**Локальный интеллектуальный Q&A-ассистент** на базе:

- **RAG**: advanced retrieval (BM25 + Vector + RRF, cross-encoder reranker, query expansion)
- **MCP**: инструменты для динамического доступа к документам
- **Локальная LLM** (Ollama): ответы без утечки данных

# ✨ Ключевые преимущества

- ✅ Privacy-first (всё работает локально)
- ✅ Нет расходов на API
- ✅ Быстрый семантический поиск + reranker для точности
- ✅ Интеллектуальный доступ к документам через MCP
- ✅ Полный контроль над данными

# 🏗️ Архитектура — верхний уровень

```
┌──────────────────────┐
│   User Interface     │ (CLI)
└──────────┬───────────┘
           │
     ┌─────┴─────┐
     ▼           ▼
  [RAG]       [MCP]
  search()     Tools
     │           │
     └─────┬─────┘
           ▼
    [Ollama LLM]
```

# 🏗️ Архитектура — хранилище

```
┌────────────────┐
│  FAISS Index   │ векторы (cosine via IndexFlatIP)
│  + BM25 (RAM)  │ ленивый BM25Okapi поверх чанков
│  + MCP Tools   │ read / list / search документы
└────────┬───────┘
         │
    ┌────▼─────┐
    │   docs/  │  исходные файлы
    │ directory│  (md / txt / pdf / docx)
    └──────────┘
```

# 🔍 RAG Pipeline

**Build-time** (раз на корпус):

1. Document Loading → читаем .md, .txt, .pdf, .docx
2. Chunking → режем на чанки (CHUNK_SIZE токенов cl100k_base, перехлёст CHUNK_OVERLAP)
3. Embedding → SentenceTransformers (`all-MiniLM-L6-v2`)
4. Indexing → FAISS `IndexFlatIP` + L2-нормализация → cosine

**Runtime** (на каждый вопрос) — advanced pipeline (спринт 01):

5. Query expansion → короткие/аббревиатурные запросы LLM переформулирует
6. Hybrid retrieve → BM25 + Vector параллельно, слияние через RRF (top_n = TOP_K_HYBRID)
7. Reranker → cross-encoder `BAAI/bge-reranker-base` оставляет top-`TOP_K`
8. Prompt Building → собираем context-aware промпт
9. LLM Generation → ответ от Ollama (`qwen3:0.6b` по умолчанию)

Детали — `_docs/rag-pipeline.md` § 9 «Advanced Pipeline».

# 🔍 Почему FAISS?

- Быстрый векторный поиск (cosine через inner product на нормализованных векторах)
- Лёгкий и экономный по памяти
- Нет внешних зависимостей
- Идеален для локальных развёртываний
- Держит миллионы векторов

# 🔧 MCP — Model Context Protocol

MCP даёт **стандартизованный интерфейс** для вызова инструментов из LLM:

```python
read_document(file_path)
list_documents()
search_documents(query)
```

Решение «вызывать ли MCP-инструмент и какой» принимает сама LLM отдельным JSON-решением (`assistant.py::_llm_decide_mcp_usage`).

# 🔧 Преимущества MCP

- LLM сама вызывает инструменты
- Прямой доступ к документам в момент запроса
- Стандартизованный протокол (JSON-RPC по stdio)
- Легко расширяется (декоратор `@mcp.tool`)
- Инструменты выполняются локально

# 💻 Tech Stack

```
Язык:         Python 3.10+
Vector DB:    FAISS (IndexFlatIP)
Lexical:      rank_bm25 (BM25Okapi)
Embeddings:   SentenceTransformers (all-MiniLM-L6-v2)
Reranker:     CrossEncoder (BAAI/bge-reranker-base)
LLM:          Ollama (qwen3:0.6b по умолчанию)
MCP:          FastMCP
```

# 📁 Структура проекта

```
src/
├── config.py            Конфигурация (вкл. advanced-pipeline параметры)
├── main.py              CLI entry point
├── assistant.py         Оркестратор (RAG + MCP-decision + Ollama)
├── rag/
│   ├── ingest.py        Загрузка документов
│   ├── chunk.py         Разбиение на чанки
│   ├── embed.py         Эмбеддинги
│   ├── build_index.py   Сборка FAISS-индекса
│   ├── query.py         Низкоуровневый retrieve + build_prompt + ask_llm
│   └── search_engine.py Фасад search() (спринт 01):
│                        expand → hybrid (BM25+Vector+RRF) → rerank
├── mcp/
│   ├── server.py        FastMCP-сервер с read/list/search-инструментами
│   └── client.py        Обёртка subprocess + JSON-RPC stdio
└── docs/                Каталог исходных документов (gitignored)
```

# 🚀 Сборка индекса (Setup)

```
$ python main.py build-index

1. Загрузка документов из docs/
  ↓
2. Разбиение на чанки (cl100k_base, CHUNK_SIZE токенов)
  ↓
3. Эмбеддинги (all-MiniLM-L6-v2)
  ↓
4. FAISS-индекс (IndexFlatIP + L2-norm → cosine)
  ↓
5. Сохранение: index.faiss + chunks.pkl
```

# 🚀 Обработка запроса (Runtime, target pipeline)

```
Вопрос пользователя
  ↓
maybe_expand_query  — для коротких/аббревиатурных (sqli, 403, RBAC)
  ↓                    LLM расширяет в развёрнутый запрос
hybrid_retrieve(query, TOP_K_HYBRID)
  ↓                    BM25 + Vector параллельно → RRF
  + (при expanded) повторный hybrid_retrieve и RRF-объединение
  ↓
rerank(query, candidates, TOP_K)
  ↓                    cross-encoder BAAI/bge-reranker-base
LLM-decision → MCP-tool?  (да/нет + tool + args)
  ↓
build_prompt + context (+ опц. MCP-result)
  ↓
ask_llm → Ollama (qwen3:0.6b)
  ↓
answer + sources + mcp_used + mcp_tool
```

# ✨ Ключевые возможности

- **Hybrid search**: BM25 + Vector с RRF — вектор для смысла, BM25 для точных совпадений
- **Cross-encoder reranker**: top-20 кандидатов реранжирует BAAI/bge-reranker-base
- **Query expansion**: LLM-переформулировка коротких/аббревиатурных запросов
- **Multi-format**: .md, .txt, .pdf, .docx
- **Source attribution**: ответ всегда с указанием источников и score
- **MCP-инструменты**: LLM по необходимости читает документ целиком
- **Нет внешних API**: всё локально

# ⚙️ Ключевые параметры конфигурации

```python
# Базовые
CHUNK_SIZE = 700
CHUNK_OVERLAP = 100
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
OLLAMA_MODEL = "qwen3:0.6b"
TOP_K = 5

# Advanced pipeline (спринт 01)
HYBRID_ENABLED = True
TOP_K_HYBRID = 20
RRF_K = 60
RERANK_ENABLED = True
RERANKER_MODEL = "BAAI/bge-reranker-base"
QUERY_EXPANSION_ENABLED = True
QUERY_EXPANSION_MIN_TOKENS = 4
```

Полная таблица и пояснения — `_docs/configuration.md`.

# 🎬 Демо — запуск

```bash
$ python main.py
```

Вывод:
```
🤖 Company Knowledge Base Assistant
Введите вопрос по документации. exit — выход.
```

# 🎬 Демо — короткий запрос (sqli)

```
❓ sqli
🪄 expanded → "SQL injection prevention guidelines"
🔍 Retrieved 5 chunks for query: "sqli"
  1. [score=0.6422] docs/security-policy.md#0
  ...

🤖 SQL injection (sqli) is mitigated through parameterised queries...
📚 Sources:
  • docs/security-policy.md
```

# 🎬 Демо — MCP list_documents

```
❓ list all documents in the docs directory
🔧 LLM decided to use MCP tool: list_documents with args: {}
✅ MCP tool returned result

🤖 Доступные документы:
  • onboarding-ru.md
  • security-policy.md
  • vacation-policy.md
```

# 🎬 Демо — MCP read_document

```
❓ Show me the full vacation policy
🔧 LLM decided to use MCP tool: read_document with args: {'file_path': 'docs/vacation-policy.md'}
✅ MCP tool returned result

🤖 [Полный текст политики отпусков…]
```

# 🔐 Безопасность — Local vs Cloud

**Cloud**: Данные → Интернет → Сервер
- ⚠️ Сетевая передача
- ⚠️ Внешнее хранилище
- ⚠️ Платная подписка

**Local**: Данные → Локальная система
- ✅ Нет передачи по сети
- ✅ Только локальное хранилище
- ✅ Без платных подписок

# 🔐 Гарантии реализации

- **MCP sandbox**: `read_document` защищён от path traversal (`Path.resolve()` + `startswith`)
- **Локальное хранение**: документы не покидают машину
- **Нет телеметрии**: никаких внешних вызовов, кроме Ollama (localhost)
- **Offline-ready**: работает без интернета после первой загрузки моделей

# ⚡ Performance Benchmarks

```
Index Building:    ~30s (one-time, на ~10 МБ документов)
Query Embedding:   ~50ms
FAISS Search:      ~5ms
BM25 Search:       <50ms (для 10k чанков)
Rerank (top-20):   ~200ms (CPU, BAAI/bge-reranker-base)
LLM Generation:    2-5s
Total Cycle:       2-7s (advanced pipeline)
```

# ⚡ Ускорение

```python
# Быстрее (отключить реранкер):
RERANK_ENABLED = False

# Меньше кандидатов на реранк:
TOP_K_HYBRID = 10

# Отключить LLM-expansion:
QUERY_EXPANSION_ENABLED = False
```

# 🚢 Развёртывание — одна машина

```
1. Установить Ollama и Python-зависимости
2. ollama pull qwen3:0.6b
3. Скопировать docs/ на сервер
4. python main.py build-index
5. Запустить в фоне:

$ nohup python main.py > log &
```

# 🚢 Масштабирование — вариант 1: FastAPI

```
[HTTP клиенты]                  [HTTP + Webllm]
       ↓                                  ↓
   [FastAPI]                          [FastAPI]
       ↓                                  ↓
[Ollama + FAISS + BM25]              [FAISS + BM25]
```

# 🚢 Масштабирование — вариант 2: распределённо

```
[Клиенты] → [Load Balancer]
              ↓
     [Несколько Retriever-воркеров]
```

# 🚢 Масштаб хранилища

```
Docs     Index      Build
10 MB    ~2 MB      ~30s
100 MB   ~20 MB     ~5min
1 GB     ~200 MB    ~30min
```

# 🔮 Что уже закрыто (спринт 01)

- ☑ Hybrid search (BM25 + Vector + RRF)
- ☑ Cross-encoder reranker (BAAI/bge-reranker-base)
- ☑ Query expansion (LLM rewrite)
- ☑ Score каждого чанка в verbose-выводе

# 🔮 Phase 2 — расширенные возможности (в roadmap)

- ☐ Web UI (Streamlit / Vite + React)
- ☐ HTTP API (FastAPI)
- ☐ Multi-language embeddings (multilingual-e5)
- ☐ Document versioning
- ☐ Fine-tuned embeddings

# 🔮 Phase 3 — advanced (в roadmap)

- ☐ История диалога (multi-turn)
- ☐ Multi-hop reasoning
- ☐ Метаданные-фильтры (`policies/` и т.д.)
- ☐ Feedback loop
- ☐ Analytics dashboard

# 🔮 Phase 4 — enterprise (в roadmap)

- ☐ Аутентификация пользователей
- ☐ Audit logging
- ☐ Role-based access
- ☐ LLM fine-tuning
- ☐ Cost analysis

Полный roadmap с приоритетами и рисками — `_docs/roadmap.md`.

# 📊 Почему это работает

| Аспект         | Традиционный поиск | Наш RAG (спринт 01)                  |
|----------------|--------------------|--------------------------------------|
| **Понимание**  | Ключевые слова     | Semantic + lexical (BM25) + rerank   |
| **Ответы**     | Документы          | Прямой ответ с источниками           |
| **Приватность**| Облако             | Локально                             |
| **Стоимость**  | Подписка           | One-time (оборудование)              |
| **Скорость**   | Медленно           | 2–7 с (всё локально)                 |

# ✅ Что вы получаете

- Локальную privacy-first базу знаний
- Advanced retrieval: hybrid + reranker + query expansion
- Интеллектуальный вызов MCP-инструментов
- Поддерживаемый Python-код с фактической документацией (`_docs/`, `_board/`)
- Основу для дальнейших enterprise-фичей

# 🙋 Быстрый старт

```bash
# 1. Собрать индекс
python main.py build-index

# 2. Интерактивный режим
python main.py

# 3. Посмотреть конфиг
cat src/config.py
```

# 📚 Ресурсы

- **Код**: `radif-ru/local-rag-mcp`
- **Документация проекта**: `_docs/` (русский)
- **Доска задач / спринты**: `_board/`
- **FAISS**: github.com/facebookresearch/faiss
- **rank_bm25**: github.com/dorianbrown/rank_bm25
- **Ollama**: ollama.ai
- **FastMCP**: github.com/jlowin/fastmcp
- **Transformers**: huggingface.co
