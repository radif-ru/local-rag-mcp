# Технологический стек

## 1. Runtime

- **Python** — 3.10+ (рекомендуется 3.12). 3.10+ нужен для type hints в стиле `X | None` и нативной работы FastMCP.
- **OS** — Linux / macOS / WSL2. Основная среда разработки — Linux.

## 2. Машинное обучение / поиск

| Компонент              | Что и зачем                                                                            |
|------------------------|----------------------------------------------------------------------------------------|
| `sentence-transformers`| Эмбеддинги. По умолчанию модель `all-MiniLM-L6-v2` (384 dim, MiniLM, multilingual-light). |
| `faiss-cpu`            | Векторный индекс `IndexFlatIP` + L2-нормализация. CPU-only, без GPU-зависимостей.       |
| `numpy`                | Базовые операции с массивами эмбеддингов.                                              |
| `tiktoken`             | Токенизация для чанкования (`cl100k_base`). См. оговорку в `current-state.md`.         |

## 3. LLM-слой

- **Ollama** — локальный рантайм для LLM. REST API на `http://localhost:11434`.
- **Используемая модель**: значение из `OLLAMA_MODEL` в `src/config.py`. Текущее значение — `qwen3:0.6b` (быстрая модель для Q&A с коротким контекстом).
- **Клиенты**:
  - `requests` — синхронный HTTP, используется в `rag/query.py::ask_llm` (endpoint `/api/generate`).
  - `ollama` (Python SDK) — используется в `assistant.py::_llm_decide_mcp_usage` (endpoint `/api/chat`) для structured-decision промпта.

> Эти два клиента сосуществуют исторически. См. `current-state.md` § «Дублирование Ollama-клиента» — кандидат на унификацию.

## 4. MCP

- **FastMCP** (`fastmcp`) — фреймворк MCP-сервера на Python. Декоратор `@mcp.tool` для регистрации инструментов.
- Транспорт — **stdio** (стандартный для MCP). Сервер запускается как subprocess из ассистента.
- Клиент написан вручную в `src/mcp/client.py` (тонкая JSON-RPC обёртка). Сторонний MCP-SDK не используется.

## 5. Парсинг документов

| Формат   | Библиотека       | Где                           |
|----------|------------------|-------------------------------|
| `.md`    | `pathlib.Path.read_text` | `rag/ingest.py::load_document` |
| `.txt`   | `pathlib.Path.read_text` | `rag/ingest.py::load_document` |
| `.pdf`   | `pypdf`          | `rag/ingest.py::load_document` |
| `.docx`  | `python-docx`    | `rag/ingest.py::load_document` |

## 6. Терминальный UI

- **`rich`** — используется в `assistant.py::__main__` (запуск через `python -m assistant`) для красивой отрисовки markdown-ответа. В стандартном `python main.py` не задействован.

## 7. Зависимости (фактический `src/requirements.txt`)

```text
# Core dependencies
ollama>=0.1.0
sentence-transformers>=2.2.0
faiss-cpu>=1.7.4
numpy>=1.24.0
tiktoken>=0.5.0
requests>=2.31.0

# Document processing
pypdf>=3.17.0
python-docx>=1.1.0
rich>=14.2.0

# MCP
fastmcp>=0.1.0
```

Замечания:

- Версии указаны как «не ниже». Воспроизводимость на уровне minor может пострадать — кандидат на пиннинг (см. `roadmap.md`).
- Тестовых зависимостей (pytest и т. п.) нет — тестов в проекте сейчас тоже нет.

## 8. Менеджмент окружения

- В корне репозитория есть `.venv/` (стандартный `python -m venv`). Зависимости ставятся через `pip install -r src/requirements.txt`.
- Альтернативные менеджеры (poetry, uv, pdm) не используются.
- Файлы окружения — нет `.env` и нет загрузчика `.env`. Все параметры — в `src/config.py` как Python-константы.

## 9. Локальные требования окружения

Чтобы проект запустился:

1. **Python 3.10+** (`python --version`).
2. **Ollama** установлен и запущен:
   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ollama serve   # или systemd-юнит
   ollama pull qwen3:0.6b   # или другая модель из OLLAMA_MODEL
   ```
3. **Виртуальное окружение** активировано, зависимости установлены:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r src/requirements.txt
   ```
4. **Документы** для индексации лежат в `src/docs/` (или в каталоге, заданном `DOCUMENTS_DIR`).
5. (При первом запуске) **загрузка модели эмбеддингов** — `sentence-transformers` сам скачает `all-MiniLM-L6-v2` в `~/.cache/huggingface/`. Нужен интернет один раз.

## 10. Чего в стеке нет (и пока не планируется)

- БД (SQLite, Postgres, Redis) — единственное хранилище это `index.faiss` + `chunks.pkl` на диске.
- Очереди / брокеры (Celery, RQ, NATS).
- Web-фреймворки (FastAPI, Flask) — кандидаты в `roadmap.md` (Phase 2).
- Облачные LLM/embeddings (OpenAI, Anthropic, Cohere) — противоречит local-first.
- Docker / docker-compose — кандидат, но не текущая необходимость.
- Тестовый фреймворк (pytest) — кандидат, см. `roadmap.md`.
- CI (GitHub Actions и пр.) — нет.
- Логгер (`logging`) — пока используется `print(...)`. См. `current-state.md`.
