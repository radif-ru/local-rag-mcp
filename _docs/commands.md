# Команды и режимы запуска

Документ описывает CLI-команды и интерактивный режим Q&A.

## 1. Сводка

| Команда                         | Назначение                                                | Документ              |
|---------------------------------|-----------------------------------------------------------|-----------------------|
| `python main.py build-index`    | Собрать FAISS-индекс из документов в `DOCUMENTS_DIR`.     | См. §3                |
| `python main.py`                | Запустить интерактивный Q&A-цикл.                          | См. §4                |
| `python -m rag.build_index`     | То же, что `build-index`, без обёртки.                     | См. §3.2              |
| `python -m rag.query`           | Standalone Q&A без MCP (минимальный пайплайн).             | См. §5                |
| `python assistant.py`           | Интерактивный Q&A с rich-форматированием markdown.         | См. §6                |
| `python mcp/server.py`          | Запуск MCP-сервера в stdio-режиме (для отладки).           | См. §7                |

Все команды запускаются из каталога **`src/`** при активированном виртуальном окружении.

## 2. Подготовка окружения (один раз)

```bash
# 1. Виртуальное окружение
python -m venv .venv
source .venv/bin/activate

# 2. Зависимости
pip install -r src/requirements.txt

# 3. Ollama
ollama serve &              # если ещё не запущен
ollama pull qwen3:0.6b      # модель из OLLAMA_MODEL

# 4. Документы
mkdir -p src/docs
# скопировать .md/.txt/.pdf/.docx в src/docs/
```

## 3. `build-index` — сборка FAISS-индекса

### 3.1 Через `main.py`

```bash
cd src
python main.py build-index
```

Выполняет: `ingest_documents()` → `chunk_documents()` → `embed_chunks()` → создание `IndexFlatIP` → сохранение `index.faiss` и `chunks.pkl` в `src/`.

Артефакты:

```
src/index.faiss     ← бинарный FAISS-индекс
src/chunks.pkl      ← pickle со списком чанков и метаданных
```

Вывод примерно такой:

```
📥 Loading documents...
Loading: src/docs/policy.md
Loading: src/docs/security.pdf
✂️ Chunking...
🧠 Generating embeddings...
Batches: 100%|████████████████| 12/12 [00:08<00:00,  1.45it/s]
📦 Creating FAISS index...
💾 Saving...
✅ Indexing complete: 87 chunks indexed
   Index saved to: /path/to/src/index.faiss
   Chunks saved to: /path/to/src/chunks.pkl
```

### 3.2 Напрямую через модуль

```bash
cd src
python -m rag.build_index
```

Эквивалентно. Используется, если нужно вызвать сборку из-под отладчика или изолированно.

### 3.3 Когда нужна пересборка

- Добавили / изменили / удалили файлы в `DOCUMENTS_DIR`.
- Сменили `CHUNK_SIZE`, `CHUNK_OVERLAP`, `EMBEDDING_MODEL`.
- Сменили версию `sentence-transformers` (изменения в самой модели).

См. также `rag-pipeline.md` § «Пересборка индекса».

### 3.4 Поведение при отсутствии документов

```
📥 Loading documents...
❌ No documents found. Please add documents to the docs directory.
```

Сборка завершается, артефакты **не перезаписываются**. Если индекс уже был — он остаётся прежним.

## 4. Интерактивный Q&A — `python main.py`

```bash
cd src
python main.py
```

Цикл:

1. Печатает баннер.
2. Ждёт ввода `❓ Question: ...`.
3. Извлекает контексты из FAISS (или строит индекс автоматически, если его нет).
4. Спрашивает LLM, нужен ли MCP-инструмент.
5. При необходимости — вызывает MCP.
6. Генерирует ответ через Ollama.
7. Печатает ответ + источники + признак использования MCP.

### Команды выхода

- `exit`, `quit`, `q` — корректный выход (закрывает MCP-subprocess).
- `Ctrl+C` — также корректный, через `KeyboardInterrupt`.

### Пример сессии

```
============================================================
🤖 Company Knowledge Base Assistant
============================================================

Ask questions about company policies, procedures, and documentation.
Type 'exit' or 'quit' to stop

❓ Question: What are the company values?

────────────────────────────────────────────────────────────
🤖 Answer:

📚 Retrieved 5 relevant chunks from knowledge base
The company values include innovation, integrity, and collaboration...

📚 Sources:
  • src/docs/Loan Rangers Team.md
  • src/docs/Info Security.md

────────────────────────────────────────────────────────────

❓ Question: List all documents

────────────────────────────────────────────────────────────
🤖 Answer:

📚 Retrieved 5 relevant chunks from knowledge base
🔧 LLM decided to use MCP tool: list_documents with args: {}
✅ MCP tool returned result (length: 124 chars)
Available documents:
- Loan Rangers Team.md
- Information Security.md
- Services.md

🔧 Used MCP tool: list_documents
────────────────────────────────────────────────────────────
```

### Что происходит «под капотом»

См. `architecture.md` § «Поток обработки одного запроса».

### Что выводится при `verbose=True` (текущий по умолчанию режим в `main.py`)

- `📚 Retrieved N relevant chunks from knowledge base` — после `retrieve()`.
- `🔧 LLM decided to use MCP tool: <name> with args: {...}` — если LLM решила использовать MCP.
- `✅ MCP tool returned result (length: N chars)` — после успешного вызова.
- В случае ошибки в pipeline — `❌ Error: <message>` + traceback.

## 5. `python -m rag.query` — standalone RAG без MCP

```bash
cd src
python -m rag.query
```

Минимальный цикл: только RAG (`retrieve` + `build_prompt` + `ask_llm`), без `assistant.py` и без MCP. Полезно для отладки качества RAG в отрыве от decision-промпта.

```
❓ Question: What is the vacation policy?

🤖 Answer:

According to the vacation policy document...

📚 Sources:
  - src/docs/vacation-policy.md
```

## 6. `python assistant.py` — Q&A с rich-выводом

Альтернативная точка входа, отличается от `main.py` тем, что использует `rich.Console + Markdown` для красивого рендера markdown-ответа. Логика идентична.

```bash
cd src
python assistant.py
```

> **Дублирование с `main.py`**: текущий `__main__` блок в `assistant.py` повторяет цикл из `main.py`. Кандидат на унификацию — см. `current-state.md`.

## 7. `python mcp/server.py` — отладка MCP-сервера

Запуск MCP-сервера напрямую (для ручной отладки JSON-RPC):

```bash
cd src
python mcp/server.py
```

Сервер ждёт JSON-RPC сообщения на stdin и отвечает на stdout. Пример вручную:

```json
{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "manual", "version": "1.0"}}}
```

Лучше использовать `MCPClient` для тестов (см. `mcp-tools.md` § «Тестирование MCP вручную»).

## 8. Частые ошибки запуска и что делать

| Симптом                                                  | Причина                                                       | Решение                                                                  |
|----------------------------------------------------------|---------------------------------------------------------------|--------------------------------------------------------------------------|
| `ModuleNotFoundError: No module named 'config'`          | Запуск не из `src/`.                                          | `cd src && python main.py ...`                                           |
| `❌ No documents found.`                                  | `DOCUMENTS_DIR` пуст или указывает не туда.                   | Положить файлы в `src/docs/` или поправить `DOCUMENTS_DIR` в `config.py`. |
| `ConnectionError: HTTPConnectionPool(host='localhost', port=11434)` | Ollama не запущена.                                           | `ollama serve &`                                                         |
| `404 Not Found` от Ollama                                | Модель из `OLLAMA_MODEL` не установлена.                      | `ollama pull <model>`                                                    |
| `RuntimeError: <model> not found in HuggingFace cache`   | Первый запуск без интернета.                                  | Один раз запустить с интернетом для скачивания эмбеддинг-модели.         |
| Зависание после ввода вопроса                            | Возможна проблема с MCP-сервером или Ollama.                  | `Ctrl+C`, проверить логи Ollama (`ollama logs`).                         |
| `pickle.UnpicklingError` при чтении `chunks.pkl`         | Артефакт сломан или собран другой версией.                    | Удалить `index.faiss` и `chunks.pkl`, пересобрать `build-index`.         |

См. также `current-state.md` § «Известные проблемы».
