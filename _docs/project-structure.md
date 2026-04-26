# Структура проекта

Документ описывает фактическую структуру репозитория и назначение модулей.

## 1. Дерево репозитория

```
local-rag-mcp/
├── .gitignore                # Корневой gitignore (Python + ML + IDE + локальные настройки)
├── .venv/                    # Виртуальное окружение (в .gitignore)
├── .idea/                    # PyCharm/JetBrains IDE (в .gitignore)
├── CLAUDE.md                 # Поведенческие гайдлайны LLM-агента (общие)
├── README.md                 # Пользовательское описание проекта (фичи, демо, бенчмарки)
│
├── _docs/                    # Проектная документация (этот каталог)
│   ├── README.md             # Индекс документации
│   ├── project.md            # Что и зачем, философия
│   ├── architecture.md       # Архитектура, потоки данных
│   ├── stack.md              # Версии, зависимости
│   ├── project-structure.md  # Этот файл
│   ├── rag-pipeline.md       # Детали RAG-конвейера
│   ├── mcp-tools.md          # MCP-инструменты и протокол
│   ├── configuration.md      # Все параметры config.py
│   ├── commands.md           # CLI-команды
│   ├── instructions.md       # Правила разработки
│   ├── current-state.md      # Текущее состояние, известные проблемы
│   ├── roadmap.md            # План развития
│   ├── legacy.md             # Указатель на технический долг (ссылки в current-state.md § 2 и roadmap.md)
│   └── links.md              # Каталог ссылок на внешнюю документацию
│
├── _board/                   # Доска процесса для LLM-агента
│   ├── README.md             # Назначение
│   ├── process.md            # Алгоритм работы над одной задачей
│   ├── plan.md               # План задач (заполняется по ТЗ)
│   └── progress.txt          # Ad-hoc заметки о прогрессе
│
└── src/                      # Исходный код приложения
    ├── .gitignore            # Локальный gitignore (FAISS-индекс, .pkl, кэш)
    ├── README.md             # README уровня src/ (быстрый старт)
    ├── COMMANDS.md           # Справочник команд для запуска
    ├── requirements.txt      # Python-зависимости
    ├── config.py             # Единая точка конфигурации (константы)
    ├── main.py               # CLI-точка входа
    ├── assistant.py          # Главный класс CompanyKBAssistant (RAG + MCP)
    │
    ├── rag/                  # RAG-конвейер
    │   ├── __init__.py
    │   ├── ingest.py         # Загрузка документов (.md/.txt/.pdf/.docx)
    │   ├── chunk.py          # Чанкование (tiktoken cl100k_base)
    │   ├── embed.py          # Эмбеддинги (SentenceTransformer)
    │   ├── build_index.py    # Сборка FAISS-индекса
    │   └── query.py          # Поиск, построение промпта, запрос к Ollama
    │
    ├── mcp/                  # MCP-слой
    │   ├── __init__.py
    │   ├── server.py         # FastMCP-сервер с инструментами (read/list/search)
    │   └── client.py         # JSON-RPC stdio клиент
    │
    ├── docs/                 # База документов для индексации (по умолчанию)
    │   └── .gitkeep
    │
    ├── index.faiss           # Сериализованный FAISS-индекс (в .gitignore)
    └── chunks.pkl            # Метаданные чанков (в .gitignore)
```

## 2. Назначение ключевых файлов

| Путь                              | Ответственность                                                                                |
|-----------------------------------|------------------------------------------------------------------------------------------------|
| `CLAUDE.md`                       | Поведенческие правила LLM-агента (think before coding, simplicity, surgical changes).          |
| `README.md` (корень)              | Высокоуровневое описание для пользователей и stakeholder'ов.                                   |
| `_docs/README.md`                 | Индекс проектной документации.                                                                  |
| `_board/plan.md`                  | План задач со статусами `ToDo`/`Progress`/`Done`.                                              |
| `_board/process.md`               | Универсальный алгоритм выполнения задачи.                                                       |
| `src/config.py`                   | Все настройки — пути, размеры чанков, имя модели, URL Ollama, TOP_K.                            |
| `src/main.py`                     | Точка входа CLI: режимы `build-index` и интерактивный Q&A.                                     |
| `src/assistant.py`                | Класс `CompanyKBAssistant`: метод `query(...)`, оркестрация RAG + MCP + LLM.                    |
| `src/rag/ingest.py`               | `ingest_documents()`, `load_document(path)` для каждого формата.                                |
| `src/rag/chunk.py`                | `chunk_text(text)`, `chunk_documents(docs)` — токенайзер `cl100k_base`.                         |
| `src/rag/embed.py`                | `embed_chunks(chunks)` — `SentenceTransformer.encode`.                                          |
| `src/rag/build_index.py`          | `build_index()` — полный цикл ingest → chunk → embed → index → save.                            |
| `src/rag/query.py`                | `retrieve(query)`, `build_prompt(query, contexts)`, `ask_llm(prompt)`, `ask(query)`.            |
| `src/mcp/server.py`               | `FastMCP("doc-tools")` + три `@mcp.tool`: `read_document`, `list_documents`, `search_documents`. |
| `src/mcp/client.py`               | Класс `MCPClient`: `initialize()`, `call_tool(name, arguments)`, `close()`.                     |
| `src/docs/`                       | Каталог исходных документов для индексации (имя по `DOCUMENTS_DIR`).                            |
| `src/index.faiss`                 | Сериализованный FAISS-индекс (артефакт сборки).                                                |
| `src/chunks.pkl`                  | Pickle-файл со списком чанков и их метаданными (артефакт сборки).                              |

## 3. Принципы организации

### 3.1 Слои не протекают в одну сторону

```
main.py  →  assistant.py  →  rag/* + mcp/*  →  config.py
```

- `main.py` ничего не знает о FAISS, эмбеддингах и MCP-протоколе.
- `assistant.py` знает про RAG как «дай мне контексты» и про MCP как «вызови инструмент». Он — единственный, кто видит обе подсистемы.
- `rag/*` ничего не знает про MCP, и наоборот.
- `config.py` импортируется всеми и не импортирует ничего проектного.

### 3.2 Каждый модуль самодостаточен в импорте

Модули `rag/*` и `mcp/server.py` для импорта `config` добавляют родительский каталог в `sys.path`:

```python
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import ...
```

Это позволяет запускать модули как `python -m rag.build_index` и как часть пакета. **Не повторяйте этот паттерн в новых модулях** — лучше превратить `src/` в нормальный пакет (см. `roadmap.md`).

### 3.3 Артефакты сборки лежат рядом с кодом

`src/index.faiss` и `src/chunks.pkl` сохраняются по путям из `config.py` относительно `src/`. Это упрощает запуск, но снижает гибкость для деплоя. См. `roadmap.md` про вынос в отдельный `data/`.

## 4. Что должно быть в `.gitignore`

Корневой `.gitignore` уже содержит расширенный список (Python, виртуальные окружения, IDE, OS-файлы, FAISS, pickle, ключи, логи). Локальный `src/.gitignore` дублирует ключевые правила (FAISS, pkl, кэш, IDE, env-файлы).

Минимально критичное:

```gitignore
# Python
__pycache__/
*.py[cod]
.venv/
venv/

# IDE
.idea/
.vscode/

# Артефакты сборки индекса
*.faiss
index.faiss
*.pkl
chunks.pkl

# Содержимое базы знаний (документы могут быть приватными)
src/docs/*.md
src/docs/*.txt
src/docs/*.pdf
src/docs/*.docx
!src/docs/.gitkeep

# Локальные конфиги, секреты
.env
.env.*
config.local.py
```

## 5. Правила добавления новых файлов

- **Код** → `src/<подсистема>/` или новая подсистема `src/<имя>/__init__.py`. Перед созданием новой подсистемы проверить, нет ли подходящей.
- **Документация** → `_docs/<имя>.md` (kebab-case, на русском). Обновить `_docs/README.md` (раздел «Навигация»).
- **Задачи и спринты** → `_board/plan.md`. Большие задачи вынести в `_board/tasks/<id>_<short-name>.md` (см. `_board/README.md`).
- **Тесты** (когда появятся) → `tests/` в корне, зеркалирование структуры `src/`.
- **Сценарии запуска / инфраструктура** → `scripts/` или `Makefile` в корне.

## 6. Что НЕ должно появляться в репозитории

- Реальные документы пользователя в `src/docs/` (если они приватные).
- Артефакты сборки индекса (`*.faiss`, `*.pkl`).
- Кеш моделей (`~/.cache/huggingface/`, `~/.ollama/`).
- Логи запусков.
- Локальные конфиги с путями/секретами (использовать `config.local.py`, добавленный в `.gitignore`).
