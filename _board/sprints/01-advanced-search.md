# Спринт 01. Advanced Search Pipeline

- **Статус спринта:** Active
- **Ветка:** `feature/advanced-search-pipeline`
- **Дата старта:** 2026-04-25
- **Дата закрытия:** —
- **Связанные документы:**
  - `../../_docs/rag-pipeline.md` § 6, § 9
  - `../../_docs/architecture.md` § 4
  - `../../_docs/configuration.md` § 1
  - `../../_docs/current-state.md` § 2.5, § 2.10
  - `../../_docs/roadmap.md` Phase 4 (Reranker, Hybrid FAISS+BM25)

## 1. Цель спринта

Текущий retrieval-слой — это чистый семантический поиск (`src/rag/query.py::retrieve`): эмбеддинги FAISS + top-K чанков. Для коротких и «технических» запросов (коды ошибок, аббревиатуры) этого недостаточно — эмбеддинги «размазывают» точные совпадения, в выдаче много шума, ответ LLM получается общим.

Цель спринта — поднять качество retrieval до «Advanced Pipeline»:

1. Добавить **гибридный поиск** (BM25 + Vector, слияние через RRF).
2. Добавить этап **реранкинга** (cross-encoder) после top-K извлечения.
3. Добавить **query expansion** (LLM-переформулировка для коротких/аббревиатурных запросов).
4. Не ломая контракт MCP-инструментов и текущего класса `CompanyKBAssistant`.

Дополнительно — подготовить почву: зафиксировать текущий поток поиска (Impact Analysis), добавить минимальную наблюдаемость (логирование `score` на уровень чанка), завести рабочую ветку.

## 2. Скоуп

### В скоупе

- Новый модуль `src/rag/search_engine.py` с гибридным поиском, реранкером и query expansion.
- Новая зависимость `rank_bm25` (BM25 в Python).
- Использование cross-encoder через уже имеющийся `sentence-transformers` (модель `BAAI/bge-reranker-base`).
- Query expansion через текущий Ollama-клиент (без новых LLM, без новых сетевых вызовов).
- Логирование `score` каждого чанка в консольный вывод.
- Обновление документации в `_docs/` под новый функционал.
- Перевод корневого `README.md` и `src/README.md` на русский с актуализацией под новый pipeline.

### Не в скоупе

- HTTP-транспорт MCP, Web-UI, REST API — отдельные фазы `_docs/roadmap.md`.
- Замена эмбеддинг-модели на multilingual — отдельная задача.
- Метаданные-фильтры («искать только в `policies/`») — отдельная задача.
- Миграция `print` → `logging` — отдельная фаза.
- Pytest-инфраструктура — отдельная фаза.
- Изменения MCP-инструментов (`read_document`, `list_documents`, `search_documents`).

## 3. Acceptance criteria спринта

Спринт считается закрытым, когда выполнены **все** условия:

- [ ] Все коммиты спринта — в ветке `feature/advanced-search-pipeline`, ветка запушена.
- [ ] `src/rag/search_engine.py` реализует `hybrid_retrieve`, `rerank`, `maybe_expand_query`, `search`; модуль импортируется без ошибок.
- [ ] `CompanyKBAssistant.query` использует `search(...)`; контракт метода (`{answer, sources, mcp_used, mcp_tool}`) не изменён.
- [ ] В консольном выводе при `verbose=True` видны `score` каждого найденного чанка (хотя бы на одном из этапов: hybrid и/или rerank).
- [ ] `python main.py build-index` собирает индекс без ошибок; интерактивный режим отвечает без падений на 5 smoke-вопросах (минимум 2 — короткие/аббревиатурные).
- [ ] Контракт MCP-инструментов не изменён (`src/mcp/server.py` не редактировался).
- [ ] Обновлены: `_docs/rag-pipeline.md`, `_docs/architecture.md`, `_docs/configuration.md`, `_docs/current-state.md`, `_docs/roadmap.md` (закрытые пункты Phase 4).
- [ ] `README.md` (корень) и `src/README.md` переведены на русский и отражают новый pipeline.
- [ ] Все задачи спринта — в статусе `Done`, сводная таблица актуальна.

---

## 4. Этап 1. Legacy Audit & Traceability

Цель этапа — зафиксировать текущий поток поиска до изменений и добавить минимальную наблюдаемость, чтобы было с чем сравнивать после реализации.

### 4.1 Уточнение про два «search» в проекте

В проекте два объекта с именем «search». Спецификация спринта относится **только к первому**:

- `src/rag/query.py::retrieve` — семантический retrieval, top-K чанков, FAISS. **Это «search», который мы расширяем.**
- `src/mcp/server.py::search_documents` — поиск по **имени файла**, регистр-нечувствительный `in`-поиск по `path.name`. К этому спринту не относится, контракт не трогаем.

### Задача 1.1. Зафиксировать рабочую ветку и записать старт спринта

- **Статус:** Done
- **Приоритет:** high
- **Объём:** XS
- **Зависит от:** —
- **Связанные документы:** `../README.md` § «Жизненный цикл задачи», `../process.md` § 3.
- **Затрагиваемые файлы:** `_board/progress.txt`.

#### Описание

Ветка `feature/advanced-search-pipeline` уже создана (текущая активная ветка). Все коммиты спринта обязаны идти в неё. Зафиксировать запись о старте спринта в `_board/progress.txt` (если ещё не сделано в рамках инициализации).

#### Definition of Done

- [x] `git branch --show-current` возвращает `feature/advanced-search-pipeline`.
- [x] Ветка запушена: `git push -u origin feature/advanced-search-pipeline`.
- [x] В `_board/progress.txt` есть запись от текущей даты с заголовком «Старт спринта 01».

---

### Задача 1.2. Impact Analysis текущего поиска (As-Is)

- **Статус:** ToDo
- **Приоритет:** high
- **Объём:** S
- **Зависит от:** Задача 1.1.
- **Связанные документы:** `../../_docs/rag-pipeline.md` § 6, `../../_docs/architecture.md` § 4.
- **Затрагиваемые файлы:** `_docs/rag-pipeline.md`.

#### Описание

Зафиксировать в документации текущий («As-Is») поток обработки поискового запроса от `user_query` до `contexts`. Это нужно как baseline для сравнения после реализации Advanced Pipeline.

Шаги:

1. В `_docs/rag-pipeline.md` § 6 добавить подсекцию «As-Is pipeline (до спринта 01)» со схемой:
   ```
   user_query
     ↓ model.encode([query])
     ↓ faiss.normalize_L2(q_emb)
     ↓ index.search(q_emb, TOP_K)        ← единственный источник ранжирования
     ↓ [chunks[i] for i in ids[0]]
   contexts → build_prompt → ask_llm → answer
   ```
2. Добавить ссылку «Целевой pipeline — см. `_board/sprints/01-advanced-search.md` § 5.4».
3. Не править код в этой задаче.

#### Definition of Done

- [ ] В `_docs/rag-pipeline.md` § 6 есть подсекция «As-Is pipeline» с приведённой схемой.
- [ ] Есть ссылка на `_board/sprints/01-advanced-search.md` § 5.4 как «целевой pipeline».
- [ ] Smoke-test не требуется — это документация.

---

### Задача 1.3. Логирование score в `retrieve`

- **Статус:** ToDo
- **Приоритет:** high
- **Объём:** S
- **Зависит от:** Задача 1.2.
- **Связанные документы:** `../../_docs/rag-pipeline.md` § 6, `../../_docs/instructions.md` § 3.3.
- **Затрагиваемые файлы:** `src/rag/query.py`, `src/assistant.py`.

#### Описание

`src/rag/query.py::retrieve` уже получает `scores, ids = index.search(...)`, но `scores` отбрасывается. Нужно вернуть его потребителям и вывести в консоль.

Шаги:

1. В `retrieve` добавить поле `score: float` в каждый возвращаемый чанк (рядом с `text`, `source`, `chunk_id`).
2. При `verbose=True` в `CompanyKBAssistant.query` (`src/assistant.py`) выводить блок:
   ```
   🔍 Retrieved 5 chunks for query: "..."
     1. [score=0.78] src/docs/policy.md#3
     2. [score=0.71] src/docs/security.md#1
     ...
   ```
3. Изменения **аддитивные** — потребители (`rag/query.py::ask`, `assistant.py::query`) уже используют только `c["source"]` и `c["text"]`. Поле `score` появится дополнительно.

#### Definition of Done

- [ ] `retrieve` возвращает чанки с полем `score` (тип `float`).
- [ ] При `verbose=True` в stdout видны строки `[score=...]` для каждого чанка.
- [ ] `python -m rag.query` всё так же работает (без `verbose`-блока, но без падений).
- [ ] Smoke-test: `python main.py` на 1 вопрос — видны score'ы.
- [ ] `_docs/rag-pipeline.md` § 6 обновлён под новый формат возврата `retrieve` (поле `score`).

---

## 5. Этап 2. Спецификация Advanced Pipeline

Этот раздел — сама спецификация, на которую опираются задачи Этапа 3. Отдельный файл `search-spec.md` не создаётся (см. правило `_board/README.md` — выносные документы только если описание не помещается в текущую структуру).

### 5.1 Hybrid Search (BM25 + Vector, слияние через RRF)

**Идея.** Параллельно с векторным поиском запускаем BM25 по тем же чанкам, два ранжирования объединяем через **Reciprocal Rank Fusion (RRF)**.

**Алгоритм.** Для запроса `q`:

1. Получаем два ранжированных списка длины `N` (предлагаемое `N = 20`):
   - `V = [c_v1, ..., c_vN]` — от вектора (FAISS, `index.search(q_emb, N)`).
   - `B = [c_b1, ..., c_bN]` — от BM25 (`rank_bm25.BM25Okapi.get_top_n(q_tokens, chunks, N)`).
2. Для каждого чанка `c` считаем RRF-score:
   ```
   RRF(c) = sum( 1 / (k + rank_r(c)) ) для r in {V, B}
   ```
   где `k = 60` (каноническое значение, Cormack & Clarke 2009), `rank_r(c)` — 1-based позиция `c` в списке `r`. Если `c` нет в списке — слагаемое 0.
3. Сортируем по убыванию `RRF`, возвращаем top-`TOP_K_HYBRID` (предлагаемое — 20, на вход реранкера).

**Интерфейс.**

```python
def hybrid_retrieve(query: str, top_n: int = TOP_K_HYBRID) -> list[dict]:
    """Top-N чанков по RRF(vector + BM25). Поле 'score' — итоговый RRF."""
```

**Детали реализации.**

- BM25-индекс строится поверх токенов `chunks[*]['text']` (простой `.lower().split()`, без стемминга в первой версии).
- Индекс BM25 живёт в RAM рядом с FAISS, ленивая инициализация при первом вызове или в `_ensure_index_exists()`. **Не сохраняем на диск** — тексты уже в `chunks.pkl`, пересборка BM25 для 10k чанков занимает <100 мс.
- Параметр `RRF_K = 60` — в `config.py`.

**Почему RRF, а не weighted sum.** RRF не требует нормализации score'ов между двумя разными метриками (cosine vs BM25), не нужно подбирать веса. Weighted sum — резервный вариант, если RRF окажется недостаточным (см. § 7 «Риски»).

**Пример ценности.** Запрос `"403 Forbidden"`:

- Вектор: ранг 1 — общий чанк про HTTP-коды.
- BM25: ранг 1 — чанк, содержащий точную подстроку «403».
- RRF вытягивает чанк с точным совпадением в топ-3.

### 5.2 Reranker (cross-encoder)

**Идея.** После гибридного поиска (top-20) применяем cross-encoder и оставляем top-5 по более точному ранжированию пары (query, passage).

**Алгоритм.**

1. Получить top-20 от `hybrid_retrieve`.
2. Для каждого чанка `c` построить пару `(q, c.text)`.
3. Прогнать через `sentence_transformers.CrossEncoder("BAAI/bge-reranker-base")`.
4. По полученным логит-score переранжировать.
5. Вернуть top-`TOP_K` (5 по умолчанию).

**Интерфейс.**

```python
def rerank(query: str, candidates: list[dict], top_k: int = TOP_K) -> list[dict]:
    """Переранжирует кандидатов cross-encoder'ом, возвращает top_k. Поле 'score' — rerank-score."""
```

**Детали.**

- Модель `BAAI/bge-reranker-base` (~278 МБ) грузится с HuggingFace при первом запуске (как и `all-MiniLM-L6-v2`).
- Инференс cross-encoder на CPU дороже вектора (десятки миллисекунд на пару). На 20 парах — ориентировочно ~500 мс. Это приемлемо: LLM-генерация и так 2–5 сек.
- Параметры в `config.py`:
  - `RERANKER_MODEL = "BAAI/bge-reranker-base"`,
  - `TOP_K_HYBRID = 20` (на вход реранкера),
  - `TOP_K = 5` (на выход реранкера, остаётся прежним),
  - `RERANK_ENABLED = True` (флаг отключения для деградации/отладки).

**Почему так.** Cross-encoder смотрит на пару `(query, passage)` целиком и точнее sentence-эмбеддингов. Делать cross-encoder на всех чанках слишком дорого, поэтому сначала дёшево сужаем гибридом, потом дорого и точно — cross-encoder'ом.

### 5.3 Query Expansion (LLM rewrite)

**Идея.** Для коротких/аббревиатурных запросов перед поиском расширяем текст более развёрнутым через LLM.

**Эвристика активации.** Query expansion включается, если выполнено хотя бы одно:

- длина запроса ≤ `QUERY_EXPANSION_MIN_TOKENS` (по умолчанию 4) **слов**, **или**
- запрос состоит из «аббревиатурных» токенов (все заглавные ИЛИ короткие 2–6 символов без гласных: `sqli`, `XSS`, `403`, `RBAC`).

Если эвристика не сработала — этап пропускается (оригинальный запрос идёт напрямую в гибрид).

**Алгоритм.**

1. Построить промпт через существующий `ollama.Client` в `assistant.py`:
   ```
   System: You expand short or abbreviated search queries into a longer,
   topic-focused natural-language query. Return ONLY the expanded query,
   without any preface or quotes.

   User: {original_query}
   ```
2. Получить ответ, очистить от кавычек/markdown.
3. Передать **оба** запроса (`original` и `expanded`) в `hybrid_retrieve`, объединить два полученных списка через RRF (третье вхождение в формулу — рекомендация для устойчивости к искажениям expansion'а).

**Интерфейс.**

```python
def maybe_expand_query(query: str) -> tuple[str, str | None]:
    """Возвращает (original, expanded_or_None). expanded=None — эвристика не сработала."""
```

**Параметры в `config.py`:**

- `QUERY_EXPANSION_ENABLED = True`,
- `QUERY_EXPANSION_MIN_TOKENS = 4`.

**Пример.** `sqli` → `SQL Injection vulnerability examples and mitigations`.

### 5.4 Целевой поток одного запроса (target pipeline)

```
user_query
  ↓
maybe_expand_query(query)
  → expanded (опционально, по эвристике)
  ↓
hybrid_retrieve(query, top_n=TOP_K_HYBRID)               ← BM25 + Vector + RRF
  + при наличии expanded — повторный hybrid_retrieve(expanded), объединение через RRF
  ↓
rerank(query, candidates, top_k=TOP_K)                   ← cross-encoder
  ↓
contexts (Top-K с полем score) → build_prompt → ask_llm → answer
```

### Задача 2.1. Утвердить спецификацию Advanced Pipeline

- **Статус:** ToDo
- **Приоритет:** high
- **Объём:** XS
- **Зависит от:** Задача 1.3.
- **Связанные документы:** этот файл § 5.
- **Затрагиваемые файлы:** —.

#### Описание

Перед стартом Этапа 3 — пройтись по § 5.1–5.4, при необходимости уточнить:

- значения `TOP_K_HYBRID`, `RRF_K`, `QUERY_EXPANSION_MIN_TOKENS`,
- эвристику активации query expansion,
- стратегию объединения «оригинал + expanded» (двойной hybrid + RRF либо замена).

Любые правки фиксируются в этом файле в виде commit'а `docs(sprint-01): refine pipeline spec`. Если спецификация принимается без правок — задача закрывается без изменения файла.

#### Definition of Done

- [ ] Раздел § 5 прочитан, либо принят как есть, либо уточнён отдельным коммитом.
- [ ] Параметры (`TOP_K_HYBRID`, `RRF_K`, `RERANKER_MODEL`, `QUERY_EXPANSION_MIN_TOKENS`) подтверждены — это значения, с которыми стартует реализация.

---

## 6. Этап 3. Реализация

### 6.1 Целевой модуль и контракт с существующим кодом

- **Создать** `src/rag/search_engine.py` с функциями: `hybrid_retrieve`, `rerank`, `maybe_expand_query`, `search` (фасад). Имя модуля — из исходного ТЗ (`search_engine.py`).
- **Сохранить** `src/rag/query.py::retrieve` как «низкоуровневый семантический retrieve» — он используется `search_engine` изнутри. **Не удаляем**, чтобы не сломать `rag/query.py::ask` и `python -m rag.query`.
- **Перевести** `src/assistant.py::CompanyKBAssistant.query` на новый фасад:
  ```python
  from rag.search_engine import search
  contexts = search(user_query)
  ```
  Остальной поток (`_llm_decide_mcp_usage`, `build_prompt`, `ask_llm`) — без изменений.
- **MCP-инструменты** — без изменений. `mcp/server.py` не редактируем.
- **Поле `score`** — каждый возвращаемый чанк всегда содержит итоговое поле `score` (на стадии rerank — score реранкера, на стадии hybrid — RRF, на стадии retrieve — cosine). Дополнительно можно сохранить промежуточные `hybrid_score`, `rerank_score` для диагностики (опционально, не обязательно для DoD).

### 6.2 Порядок внедрения

Чтобы каждый коммит был верифицируем по smoke-тесту:

1. Hybrid (без реранкера, без expansion) → коммит, smoke.
2. Reranker поверх hybrid → коммит, smoke.
3. Query expansion поверх hybrid + rerank → коммит, smoke.
4. Переключение `assistant.py` на `search` → коммит, smoke.
5. Документация → коммит.
6. README (русский + актуализация) → коммит.

### Задача 3.1. Hybrid Search (BM25 + Vector + RRF)

- **Статус:** ToDo
- **Приоритет:** high
- **Объём:** M
- **Зависит от:** Задача 2.1.
- **Связанные документы:** § 5.1, `../../_docs/rag-pipeline.md` § 6.
- **Затрагиваемые файлы:** `src/rag/search_engine.py` (новый), `src/config.py`, `src/requirements.txt`.

#### Описание

Создать `src/rag/search_engine.py` с функцией `hybrid_retrieve(query, top_n=TOP_K_HYBRID)`. Реализовать BM25-индекс (in-memory, ленивая инициализация). Объединить вектор и BM25 через RRF.

Шаги:

1. Добавить в `src/requirements.txt`: `rank_bm25>=0.2.2`.
2. В `src/config.py` добавить:
   - `TOP_K_HYBRID = 20`,
   - `RRF_K = 60`,
   - `HYBRID_ENABLED = True`.
3. В `search_engine.py` реализовать:
   - ленивое построение `BM25Okapi(tokenized_chunks)` при первом вызове;
   - `hybrid_retrieve(query, top_n)` — два списка top-`top_n` (vector и BM25), RRF-merge, возврат top-`top_n` чанков с полем `score = RRF`.
4. На этом шаге `search_engine` ещё **не подключается** к `assistant.py` — только модуль и его smoke-тест.

#### Definition of Done

- [ ] `src/rag/search_engine.py` существует, импортируется без ошибок (`python -c "from rag.search_engine import hybrid_retrieve; print('OK')"` из `src/`).
- [ ] `pip install -r src/requirements.txt` ставит `rank_bm25` без конфликтов.
- [ ] `python -c "from rag.search_engine import hybrid_retrieve; r = hybrid_retrieve('test query'); print(len(r), r[0]['score'])"` отрабатывает на собранном индексе.
- [ ] Smoke-тест на 3 запросах (1 обычный, 1 с точным кодом «403 Forbidden», 1 русский) — каждый возвращает непустой список с полем `score`.
- [ ] MCP-инструменты не затронуты (`git diff src/mcp/` пустой).
- [ ] `_docs/rag-pipeline.md` обновлён: упомянут гибридный поиск.

---

### Задача 3.2. Reranker (cross-encoder)

- **Статус:** ToDo
- **Приоритет:** high
- **Объём:** M
- **Зависит от:** Задача 3.1.
- **Связанные документы:** § 5.2, `../../_docs/rag-pipeline.md` § 9.
- **Затрагиваемые файлы:** `src/rag/search_engine.py`, `src/config.py`.

#### Описание

В `search_engine.py` добавить функцию `rerank(query, candidates, top_k=TOP_K)` через `sentence_transformers.CrossEncoder("BAAI/bge-reranker-base")`. Также добавить функцию-фасад `search(query)` = `hybrid_retrieve` → `rerank`.

Шаги:

1. В `src/config.py` добавить:
   - `RERANKER_MODEL = "BAAI/bge-reranker-base"`,
   - `RERANK_ENABLED = True`.
2. В `search_engine.py` реализовать:
   - ленивая инициализация `CrossEncoder(RERANKER_MODEL)` при первом вызове `rerank`;
   - `rerank(query, candidates, top_k)` — пары (query, c.text), `model.predict(pairs)`, сортировка, возврат top-`top_k` с полем `score = rerank_score`;
   - `search(query)` — `rerank(query, hybrid_retrieve(query, TOP_K_HYBRID), TOP_K)` (если `RERANK_ENABLED=False` — возвращается top-`TOP_K` от `hybrid_retrieve`).
3. Документация: дополнить `_docs/rag-pipeline.md` § 9 (или новый § «Advanced Pipeline»).

#### Definition of Done

- [ ] `src/rag/search_engine.py::rerank` и `search` реализованы.
- [ ] Первый запуск докачивает `BAAI/bge-reranker-base` без ошибок.
- [ ] `python -c "from rag.search_engine import search; r = search('test'); print(len(r), r[0]['score'])"` отрабатывает.
- [ ] Smoke-тест на тех же 3 запросах, что в задаче 3.1, — top-`TOP_K` возвращается, `score` теперь rerank-score.
- [ ] Время на запрос укладывается в +1 сек к baseline (если нет — оставить запись в `_docs/current-state.md`, не блокировать спринт).
- [ ] MCP-инструменты не затронуты.

---

### Задача 3.3. Query Expansion (LLM rewrite)

- **Статус:** ToDo
- **Приоритет:** medium
- **Объём:** M
- **Зависит от:** Задача 3.2.
- **Связанные документы:** § 5.3, `../../_docs/architecture.md` § 4.
- **Затрагиваемые файлы:** `src/rag/search_engine.py`, `src/config.py`.

#### Описание

В `search_engine.py` добавить `maybe_expand_query` и подключить к `search`. Использовать существующий `ollama.Client` (как в `assistant.py::_llm_decide_mcp_usage`).

Шаги:

1. В `src/config.py` добавить:
   - `QUERY_EXPANSION_ENABLED = True`,
   - `QUERY_EXPANSION_MIN_TOKENS = 4`.
2. В `search_engine.py`:
   - реализовать эвристику активации (см. § 5.3);
   - реализовать вызов LLM с system-промптом из § 5.3;
   - в `search(query)` при наличии `expanded`: получить второй hybrid-список и объединить с первым через RRF, затем — `rerank`.
3. Не забыть: при `QUERY_EXPANSION_ENABLED=False` или провале LLM-вызова — silently fallback на оригинальный запрос.

#### Definition of Done

- [ ] `maybe_expand_query` корректно отрабатывает на коротких/аббревиатурных запросах (`sqli`, `403`, `XSS`) и пропускает длинные.
- [ ] При `verbose=True` в логах видно `expanded → "..."` для коротких запросов.
- [ ] Smoke-тест: 5 вопросов (2 короткие/аббревиатурные, 3 обычные) — все возвращают непустой ответ.
- [ ] Откат на оригинал при ошибке Ollama не падает с исключением.
- [ ] `_docs/architecture.md` § 4 обновлён схемой целевого pipeline.

---

### Задача 3.4. Переключить `CompanyKBAssistant` на новый фасад

- **Статус:** ToDo
- **Приоритет:** high
- **Объём:** S
- **Зависит от:** Задача 3.3.
- **Связанные документы:** `../../_docs/architecture.md` § 3.2, `../../_docs/rag-pipeline.md`.
- **Затрагиваемые файлы:** `src/assistant.py`.

#### Описание

В `src/assistant.py::CompanyKBAssistant.query` заменить вызов `retrieve(user_query)` на `search(user_query)` из `rag.search_engine`. Контракт метода `query` сохраняется как есть: `{answer, sources, mcp_used, mcp_tool}`.

Шаги:

1. Импорт: `from rag.search_engine import search`.
2. Заменить `contexts = retrieve(user_query)` → `contexts = search(user_query)`.
3. Никаких других правок в `assistant.py`. `_llm_decide_mcp_usage`, `_call_mcp_tool`, `build_prompt` не трогаем.
4. `rag/query.py::retrieve` остаётся как есть (вызов из `search_engine` и из `rag/query.py::ask` для `python -m rag.query`).

#### Definition of Done

- [ ] `assistant.py` импортирует `search` из `rag.search_engine`, `retrieve` напрямую больше не используется.
- [ ] Smoke-тест: 5 вопросов в интерактивном режиме (`python main.py`), у всех — непустой ответ, источники, MCP-решения принимаются как раньше.
- [ ] Smoke-тест MCP: 1 вопрос «list all documents» — корректно вызывает MCP-инструмент.
- [ ] Контракт возврата `query` не изменён (поля те же).

---

### Задача 3.5. Обновить документацию в `_docs/`

- **Статус:** ToDo
- **Приоритет:** medium
- **Объём:** M
- **Зависит от:** Задача 3.4.
- **Связанные документы:** `../../_docs/rag-pipeline.md`, `../../_docs/architecture.md`, `../../_docs/configuration.md`, `../../_docs/current-state.md`, `../../_docs/roadmap.md`.
- **Затрагиваемые файлы:** `_docs/rag-pipeline.md`, `_docs/architecture.md`, `_docs/configuration.md`, `_docs/current-state.md`, `_docs/roadmap.md`.

#### Описание

Привести проектную документацию в соответствие с новым pipeline.

Шаги:

1. `_docs/rag-pipeline.md`:
   - Новый раздел «Advanced Pipeline» с финальной схемой (см. § 5.4 этого файла).
   - Описание модуля `src/rag/search_engine.py` — фасад `search`.
   - Обновить § 9 «Что не реализовано»: убрать пункты «Reranker» и «Hybrid search».
2. `_docs/architecture.md`:
   - Обновить § 3.3 (RAG-конвейер) — добавить `search_engine.py`.
   - Обновить § 4 (поток обработки запроса) — новые этапы expansion / hybrid / rerank.
3. `_docs/configuration.md`:
   - В § 1 (таблица параметров) добавить: `TOP_K_HYBRID`, `RRF_K`, `HYBRID_ENABLED`, `RERANKER_MODEL`, `RERANK_ENABLED`, `QUERY_EXPANSION_ENABLED`, `QUERY_EXPANSION_MIN_TOKENS`.
   - В § 2 — описание влияния каждого нового параметра.
4. `_docs/current-state.md`:
   - В § 1 «Что работает» добавить: гибридный поиск, реранкер, query expansion.
   - При обнаружении новых нюансов — записать в § 2.
5. `_docs/roadmap.md`:
   - В Phase 4 пометить «Reranker», «Гибридный поиск FAISS+BM25» как `(done in sprint-01)` или перенести в раздел «История закрытий» (если такого нет — создать в конце документа).

#### Definition of Done

- [ ] Все пять документов в `_docs/` обновлены по чек-листу.
- [ ] `_docs/README.md` § «Навигация» — без изменений (новых файлов не появляется).
- [ ] Прочитать обновления один раз — нет внутренних противоречий и битых ссылок.

---

### Задача 3.6. Перевести `README.md` на русский и актуализировать

- **Статус:** ToDo
- **Приоритет:** medium
- **Объём:** M
- **Зависит от:** Задача 3.5.
- **Связанные документы:** `../../_docs/README.md` § «Язык документации».
- **Затрагиваемые файлы:** `README.md` (корень), `src/README.md`.

#### Описание

Корневой `README.md` и `src/README.md` сейчас на английском. Перевести на русский и актуализировать под новый pipeline (упомянуть hybrid + rerank + query expansion). Технические идентификаторы (RAG, MCP, FAISS, BM25, RRF, embedding, chunk, reranker, query expansion, FastMCP, Ollama, qwen3, all-MiniLM-L6-v2) **не переводим** — это правило `_docs/README.md` § «Язык документации».

Шаги:

1. `README.md` (корень):
   - Перевести на русский.
   - Заменить блок «Query Processing (Runtime)» на актуальный target pipeline (см. § 5.4 этого файла).
   - В блоке «RAG Pipeline» добавить шаги hybrid retrieve / rerank / query expansion.
   - Сохранить структуру с эмодзи-заголовками (это стилистический выбор существующего README).
2. `src/README.md`:
   - Перевести на русский.
   - В разделе «Project Structure» добавить `rag/search_engine.py`.
   - В разделе «How It Works» обновить шаги retrieval.
   - Раздел «MCP Tools» оставить как есть (список инструментов не менялся).
3. Пересмотреть упоминание модели по умолчанию: в `src/README.md` сейчас `OLLAMA_MODEL: "llama3"` в описании, в реальности — `qwen3:0.6b`. Привести в соответствие с `src/config.py`.

#### Definition of Done

- [ ] Оба файла переведены на русский, английские термины индустрии оставлены как есть.
- [ ] В обоих файлах упомянуты hybrid search, reranker, query expansion.
- [ ] Указанная модель Ollama в `src/README.md` совпадает с `src/config.py::OLLAMA_MODEL`.
- [ ] Smoke-test: README читается без внутренних противоречий, разметка корректна (заголовки, code-блоки).

---

## 7. Риски и смягчение

| # | Риск                                                                  | Смягчение                                                                                          |
|---|------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------|
| 1 | RRF даёт хуже, чем чистый вектор на русскоязычных запросах             | Параметризовать через `config.py` (`HYBRID_ENABLED`, `RRF_K`). При деградации — откатить флагом.   |
| 2 | Cross-encoder слишком медленный на CPU                                 | Снизить `TOP_K_HYBRID` до 10 при инференсе >1 сек. Флаг `RERANK_ENABLED=False` для отключения.    |
| 3 | Query expansion искажает смысл, особенно у аббревиатур-омонимов        | Слать в hybrid и оригинал, и expanded; объединять через RRF. Эвристика активации.                 |
| 4 | Рост времени ответа и потребления памяти                               | В задаче 1.3 — логирование score; смежно — фиксировать тайминги стадий в `progress.txt` ad-hoc.    |
| 5 | Несовпадение токенайзера BM25 и эмбеддинг-модели                       | Признаваемый факт (см. `_docs/current-state.md` § 2.2). Первая версия — `.lower().split()`.        |
| 6 | Удаление `RAW.md`-«сырого» ТЗ из истории сбивает контекст              | Все требования отражены в этом файле; `RAW.md` нигде в репозитории не упоминается.                 |

## 8. Сводная таблица задач спринта

| #     | Задача                                                                                                                     | Приоритет | Объём | Статус | Зависит от |
|-------|----------------------------------------------------------------------------------------------------------------------------|:---------:|:-----:|:------:|:----------:|
| 1.1   | Зафиксировать рабочую ветку и записать старт спринта                                                                       | high      | XS    | Done   | —          |
| 1.2   | Impact Analysis текущего поиска (As-Is)                                                                                    | high      | S     | ToDo   | 1.1        |
| 1.3   | Логирование score в `retrieve`                                                                                             | high      | S     | ToDo   | 1.2        |
| 2.1   | Утвердить спецификацию Advanced Pipeline                                                                                   | high      | XS    | ToDo   | 1.3        |
| 3.1   | Hybrid Search (BM25 + Vector + RRF)                                                                                        | high      | M     | ToDo   | 2.1        |
| 3.2   | Reranker (cross-encoder)                                                                                                   | high      | M     | ToDo   | 3.1        |
| 3.3   | Query Expansion (LLM rewrite)                                                                                              | medium    | M     | ToDo   | 3.2        |
| 3.4   | Переключить `CompanyKBAssistant` на новый фасад                                                                            | high      | S     | ToDo   | 3.3        |
| 3.5   | Обновить документацию в `_docs/`                                                                                           | medium    | M     | ToDo   | 3.4        |
| 3.6   | Перевести `README.md` и `src/README.md` на русский и актуализировать (возможно потребуется актуализировать и другие файлы) | medium    | M     | ToDo   | 3.5        |

> Таблицу обновлять синхронно с заголовками задач выше.

## 9. История изменений спринта

- **2026-04-25** — спринт открыт, ТЗ зафиксировано, задачи 1.1–3.6 в `ToDo`.
