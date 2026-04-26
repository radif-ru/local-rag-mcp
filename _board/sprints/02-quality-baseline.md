# Спринт 02. Quality Baseline (документация, логирование, обработка ошибок, тесты)

- **Статус спринта:** Active
- **Ветка:** `feature/quality-baseline`
- **Дата старта:** 2026-04-26
- **Дата закрытия:** —
- **Связанные документы:**
  - `../../_docs/current-state.md` § 2.5 (таймауты), § 2.6 (stderr MCP), § 2.9 (тесты), § 2.10 (логирование), § 2.14 (pickle)
  - `../../_docs/instructions.md` § 3.3 (логирование), § 6 (обработка ошибок), § 8 (тесты)
  - `../../_docs/roadmap.md` Phase 1 (корректность и надёжность), Phase 2 (тесты и инфраструктура)
  - `../../_board/README.md` § «Связи с другими артефактами», § «Правила»
  - `../../_board/plan.md` § «Правила работы со спринтами»

## 1. Цель спринта

Закрыть базовые «инфраструктурные» долги, без которых дальнейшие фичи будут хрупкими:

1. **Документация и правила процесса** — добавить недостающие справочные документы (`links.md`, `legacy.md`) и закрепить явное правило «новый спринт открывается в новой ветке», чтобы это не было устной договорённостью.
2. **Логирование** — убрать `print(...)` из кодовой базы (за исключением осознанного «UI-print» в CLI), завести единую конфигурацию `logging`, вынести её в отдельный конфигурационный модуль/файл.
3. **Обработка ошибок** — закрыть точки, где сейчас исключение либо повисает (нет таймаутов), либо проглатывается без диагностики, либо валится traceback'ом наружу пользователю. Сводное правило: **на верхнем уровне CLI не должно быть необработанных исключений.**
4. **Тесты** — поднять `pytest`-инфраструктуру и покрыть базовыми тестами критические подсистемы: `rag/chunk`, `rag/query`, `rag/search_engine`, `mcp/server`, `assistant.py`.

## 2. Скоуп

### В скоупе

- Новый документ `_docs/links.md` (внешние ссылки на документацию используемых библиотек/моделей/протоколов).
- Новый документ `_docs/legacy.md` — **тонкий указатель** на разделы `_docs/current-state.md` § 2 и `_docs/roadmap.md`, **без дублирования содержимого**.
- Правило «каждый новый спринт открывается в отдельной ветке `feature/<short-name>`» — формализовано в `_board/plan.md` и `_docs/instructions.md`.
- Единая `logging`-инфраструктура (конфиг + `get_logger(name)`-хелпер). Конфигурационный файл логов — отдельный модуль или `logging.conf`.
- Миграция `print(...)` → `logger.*` во всех модулях `src/` (кроме явного пользовательского вывода в CLI-цикле).
- Закрытие точек отказа из `current-state.md` § 2.5 (таймауты `requests.post` и `MCPClient._send`), § 2.6 (stderr MCP-сервера).
- Унификация обработки ошибок в `main.py` и `assistant.py`: пользователю — короткое сообщение, в лог — полный traceback.
- `pytest` + `pytest-mock` + базовая директория `tests/` с зеркалированием `src/`.
- Тесты на критические модули (см. § 6).
- Обновление `_docs/`: `configuration.md` (новые параметры логирования), `current-state.md` (перенос закрытых записей в § 6 «История закрытий»), `instructions.md` (актуализация § 3.3, § 8).

### Не в скоупе

- CI (GitHub Actions, lint в pipeline) — отдельный кандидат, см. `_docs/roadmap.md` Phase 2.
- Замена `pickle` на JSON/parquet (`current-state.md` § 2.14) — отдельный кандидат, Phase 3.
- Превращение `src/` в нормальный пакет (`pyproject.toml`) — отдельный кандидат, Phase 3.
- Унификация Ollama-клиентов (requests vs ollama-sdk) — отдельный кандидат, Phase 3.
- Удаление мёртвого `else` в `ingest.py` (`current-state.md` § 2.1) — может попасть в этот спринт «попутно» только в рамках задачи на тесты `rag/ingest.py`, иначе — отдельной задачей.
- Покрытие `rag/embed.py`, `rag/build_index.py` тестами с реальной моделью — слишком долго на CPU; используем моки.
- Изменение MCP-инструментов и контракта `CompanyKBAssistant.query`.

## 3. Acceptance criteria спринта

Спринт считается закрытым, когда выполнены **все** условия:

- [ ] Все коммиты спринта — в ветке `feature/quality-baseline`, ветка запушена и (при возможности) смержена в `main`.
- [ ] Существуют файлы `_docs/links.md` и `_docs/legacy.md`. Оба упомянуты в `_docs/README.md` § «Навигация» и в дереве `_docs/project-structure.md` § 1.
- [ ] В `_board/plan.md` § «Правила работы со спринтами» **явно** зафиксировано: «новый спринт открывается в новой ветке `feature/<short-name>`». То же — в `_docs/instructions.md` § 4.1.
- [ ] В `src/` не осталось `print(...)` за пределами явного «UI-print» в `src/main.py`-цикле и `src/assistant.py::__main__` (rich-вывод). Все остальные `print` заменены на `logger.*`.
- [ ] Существует единый `logging`-конфиг (отдельный модуль `src/log_config.py` либо `logging.conf` + хелпер). Уровень настраивается через env-переменную (например, `KB_LOG_LEVEL`).
- [ ] `requests.post` в `rag/query.py::ask_llm` имеет `timeout=`. `MCPClient._send` имеет таймаут чтения. Stderr MCP-сервера явно потребляется (`DEVNULL` или logger-поток).
- [ ] В `src/main.py` и `src/assistant.py` **нет необработанных исключений**, всплывающих к пользователю traceback'ом. Любая ошибка → короткое сообщение пользователю + полный stacktrace в лог.
- [ ] `pytest -q` зелёный. Минимальный набор тестов покрывает: `rag/chunk`, `rag/query::retrieve`, `rag/search_engine` (`hybrid_retrieve`, `rerank`, `maybe_expand_query` — внешние вызовы замоканы), `mcp/server` (3 инструмента), `assistant._llm_decide_mcp_usage` (с моком LLM).
- [ ] Обновлены: `_docs/configuration.md` (новые env/параметры логирования), `_docs/instructions.md` § 3.3 (теперь `logging` обязателен), § 8 (актуальный pytest-сетап), `_docs/current-state.md` § 6 (история закрытий).
- [ ] Все задачи спринта — в статусе `Done`, сводная таблица актуальна.

---

## 4. Этап 1. Документация и правила процесса

Цель этапа — закрепить договорённости и добавить недостающие справочные документы. Все задачи — чисто документация, без правок кода.

### Задача 2.1.1. Создать `_docs/links.md` и подключить к навигации

- **Статус:** Progress
- **Приоритет:** medium
- **Объём:** S
- **Зависит от:** —
- **Связанные документы:** `_docs/README.md`, `_docs/stack.md`, `_docs/project-structure.md`.
- **Затрагиваемые файлы:** `_docs/links.md` (новый), `_docs/README.md`, `_docs/project-structure.md`.

#### Описание

Создать `_docs/links.md` — каталог ссылок на внешнюю документацию используемых в проекте библиотек, моделей и протоколов. Цель — не искать одно и то же повторно при работе над задачей.

Минимальный набор ссылок (брать из `_docs/stack.md` + спринта 01):

- LLM-слой: Ollama, Ollama REST API (`/api/generate`, `/api/chat`), Ollama Python SDK, модель `qwen3:0.6b`.
- Эмбеддинги/поиск: `sentence-transformers`, модели `all-MiniLM-L6-v2` и `BAAI/bge-reranker-base`, FAISS, `numpy`, `tiktoken (cl100k_base)`, `rank_bm25`, статья по RRF (Cormack & Clarke, 2009).
- MCP: спецификация Model Context Protocol, FastMCP, JSON-RPC 2.0.
- Парсинг документов: `pypdf`, `python-docx`.
- UI: `rich`.
- Стандарты разработки: Conventional Commits, Python typing.

К каждой строке — пометка «зачем нужно в проекте» (модуль/функция/константа `config.py`).

После создания — обновить:

1. `_docs/README.md` § «Навигация» — добавить пункт «Внешние ссылки → `links.md`».
2. `_docs/project-structure.md` § 1 (дерево репозитория) — добавить файл в блок `_docs/`.

#### Definition of Done

- [ ] `_docs/links.md` существует, ссылается на >= 12 внешних ресурсов, к каждому — короткая пометка про использование в проекте.
- [ ] `_docs/README.md` упоминает `links.md` в разделе «Навигация».
- [ ] `_docs/project-structure.md` § 1 показывает `links.md` в дереве `_docs/`.
- [ ] Smoke: все ссылки — валидные https-URL (визуальная проверка, без массового curl).

---

### Задача 2.1.2. Создать `_docs/legacy.md` (тонкий указатель)

- **Статус:** ToDo
- **Приоритет:** medium
- **Объём:** S
- **Зависит от:** Задача 2.1.1.
- **Связанные документы:** `_docs/current-state.md` § 2, `_docs/roadmap.md`, `_board/README.md`.
- **Затрагиваемые файлы:** `_docs/legacy.md` (новый), `_docs/README.md`, `_docs/project-structure.md`, `_board/README.md`.

#### Описание

Содержательный список «костылей и того, что можно улучшить» уже есть в `_docs/current-state.md` § 2 («Известные проблемы (баги, недочёты, легаси)») и `_docs/roadmap.md` (по фазам). Создавать дубль запрещено правилом `_board/README.md` § «Что НЕ делается на доске» («Не дублируем содержимое `_docs/` — ссылаемся»).

Поэтому `_docs/legacy.md` — это **тонкий указатель** (1 экран):

1. Короткое описание роли документа: «единая точка входа в перечень технического долга».
2. Список ссылок на конкретные подсекции `_docs/current-state.md` § 2.1 — § 2.14 (по 1 строке на пункт с кратким названием).
3. Список ссылок на разделы `_docs/roadmap.md` (Phase 1 — Phase 7) с одной строкой про цель каждой фазы.
4. Правило обновления: «новые костыли — записываются в `current-state.md` § 2 (по шаблону § 5 этого документа), кандидаты на улучшение — в `roadmap.md`. Этот файл (`legacy.md`) трогается только при изменении набора секций в источниках».

После создания — обновить:

1. `_docs/README.md` § «Навигация» — добавить «Легаси и технический долг → `legacy.md`».
2. `_docs/project-structure.md` § 1 — добавить в дерево.
3. `_board/README.md` § «Связи с другими артефактами» — добавить отдельным пунктом «Сводный указатель легаси/долга — `_docs/legacy.md`».

#### Definition of Done

- [ ] `_docs/legacy.md` существует, занимает < 100 строк, **не дублирует** содержимое `current-state.md` или `roadmap.md` (только ссылки + краткие названия).
- [ ] Все 14 подсекций § 2.X из `current-state.md` перечислены ссылками. Все 7 фаз из `roadmap.md` — тоже.
- [ ] `_docs/README.md`, `_docs/project-structure.md`, `_board/README.md` обновлены.
- [ ] Smoke: открыть `_docs/legacy.md` и кликнуть по 3 ссылкам — все ведут на существующие разделы (визуальная проверка).

---

### Задача 2.1.3. Закрепить правило «новый спринт = новая ветка»

- **Статус:** ToDo
- **Приоритет:** high
- **Объём:** XS
- **Зависит от:** —
- **Связанные документы:** `_board/plan.md` § «Правила работы со спринтами», `_docs/instructions.md` § 4.1, `_board/README.md` § «Правила».
- **Затрагиваемые файлы:** `_board/plan.md`, `_docs/instructions.md`, `_board/README.md`.

#### Описание

Сейчас правило «коммиты спринта идут в его рабочую ветку» зафиксировано **только косвенно** (`_board/plan.md` § «Правила работы с задачами», п.5: «коммиты спринта идут в его рабочую ветку, указанную в шапке файла спринта»). Это не то же самое, что «**каждый новый спринт обязательно открывается в новой ветке от `main`**».

Нужно явно дописать правило в трёх местах:

1. `_board/plan.md` § «Правила работы со спринтами» — новый пункт:
   > «Каждый новый спринт открывается в отдельной ветке `feature/<short-name>` от актуальной `main`. Имя ветки фиксируется в шапке файла спринта и в индексе спринтов. Коммиты спринта идут только в эту ветку; merge в `main` — после закрытия спринта».
2. `_docs/instructions.md` § 4.1 «Ветки и коммиты» — добавить пункт «Новый спринт открывается в новой ветке (см. `_board/plan.md`)».
3. `_board/README.md` § «Правила» — добавить пункт «Новый спринт = новая ветка».

#### Definition of Done

- [ ] В `_board/plan.md` § «Правила работы со спринтами» есть явный пункт про ветку нового спринта.
- [ ] В `_docs/instructions.md` § 4.1 есть отсылка к этому правилу.
- [ ] В `_board/README.md` § «Правила» есть пункт про ветку.
- [ ] Все три формулировки согласованы (одинаковая суть, не противоречат друг другу).

---

## 5. Этап 2. Логирование

Цель этапа — заменить `print(...)` на `logging`, оставить «UI-print» только в CLI-обвязке. Ставится первым из код-этапов, чтобы дальнейшие задачи (обработка ошибок, тесты) уже использовали logger.

### Задача 2.2.1. Логгер-инфраструктура и конфигурационный файл

- **Статус:** ToDo
- **Приоритет:** high
- **Объём:** M
- **Зависит от:** Задача 2.1.3.
- **Связанные документы:** `_docs/configuration.md`, `_docs/instructions.md` § 3.3.
- **Затрагиваемые файлы:** `src/log_config.py` (новый), `src/config.py`, `_docs/configuration.md`, `_docs/instructions.md`.

#### Описание

Создать `src/log_config.py` — единая точка конфигурации `logging` для проекта:

1. Функция `setup_logging(level: str | None = None) -> None`: настраивает корневой logger.
2. Функция-хелпер `get_logger(name: str) -> logging.Logger`: тонкая обёртка `logging.getLogger(name)`.
3. Формат: `%(asctime)s [%(levelname)s] %(name)s: %(message)s` (или эквивалентный, на усмотрение исполнителя).
4. Уровень по умолчанию — `INFO`. Переопределение через env `KB_LOG_LEVEL` (`DEBUG` / `INFO` / `WARNING` / `ERROR`).
5. Минимум два handler'а: stdout (для CLI-наблюдателя) и файл `logs/app.log` (с ротацией: `RotatingFileHandler`, 1 MB × 3 файла — стартовые цифры).
6. Каталог `logs/` — добавить в корневой `.gitignore` (если ещё не покрыт глобом).

В `src/config.py` добавить только новые константы для путей лог-файла (`LOG_DIR`, `LOG_FILE`), без всякой оверинженеринговой настройки. Сложная конфигурация — внутри `log_config.py`.

`setup_logging()` вызывается **один раз** на процесс из точек входа: `src/main.py`, `src/mcp/server.py`, при необходимости — из `src/assistant.py::__main__`.

#### Definition of Done

- [ ] `src/log_config.py` создан, импортируется без ошибок.
- [ ] `python -c "from log_config import get_logger, setup_logging; setup_logging(); get_logger('test').info('hello')"` (из `src/`) — выводит строку формата в stdout и пишет в `logs/app.log`.
- [ ] Уровень переопределяется через `KB_LOG_LEVEL=DEBUG ... && python ...`.
- [ ] `logs/` в `.gitignore` (корневой).
- [ ] `_docs/configuration.md` § 1 дополнен: `KB_LOG_LEVEL`, `LOG_DIR`, `LOG_FILE`.
- [ ] `_docs/instructions.md` § 3.3 переписан: «`print(...)` запрещён в новом коде, использовать `logging` через `get_logger(__name__)`. Исключение — явный пользовательский вывод в CLI».

---

### Задача 2.2.2. Перевод `rag/*` и `mcp/*` на logger

- **Статус:** ToDo
- **Приоритет:** high
- **Объём:** M
- **Зависит от:** Задача 2.2.1.
- **Связанные документы:** `_docs/rag-pipeline.md`, `_docs/mcp-tools.md`.
- **Затрагиваемые файлы:** `src/rag/ingest.py`, `src/rag/chunk.py`, `src/rag/embed.py`, `src/rag/build_index.py`, `src/rag/query.py`, `src/rag/search_engine.py`, `src/mcp/server.py`, `src/mcp/client.py`.

#### Описание

Заменить все `print(...)` в указанных файлах на `logger = get_logger(__name__); logger.info/debug/warning/error(...)`. Уровень выбирать осмысленно:

- DEBUG — детали (число чанков, размеры эмбеддинг-матриц, RRF-баланс).
- INFO — события жизненного цикла (старт сборки индекса, число загруженных документов, готовность модели).
- WARNING — деградация (cross-encoder не загрузился — fallback, LLM вернула пустой expansion и т.д.).
- ERROR — реальные сбои (Ollama 5xx, MCP не стартовал, файл не открыт).

`mcp/server.py` — отдельный процесс, поэтому в нём в начале явный `setup_logging()`. Учесть, что **в stdout MCP-сервера ничего нельзя писать** (там JSON-RPC). Logger в MCP-сервере должен идти в **stderr** или **только в файл**, иначе сломается транспорт. Реализация — на исполнителе, но тест должен это проверять.

#### Definition of Done

- [ ] В `src/rag/*.py` и `src/mcp/*.py` нет `print(`. Проверка: `grep -rn 'print(' src/rag src/mcp` пусто (или только комментарии).
- [ ] Запуск `python main.py build-index` → в `logs/app.log` есть записи с уровнем INFO про каждую стадию (load → chunk → embed → save).
- [ ] Запуск `python main.py` + 1 вопрос → в `logs/app.log` записаны: retrieval-стадии (DEBUG), MCP-decision (INFO), Ollama-вызов (INFO).
- [ ] `python src/mcp/server.py` запускается, JSON-RPC stdout не загрязнён логами (проверка вручную: `echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"capabilities":{},"clientInfo":{"name":"t","version":"0"}}}' | python src/mcp/server.py` — корректный JSON в ответе).

---

### Задача 2.2.3. Перевод `assistant.py` и `main.py` на logger

- **Статус:** ToDo
- **Приоритет:** high
- **Объём:** S
- **Зависит от:** Задача 2.2.2.
- **Связанные документы:** `_docs/architecture.md` § 3.1, § 3.2.
- **Затрагиваемые файлы:** `src/assistant.py`, `src/main.py`.

#### Описание

Разделить «UI-вывод пользователю» и «программный лог»:

- **UI-print остаётся** в `main.py` (приветствие, отображение ответа и источников, прощание) и в `assistant.py::__main__` (rich-вывод markdown). Это **не лог**, это интерфейс.
- **Программный print заменяется** на logger: «Retrieved N chunks», «MCP decision: use_mcp=...», «Calling tool ...», «MCP server started/closed», предупреждения и ошибки.

`main.py` в самом начале вызывает `setup_logging()`.

`assistant.py::__main__` тоже вызывает `setup_logging()` (для самостоятельного запуска).

`verbose=True` теперь дублирует UI-вывод в logger через DEBUG (а не отдельным `print`).

#### Definition of Done

- [ ] В `src/assistant.py` и `src/main.py` все «программные» print заменены на logger. UI-print (показ ответа, источников, приглашений) — остался.
- [ ] При `KB_LOG_LEVEL=DEBUG` — в `logs/app.log` видна вся диагностика, в stdout — только UI-вывод.
- [ ] При `KB_LOG_LEVEL=WARNING` — в stdout всё ещё нормальный UI, в `logs/app.log` — пусто/почти пусто.
- [ ] Smoke: `python main.py` отвечает на 1 вопрос, в `logs/app.log` есть события всех стадий retrieval + MCP + LLM.

---

## 6. Этап 3. Обработка ошибок

Цель этапа — закрыть точки, где исключение зависает (нет таймаутов), глотается без диагностики, или вылетает traceback'ом наружу пользователю.

### Задача 2.3.1. Аудит и инвентаризация необработанных ошибок

- **Статус:** ToDo
- **Приоритет:** high
- **Объём:** S
- **Зависит от:** Задача 2.2.3.
- **Связанные документы:** `_docs/current-state.md` § 2.5, § 2.6, § 2.10.
- **Затрагиваемые файлы:** `_docs/current-state.md` (приёмка обновлений), эта секция спринта (отчёт).

#### Описание

Перед правками — **зафиксировать** в файле спринта (раздел § 9 «История изменений спринта» либо отдельно в `progress.txt`) полный список мест, где ошибка может остаться необработанной. Минимум:

- `rag/query.py::ask_llm` — `requests.post` без `timeout=` (зависает при недоступной Ollama).
- `mcp/client.py::_send` — `proc.stdout.readline()` без таймаута (зависает при немом MCP-сервере).
- `mcp/client.py::_init_mcp` (или эквивалент в `assistant.py`) — `stderr=subprocess.PIPE`, никто не читает; pipe-buffer переполняется → server hang.
- `assistant.py::_llm_decide_mcp_usage` — `except Exception: return None, None` без логирования причины.
- `main.py` — необработанные `requests.RequestException`, `BrokenPipeError`, `RuntimeError` всплывают traceback'ом.
- `rag/build_index.py` — отсутствие `try/except` вокруг `pickle.dump`, `faiss.write_index`.
- `rag/ingest.py::ingest_documents` — `else`-ветка с `TypeError` (см. `current-state.md` § 2.1) — **только зафиксировать**, не править в этом спринте.
- `mcp/server.py::read_document` — обработка `FileNotFoundError`, `PermissionError`.

После аудита — записи добавить в `_docs/current-state.md` § 2 (если ещё не зафиксированы), либо просто зафиксировать в `progress.txt`-секции для трекинга закрытий следующими задачами.

#### Definition of Done

- [ ] В `_board/progress.txt` (или § 9 спринта) есть запись «Аудит ошибок 2026-XX-XX» со списком мест.
- [ ] В `_docs/current-state.md` § 2 — записи для всех найденных проблем (если их ещё не было).

---

### Задача 2.3.2. Таймауты и stderr MCP

- **Статус:** ToDo
- **Приоритет:** high
- **Объём:** M
- **Зависит от:** Задача 2.3.1.
- **Связанные документы:** `_docs/current-state.md` § 2.5, § 2.6.
- **Затрагиваемые файлы:** `src/rag/query.py`, `src/mcp/client.py`, `src/config.py`.

#### Описание

1. В `rag/query.py::ask_llm` добавить `timeout=` (и connect, и read) в `requests.post`. Значения — параметры в `config.py`: `OLLAMA_REQUEST_TIMEOUT = 120` (секунд), `OLLAMA_CONNECT_TIMEOUT = 5`.
2. В `mcp/client.py::_send` добавить таймаут на `readline()` через `select` или отдельный поток-сторож. Параметр в `config.py`: `MCP_READ_TIMEOUT = 30`.
3. Stderr MCP-сервера — обрабатывать одним из двух способов:
   - либо `stderr=subprocess.DEVNULL` (безопасно, теряем диагностику);
   - либо отдельный daemon-поток-читатель stderr, который пишет содержимое через `logger.warning(...)` с префиксом `[mcp-server]`. **Этот вариант предпочтительнее** — диагностика сохраняется.
4. Все таймауты при срабатывании логируются как `ERROR` с понятным сообщением.

#### Definition of Done

- [ ] `requests.post` в `ask_llm` имеет `timeout=` (туплированный), значение из `config.py`.
- [ ] `MCPClient._send` бросает `TimeoutError` (или явное прикладное исключение), если ответ не пришёл за `MCP_READ_TIMEOUT`.
- [ ] Stderr MCP-сервера потребляется (DEVNULL или logger). Запуск без MCP — не зависает (вручную: убить Ollama / послать `kill -STOP` MCP-серверу — клиент возвращает ошибку за заданный timeout, не виснет).
- [ ] `_docs/current-state.md` § 2.5 и § 2.6 — записи перенесены в § 6 «История закрытий» с пометкой задачи `2.3.2` и SHA коммита.

---

### Задача 2.3.3. Унификация ошибок верхнего уровня

- **Статус:** ToDo
- **Приоритет:** high
- **Объём:** S
- **Зависит от:** Задача 2.3.2.
- **Связанные документы:** `_docs/architecture.md` § 5, `_docs/instructions.md` § 6.
- **Затрагиваемые файлы:** `src/main.py`, `src/assistant.py`.

#### Описание

Пользователь не должен видеть голый `Traceback (most recent call last):`. Добавить:

1. В `src/main.py` — единый `try/except Exception as e` вокруг `assistant.query(...)`:
   ```
   except Exception as e:
       logger.exception("query failed")
       print(f"❌ Ошибка: {e}. Подробности — в logs/app.log.")
   ```
2. То же — вокруг `assistant.close()` в `finally`.
3. В `assistant.py::_llm_decide_mcp_usage` — `except Exception as e: logger.warning("decision parse failed: %s", e); return None, None`.
4. В `assistant.py::query`:
   - сетевые ошибки Ollama → пробрасываем наверх (главный handler в `main.py`).
   - ошибки MCP-вызова — логируем `WARNING`, продолжаем без MCP (текущее поведение, но с логом).

#### Definition of Done

- [ ] Голый traceback в stdout пользователя невозможен при стандартных сценариях ошибки (Ollama 5xx, MCP timeout, отсутствие индекса).
- [ ] Все «проглоченные» исключения логируются хотя бы на уровне `WARNING`.
- [ ] Smoke: остановить Ollama, запустить `python main.py`, задать вопрос — пользователь видит читаемое сообщение, в `logs/app.log` — полный stacktrace.

---

## 7. Этап 4. Тесты

Цель этапа — покрыть критические подсистемы базовыми тестами. Не претендуем на 100% coverage; важно — закрыть регрессии в RAG и MCP-инструментах.

### Задача 2.4.1. Pytest-инфраструктура и фикстуры

- **Статус:** ToDo
- **Приоритет:** high
- **Объём:** M
- **Зависит от:** Задача 2.3.3.
- **Связанные документы:** `_docs/instructions.md` § 8.
- **Затрагиваемые файлы:** `src/requirements.txt`, `tests/__init__.py` (новый), `tests/conftest.py` (новый), `tests/fixtures/` (новый), `pytest.ini` или `pyproject.toml` (минимальный).

#### Описание

1. Добавить в `src/requirements.txt`: `pytest>=8.0`, `pytest-mock>=3.12`. Не вводим `pytest-cov`, `pytest-asyncio` без необходимости.
2. Создать `tests/` в корне репозитория. Структура зеркалит `src/`:
   ```
   tests/
   ├── __init__.py
   ├── conftest.py
   ├── fixtures/
   │   ├── docs/                 # 2-3 коротких .md для тестов
   │   ├── chunks_minimal.pkl    # либо строится в фикстуре в runtime
   │   └── index_minimal.faiss
   ├── rag/
   │   ├── __init__.py
   │   └── (test_chunk, test_query, test_search_engine — задачи 2.4.2 и 2.4.3)
   ├── mcp/
   │   ├── __init__.py
   │   └── (test_server — задача 2.4.4)
   └── test_assistant.py         (задача 2.4.5)
   ```
3. `conftest.py` — общие фикстуры:
   - `tmp_docs_dir` (3 коротких .md),
   - `minimal_index` (строит FAISS-индекс из 4-6 чанков на лету, без скачивания моделей),
   - `mock_sentence_transformer` (фикстура с замоканным `SentenceTransformer.encode`, возвращает детерминированные эмбеддинги-заглушки),
   - `mock_ollama` (мок `requests.post` и `ollama.Client.chat`).
4. `pytest.ini` (минимальный):
   ```
   [pytest]
   testpaths = tests
   pythonpath = src tests
   ```
5. Импортные хаки `sys.path.insert(...)` из `src/rag/*` нельзя ломать — ставим `pythonpath = src` в pytest, чтобы импорты `from config import ...` работали.

#### Definition of Done

- [ ] `pytest -q` запускается без ошибок (даже если в `tests/` пока пустые тесты — главное чтобы инфраструктура была валидной).
- [ ] Установка `pip install -r src/requirements.txt` ставит pytest без конфликтов.
- [ ] Минимальный «sanity» тест проходит: `tests/test_smoke.py::test_imports` импортирует `assistant`, `rag.search_engine`, `mcp.server` — без ошибок.
- [ ] `tests/fixtures/docs/` содержит 2-3 коротких `.md` (по 100-300 символов).
- [ ] Документация: `_docs/instructions.md` § 8.3 — обновлён под актуальный набор тестов.

---

### Задача 2.4.2. Тесты для `rag/chunk` и `rag/query`

- **Статус:** ToDo
- **Приоритет:** high
- **Объём:** M
- **Зависит от:** Задача 2.4.1.
- **Связанные документы:** `_docs/rag-pipeline.md`.
- **Затрагиваемые файлы:** `tests/rag/test_chunk.py` (новый), `tests/rag/test_query.py` (новый).

#### Описание

`tests/rag/test_chunk.py`:

- `test_chunk_text_deterministic` — один и тот же текст даёт один и тот же набор чанков.
- `test_chunk_text_overlap` — соседние чанки имеют ожидаемый перехлёст.
- `test_chunk_documents_preserves_source` — поле `source` чанка совпадает с исходным документом.

`tests/rag/test_query.py`:

- `test_retrieve_returns_top_k` — на минимальном индексе `retrieve` возвращает ровно `TOP_K` чанков.
- `test_retrieve_score_field_present` — каждый возвращаемый чанк имеет `score: float`.
- `test_retrieve_empty_index` — на пустом индексе возвращается `[]` без падений.
- `test_build_prompt_contains_query_and_contexts` — финальный промпт содержит подстроки из query и context'ов.

`ask_llm` НЕ тестируем напрямую — он тестируется через мок в `test_assistant.py` (задача 2.4.5).

#### Definition of Done

- [ ] `pytest tests/rag/test_chunk.py tests/rag/test_query.py -q -v` зелёный.
- [ ] Для `retrieve`-тестов используется минимальный индекс из фикстуры `minimal_index` (без сетевых вызовов и тяжёлых моделей).
- [ ] Покрытие функций `chunk_text`, `chunk_documents`, `retrieve`, `build_prompt` — есть хотя бы один тест на каждую публичную функцию.

---

### Задача 2.4.3. Тесты для `rag/search_engine`

- **Статус:** ToDo
- **Приоритет:** high
- **Объём:** M
- **Зависит от:** Задача 2.4.2.
- **Связанные документы:** спринт 01 (`01-advanced-search.md` § 5), `_docs/rag-pipeline.md`.
- **Затрагиваемые файлы:** `tests/rag/test_search_engine.py` (новый).

#### Описание

Тестируем три ключевые функции с моками тяжёлых зависимостей.

- `test_hybrid_retrieve_returns_top_n_with_score` — на минимальном индексе и подменённом BM25 возвращает top-N с полем `score` (RRF).
- `test_hybrid_retrieve_rrf_merges_two_lists` — синтетические два ранжированных списка → RRF даёт ожидаемое слияние (точечный тест на формулу).
- `test_rerank_uses_cross_encoder` — `CrossEncoder.predict` замокан, проверяем порядок и top_k.
- `test_rerank_falls_back_to_top_k_when_disabled` — при `RERANK_ENABLED=False` возвращается top-`TOP_K` от hybrid без CrossEncoder-вызова.
- `test_maybe_expand_query_short_query_triggers` — `"sqli"` → expansion вызывается.
- `test_maybe_expand_query_long_query_skipped` — длинный запрос не вызывает LLM.
- `test_maybe_expand_query_llm_failure_returns_none` — при бросках Ollama-клиента — `expanded=None`, без падения.
- `test_search_facade_full_pipeline` — `search(query)` с замоканным CrossEncoder и LLM возвращает top-`TOP_K` с полем `score`.

#### Definition of Done

- [ ] `pytest tests/rag/test_search_engine.py -q -v` зелёный.
- [ ] Cross-encoder и Ollama-клиент в тестах **замоканы**; ни один тест не качает `BAAI/bge-reranker-base`.
- [ ] Все 8 кейсов из описания реализованы.

---

### Задача 2.4.4. Тесты для MCP-сервера

- **Статус:** ToDo
- **Приоритет:** medium
- **Объём:** M
- **Зависит от:** Задача 2.4.3.
- **Связанные документы:** `_docs/mcp-tools.md`, `_docs/current-state.md` § 2.4.
- **Затрагиваемые файлы:** `tests/mcp/test_server.py` (новый).

#### Описание

Тестируем три инструмента + path-traversal защиту. Используем `tmp_docs_dir` фикстуру и patch-им `DOCUMENTS_DIR`.

- `test_list_documents_returns_all` — на 3 файлах в фикстуре возвращает 3 пути.
- `test_list_documents_empty_dir` — на пустом каталоге возвращает `[]`.
- `test_read_document_ok` — чтение существующего файла возвращает его содержимое.
- `test_read_document_not_found` — несуществующий файл → понятная ошибка (не traceback).
- `test_read_document_path_traversal_blocked` — попытка `../../etc/passwd` отклоняется.
- `test_search_documents_by_name_substring_case_insensitive` — поиск «POL» находит «policy.md», «Policy.txt».
- `test_search_documents_no_match` — поиск по несуществующему имени → `[]`.

#### Definition of Done

- [ ] `pytest tests/mcp/test_server.py -q -v` зелёный.
- [ ] Тесты не запускают MCP как subprocess — вызывают функции-инструменты напрямую (через `from mcp.server import read_document, list_documents, search_documents` или эквивалент).
- [ ] Path-traversal блок проверен.

---

### Задача 2.4.5. Тесты для `assistant.py`

- **Статус:** ToDo
- **Приоритет:** medium
- **Объём:** M
- **Зависит от:** Задача 2.4.4.
- **Связанные документы:** `_docs/architecture.md` § 3.2, `_docs/mcp-tools.md`.
- **Затрагиваемые файлы:** `tests/test_assistant.py` (новый).

#### Описание

- `test_llm_decide_mcp_usage_valid_json` — мок LLM возвращает `{"use_mcp": true, "tool": "list_documents", "args": {}}` → возвращается корректный кортеж.
- `test_llm_decide_mcp_usage_invalid_json_returns_none` — мок LLM возвращает мусор → `(None, None)` без падения, в логах `WARNING`.
- `test_llm_decide_mcp_usage_malformed_keys` — JSON есть, но без `use_mcp` → `(None, None)`.
- `test_query_returns_contract` — `query("hello")` возвращает словарь с ключами `{"answer", "sources", "mcp_used", "mcp_tool"}`.
- `test_query_uses_mcp_when_decided` — мок LLM решил «нужен tool», мок MCP-клиента возвращает stub → в финальном промпте есть MCP-блок, `mcp_used=True`.
- `test_query_skips_mcp_when_decision_is_no` — мок LLM решил «не нужен» → MCP-клиент не вызывается, `mcp_used=False`.

Все внешние вызовы (Ollama, MCP-subprocess, SentenceTransformer, CrossEncoder) — замоканы.

#### Definition of Done

- [ ] `pytest tests/test_assistant.py -q -v` зелёный.
- [ ] Контракт возврата `query` зафиксирован тестом — любая будущая регрессия ломает тест.
- [ ] Полный `pytest -q` зелёный (все тесты вместе).
- [ ] `_docs/instructions.md` § 8.2 обновлён: «Текущий smoke-цикл — `pytest -q` + 1 ручной вопрос».
- [ ] `_docs/current-state.md` § 2.9 (отсутствие тестов) — перенос в § 6 «История закрытий» с пометкой задачи `2.4.5`.

---

## 8. Риски и смягчение

| # | Риск                                                                  | Смягчение                                                                                          |
|---|------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------|
| 1 | Миграция `print` → `logger` ломает UX в CLI (исчезает «болтовня»)     | Сохранить «UI-print» в `main.py` и `assistant.py::__main__`; логи параллельно в файл.              |
| 2 | Logger в MCP-сервере ломает stdout-транспорт JSON-RPC                 | Принудительно отправлять логи в stderr или только в файл; отдельный тест на «чистоту» stdout.       |
| 3 | Тесты `search_engine` требуют сложных моков cross-encoder              | Минимальные стабы `CrossEncoder.predict` через `pytest-mock`, без реальной модели.                 |
| 4 | Таймауты `requests.post` ломают долгие LLM-ответы (>2 мин)             | Дефолт `OLLAMA_REQUEST_TIMEOUT = 120` достаточно для qwen3:0.6b; параметризовано через `config.py`. |
| 5 | `tests/fixtures/index_minimal.faiss` — байнари в репозитории          | Строить индекс на лету в фикстуре; не коммитить готовый файл.                                      |
| 6 | Spring-cleanup: правки логов разрастаются за пределы скоупа            | Чёткие задачи 2.2.2 и 2.2.3, ограниченный список затрагиваемых файлов.                             |
| 7 | Порядок этапов — логирование ДО обработки ошибок ДО тестов              | Зафиксирован в зависимостях задач; нарушать запрещено правилом плана.                             |

## 9. Сводная таблица задач спринта

| #       | Задача                                                                    | Приоритет | Объём | Статус | Зависит от |
|---------|---------------------------------------------------------------------------|:---------:|:-----:|:------:|:----------:|
| 2.1.1   | Создать `_docs/links.md` и подключить к навигации                         | medium    | S     | Progress | —        |
| 2.1.2   | Создать `_docs/legacy.md` (тонкий указатель)                              | medium    | S     | ToDo   | 2.1.1      |
| 2.1.3   | Закрепить правило «новый спринт = новая ветка»                            | high      | XS    | ToDo   | —          |
| 2.2.1   | Логгер-инфраструктура и конфигурационный файл                             | high      | M     | ToDo   | 2.1.3      |
| 2.2.2   | Перевод `rag/*` и `mcp/*` на logger                                       | high      | M     | ToDo   | 2.2.1      |
| 2.2.3   | Перевод `assistant.py` и `main.py` на logger                              | high      | S     | ToDo   | 2.2.2      |
| 2.3.1   | Аудит и инвентаризация необработанных ошибок                              | high      | S     | ToDo   | 2.2.3      |
| 2.3.2   | Таймауты (`requests.post`, MCP `_send`) и stderr MCP                      | high      | M     | ToDo   | 2.3.1      |
| 2.3.3   | Унификация ошибок верхнего уровня (`main.py`, `assistant.py`)             | high      | S     | ToDo   | 2.3.2      |
| 2.4.1   | Pytest-инфраструктура и фикстуры                                          | high      | M     | ToDo   | 2.3.3      |
| 2.4.2   | Тесты для `rag/chunk` и `rag/query`                                       | high      | M     | ToDo   | 2.4.1      |
| 2.4.3   | Тесты для `rag/search_engine`                                             | high      | M     | ToDo   | 2.4.2      |
| 2.4.4   | Тесты для MCP-сервера                                                     | medium    | M     | ToDo   | 2.4.3      |
| 2.4.5   | Тесты для `assistant.py`                                                  | medium    | M     | ToDo   | 2.4.4      |

> Таблицу обновлять синхронно с заголовками задач выше.

## 10. История изменений спринта

- **2026-04-26** — спринт открыт, ТЗ зафиксировано, задачи 2.1.1–2.4.5 в `ToDo`. Ветка `feature/quality-baseline` создана от `main`.
