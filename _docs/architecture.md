# Архитектура

Документ описывает фактическую архитектуру кода в `src/` на момент написания. При расхождении с кодом приоритет у кода — обновляйте документ.

## 1. Общая схема

```
                     +-------------------+
                     |   Пользователь    |
                     +---------+---------+
                               |
                               | input() (stdin)
                               v
                     +---------+---------+
                     |     main.py       |
                     |     (CLI loop)    |
                     +---------+---------+
                               |
                               v
                     +---------+---------+
                     |  CompanyKBAssistant |
                     |   (assistant.py)    |
                     +---+---------+-----+
                         |         |
              .----------'         '----------.
              v                                v
   +----------+----------+            +--------+---------+
   |   RAG-конвейер      |            |    MCP-клиент    |
   |   (rag/query.py)    |            |   (mcp/client.py)|
   +----+--------+-------+            +--------+---------+
        |        |                             |
        v        v                             | stdin/stdout
  +-----+--+  +--+----------+        +---------+--------+
  | FAISS  |  |chunks.pkl   |        |    MCP-сервер    |
  |index   |  |(метаданные) |        | (mcp/server.py)  |
  +--------+  +-------------+        |    [subprocess]  |
                                     +---------+--------+
                                               |
                                               v
                                     +---------+--------+
                                     |     docs/        |
                                     | (исходные файлы) |
                                     +------------------+

         RAG → "контекст для LLM"
         MCP → "инструменты, которые может вызвать LLM"

                               +-------------------+
                               |   Ollama (REST)   |
                               | localhost:11434   |
                               +-------------------+
                  ↑ ВЫЗЫВАЕТСЯ из:
                  · rag/query.py::ask_llm           (генерация финального ответа)
                  · assistant.py::_llm_decide_mcp_usage (решение об MCP)
```

Ключевая идея: **RAG-результат всегда формирует контекст** для финального промпта. **MCP-вызов — опциональное обогащение** контекста, решение принимает сама LLM.

## 2. Принципы

- **Stateless процесса**: ассистент не хранит диалог между вопросами. Текущий вопрос обрабатывается независимо.
- **Один индекс на процесс**: FAISS-индекс и `chunks` загружаются в глобалы модуля `rag/query.py` при импорте (см. `current-state.md` про связанный нюанс).
- **MCP — отдельный процесс**: запускается ассистентом как `subprocess.Popen`, общается по stdio (JSON-RPC).
- **LLM-решение об инструменте**: `assistant.py` спрашивает LLM отдельным запросом «нужен ли MCP-инструмент?», парсит JSON-ответ, при необходимости вызывает инструмент.
- **Никаких сетевых вызовов кроме Ollama**: всё остальное — локальные файлы и subprocess.

## 3. Компоненты

### 3.1 CLI-точка входа — `src/main.py`

- Аргументы:
  - `python main.py build-index` — собрать индекс и завершиться.
  - `python main.py` (без аргументов) — интерактивный Q&A-цикл.
- Создаёт экземпляр `CompanyKBAssistant`, в цикле читает `input()`, вызывает `assistant.query(...)`, печатает ответ + источники + признак использования MCP.
- Обрабатывает `KeyboardInterrupt`, гарантирует `assistant.close()` в `finally`.

### 3.2 Оркестратор — `src/assistant.py::CompanyKBAssistant`

Главный класс, склеивает RAG и MCP. Поток метода `query(user_query, verbose)`:

1. Получает контексты от RAG: `retrieve(user_query)` → список словарей `{text, source, chunk_id}`.
2. Спрашивает LLM, нужен ли MCP-инструмент: `_llm_decide_mcp_usage(query, contexts)`. Передаёт LLM:
   - текст запроса,
   - сводку первых 3 чанков (источник + первые 200 символов),
   - описание доступных инструментов,
   - правила принятия решения,
   - формат ответа (строгий JSON: `{"use_mcp": bool, "tool": str|null, "args": {...}}`).
3. Если LLM решила использовать инструмент — вызывает `_call_mcp_tool(tool_name, tool_args)` через `MCPClient`.
4. Строит промпт через `build_prompt(query, contexts)`. При наличии MCP-результата дописывает блок `<additional_info_from_mcp_tool>...</additional_info_from_mcp_tool>`.
5. Вызывает `ask_llm(prompt)` (REST к Ollama).
6. Возвращает словарь `{answer, sources, mcp_used, mcp_tool}`.

Управление ресурсами: `__init__` инициализирует `MCPClient` (запуск subprocess); `close()` корректно завершает MCP-процесс.

### 3.3 RAG-конвейер — `src/rag/`

Документировано отдельно в [`rag-pipeline.md`](./rag-pipeline.md). Кратко:

| Модуль                  | Назначение                                                                                  |
|-------------------------|---------------------------------------------------------------------------------------------|
| `rag/ingest.py`         | Загрузка документов из `DOCUMENTS_DIR` (форматы: `.md`, `.txt`, `.pdf`, `.docx`).            |
| `rag/chunk.py`          | Токенайзер `tiktoken cl100k_base`, окно `CHUNK_SIZE` с перехлёстом `CHUNK_OVERLAP`.          |
| `rag/embed.py`          | `SentenceTransformer(EMBEDDING_MODEL)`.                                                     |
| `rag/build_index.py`    | Сборка FAISS-индекса (`IndexFlatIP` + L2-нормализация) и `chunks.pkl`.                       |
| `rag/query.py`          | Низкоуровневый семантический retrieve (`retrieve`), построение промпта, обращение к Ollama.  |
| `rag/search_engine.py`  | Фасад `search` (спринт 01): query expansion → hybrid BM25+vector с RRF → cross-encoder rerank. |

### 3.4 MCP-слой — `src/mcp/`

Документировано отдельно в [`mcp-tools.md`](./mcp-tools.md). Кратко:

- `mcp/server.py` — `FastMCP("doc-tools")`. Три инструмента: `read_document`, `list_documents`, `search_documents`. Запускается как stdio MCP-сервер.
- `mcp/client.py` — тонкая обёртка над `subprocess.Popen` + JSON-RPC по stdin/stdout. Методы `initialize()`, `call_tool(name, arguments)`, `close()`.

### 3.5 Конфигурация — `src/config.py`

Один модуль с константами уровня проекта. Подробно — в [`configuration.md`](./configuration.md). Параметры включают: каталог документов, размеры чанка/перехлёста, имя эмбеддинг-модели, путь индекса, URL Ollama, имя LLM-модели, `TOP_K`, плюс параметры Advanced Pipeline (спринт 01): `HYBRID_ENABLED`, `TOP_K_HYBRID`, `RRF_K`, `RERANK_ENABLED`, `RERANKER_MODEL`, `QUERY_EXPANSION_ENABLED`, `QUERY_EXPANSION_MIN_TOKENS`.

## 4. Поток обработки одного запроса

> С спринта 01 retrieval идёт через фасад `rag.search_engine.search`,
> который объединяет три стадии (query expansion → hybrid BM25+vector с RRF
> → cross-encoder rerank). Подробное описание стадий — в
> [`rag-pipeline.md`](./rag-pipeline.md) § 9.

```
                                                       ┌──────────────────────────┐
1) Пользователь вводит вопрос                          │  main.py: input()        │
                                                       └────────────┬─────────────┘
                                                                    │ query
                                                                    ▼
2) Assistant.query(user_query, verbose=True)         ┌──────────────────────────┐
                                                     │  assistant.py            │
                                                     └────────────┬─────────────┘
                                                                  │
                                ┌─────────────────────────────────┤
                                │ search(user_query, verbose)     │
                                ▼                                 │
3) Advanced retrieval                                             │
     · maybe_expand_query → (original, expanded?)                 │
     · hybrid_retrieve(original, TOP_K_HYBRID)   ← BM25 + Vector  │
       └── при наличии expanded — повторный hybrid_retrieve       │
           и RRF-объединение двух списков                         │
     · rerank(query, candidates, TOP_K)          ← cross-encoder  │
       (BAAI/bge-reranker-base, lazy load)                        │
     · возвращает top-K чанков с полем score                      │
                                ┌─────────────────────────────────┤
                                │ _llm_decide_mcp_usage(...)      │
                                ▼                                 │
4) Решение про MCP                                                │
     LLM получает: query + сводка контекстов + описания tools.    │
     Возвращает строгий JSON: {use_mcp, tool, args}.              │
                                                                  │
       use_mcp == false                                           │
       └────► пропускаем шаг 5                                    │
                                                                  │
       use_mcp == true                                            │
       ▼                                                          │
5) Вызов MCP-инструмента                                          │
     MCPClient.call_tool(tool, args) — JSON-RPC по stdio.         │
     Результат — строка, дописывается в промпт.                   │
                                                                  │
                                ┌─────────────────────────────────┤
                                │ build_prompt(query, contexts)   │
                                │ + блок MCP-результата           │
                                ▼                                 │
6) Финальный промпт                                               │
     <role>...</role><instructions>...</instructions>             │
     <context>{source + text}*</context>                          │
     <query>{query}</query>                                       │
     <additional_info_from_mcp_tool>{result}</additional_info_from_mcp_tool>?
                                                                  │
                                ┌─────────────────────────────────┤
                                │ ask_llm(prompt)                 │
                                ▼                                 │
7) Генерация ответа                                               │
     POST http://localhost:11434/api/generate                     │
     {"model": OLLAMA_MODEL, "prompt": ..., "stream": false}      │
                                                                  │
                                                                  ▼
8) Возврат пользователю             ┌──────────────────────────────┐
                                    │ {answer, sources, mcp_used,  │
                                    │  mcp_tool}                   │
                                    └──────────────────────────────┘
```

## 5. Обработка ошибок

| Сценарий                                          | Где ловится                              | Поведение                                                               |
|---------------------------------------------------|------------------------------------------|-------------------------------------------------------------------------|
| Индекс не найден / повреждён                      | `query.py::_ensure_index_exists`         | Попытка перестроить индекс через `build_index()`.                       |
| Документов нет в `DOCUMENTS_DIR`                  | `ingest.py::ingest_documents`            | Возвращает пустой список, `build_index` печатает ошибку и не пишет файлы. |
| Ollama недоступна / 4xx / 5xx                     | `query.py::ask_llm` (через `requests`)   | Исключение пробрасывается, ловится в `main.py` и печатается пользователю. |
| MCP-сервер не запустился                          | `assistant.py::_init_mcp`                | Печатается warning, `self.mcp = None`, ассистент работает без MCP.       |
| LLM вернула невалидный JSON в decision-промпте    | `assistant.py::_llm_decide_mcp_usage`    | `except Exception` → решение «не использовать MCP», пайплайн идёт дальше. |
| MCP-инструмент вернул ошибку                      | `assistant.py::_call_mcp_tool`           | Ошибка пакуется в строку и попадает в финальный промпт как «MCP-результат». |
| Любое необработанное исключение в `query`         | `main.py` (вокруг `assistant.query`)     | Печатается ошибка + traceback, цикл продолжается.                       |
| `KeyboardInterrupt` в CLI                         | `main.py`                                | Прощание + `assistant.close()`.                                         |

## 6. Конкурентность

- В одном процессе CLI. `MCPClient` имеет `threading.Lock` вокруг отправки/чтения сообщений на случай гипотетических многопоточных вызовов, но фактически вызовы линейные.
- FAISS-поиск и SentenceTransformers-инференс блокируют поток.
- Ollama-инференс — синхронный HTTP-вызов через `requests`.

Параллельная обработка нескольких запросов в текущей версии не предусмотрена. Для будущей FastAPI-обёртки потребуется либо отдельный воркер, либо переход на асинхронный HTTP-клиент (см. `roadmap.md`).

## 7. Точки расширения

- **Новый MCP-инструмент**: добавить функцию с декоратором `@mcp.tool` в `src/mcp/server.py`, описать её в `mcp-tools.md`, расширить `decision_prompt` в `assistant.py::_llm_decide_mcp_usage`.
- **Новый формат документа**: расширить `SUPPORTED_EXTENSIONS` и `load_document` в `src/rag/ingest.py`.
- **Альтернативный векторный индекс**: заменить `IndexFlatIP` на `IndexHNSWFlat` или внешнюю БД в `rag/build_index.py` + `rag/query.py`.
- **Веб-обёртка**: отдельный модуль (например, `src/web/`), вызывающий `CompanyKBAssistant`. Архитектура самого ассистента не меняется.

## 8. Что НЕ является частью архитектуры

- **БД и persistent state**: единственное persistent — `index.faiss` + `chunks.pkl` на диске.
- **Очереди / брокеры**: нет.
- **Облачные эмбеддинги/LLM**: запрещены принципом local-first.
- **Состояние диалога**: каждое сообщение — самостоятельный pipeline.
