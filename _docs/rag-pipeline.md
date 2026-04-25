# RAG-конвейер

Документ описывает фактическую реализацию retrieval-части в `src/rag/`.

## 1. Стадии конвейера

```
┌────────────┐   ┌──────────┐   ┌──────────────┐   ┌────────────┐   ┌────────────┐
│  ingest    ├──►│  chunk   ├──►│   embed      ├──►│   index    ├──►│   query    │
│            │   │          │   │              │   │  (FAISS)   │   │            │
└────────────┘   └──────────┘   └──────────────┘   └────────────┘   └────────────┘
   ingest.py       chunk.py         embed.py        build_index.py     query.py
```

Build-time (фазы 1–4) запускается командой `python main.py build-index` и сохраняет на диск `index.faiss` + `chunks.pkl`.

Runtime (фаза 5) запускается на каждый пользовательский вопрос.

## 2. Ingest — загрузка документов

**Файл**: `src/rag/ingest.py`. **Главная функция**: `ingest_documents()`.

### Поддерживаемые форматы

```python
SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf", ".docx"}
```

| Расширение | Загрузчик                              | Что извлекаем                               |
|------------|----------------------------------------|---------------------------------------------|
| `.txt`     | `Path.read_text(encoding="utf-8", errors="ignore")` | Текст как есть.                             |
| `.md`      | то же                                  | Markdown как обычный текст (форматирование сохраняется в виде символов). |
| `.pdf`     | `pypdf.PdfReader.pages[*].extract_text()` | Объединённый текст всех страниц через `\n`. |
| `.docx`    | `python-docx`, `Document.paragraphs`   | Текст параграфов через `\n`.                |

### Возвращаемый формат

```python
[
    {"path": str, "text": str},
    ...
]
```

### Источник документов

`DOCUMENTS_DIR` из `config.py` (по умолчанию `"./docs"`, относительно `src/`). Обход — `Path(DOCUMENTS_DIR).rglob("*")`, рекурсивно.

### Известный нюанс

В `ingest.py` есть мёртвый код в `else`-ветви:

```python
else:
    [documents.append(doc) for doc in ingest_documents(path)]
```

`rglob("*")` уже рекурсивный, эта ветка достижима только для каталогов и неподдерживаемых файлов. Кроме того, `ingest_documents()` не принимает аргумент `path` — при попадании в эту ветку будет `TypeError`. Подробнее в `current-state.md`. **Не наследовать паттерн.**

## 3. Chunk — разбиение на фрагменты

**Файл**: `src/rag/chunk.py`.

### Параметры

```python
CHUNK_SIZE = 700      # размер чанка в токенах (cl100k_base)
CHUNK_OVERLAP = 100   # перехлёст между соседними чанками в токенах
```

### Алгоритм

1. Текст документа токенизуется: `tokens = encoder.encode(text)`.
2. Шаг скользящего окна: `step = CHUNK_SIZE - CHUNK_OVERLAP = 600`.
3. Для `i in range(0, len(tokens), step)` берётся срез `tokens[i:i + CHUNK_SIZE]`, декодируется обратно в строку.
4. Каждый чанк получает метаданные: `source` (путь файла), `chunk_id` (порядковый номер внутри документа).

### Токенайзер

`tiktoken.get_encoding("cl100k_base")` — токенайзер из семейства OpenAI. Не совпадает ни с токенайзером SentenceTransformers (`all-MiniLM-L6-v2` использует WordPiece), ни с токенайзером Qwen3 (BPE с другим словарём). Это **рабочий, но субоптимальный** вариант: размер чанка в «cl100k-токенах» ≠ ожидаемому количеству токенов в эмбеддинг-модели или LLM. Кандидат на замену — токенайзер от используемой эмбеддинг-модели или просто символьный размер. См. `current-state.md` и `roadmap.md`.

### Возвращаемый формат

```python
[
    {"text": str, "source": str, "chunk_id": int},
    ...
]
```

## 4. Embed — эмбеддинги

**Файл**: `src/rag/embed.py`.

### Модель

`EMBEDDING_MODEL = "all-MiniLM-L6-v2"` (`sentence-transformers`). Параметры:

- 6 слоёв MiniLM, размер вектора **384**.
- Лучшее покрытие — английский. Русский язык работает, но качество ниже, чем у multilingual-моделей (`paraphrase-multilingual-mpnet-base-v2`, `intfloat/multilingual-e5-base`). Кандидат на замену при работе с RU-документами — см. `roadmap.md`.

### Алгоритм

```python
texts = [c["text"] for c in chunks]
embeddings = model.encode(texts, show_progress_bar=True)
return np.array(embeddings)   # shape: (N, 384), dtype float32
```

Прогресс-бар идёт в stdout — может загрязнять MCP-stdio-канал, если эмбеддинг-модель загружается во время работы MCP-сервера. Для текущего пайплайна сборка происходит синхронно в `build-index`, проблемы нет.

## 5. Index — построение FAISS-индекса

**Файл**: `src/rag/build_index.py`. **Функция**: `build_index()`.

### Тип индекса

```python
index = faiss.IndexFlatIP(dim)     # inner product
faiss.normalize_L2(embeddings)     # L2-нормализация → IP эквивалентен косинусной близости
index.add(embeddings)
```

`IndexFlatIP` — точный (без аппроксимации) поиск по скалярному произведению. С нормализованными векторами это — **косинусная близость**. Подходит для тысяч-десятков тысяч чанков. Для сотен тысяч и больше — кандидат на `IndexHNSWFlat` или `IndexIVFFlat`.

### Артефакты на диске

Сохраняются по путям из `config.py`, **относительно `src/`**:

```
src/index.faiss      ← faiss.write_index(index, str(index_path))
src/chunks.pkl       ← pickle.dump(chunks, f)
```

`chunks.pkl` нужен, потому что FAISS хранит только векторы и их id; сами тексты и метаданные хранятся отдельно.

### Полный цикл `build_index()`

```python
documents = ingest_documents()           # 1. Загрузка
chunks = chunk_documents(documents)      # 2. Чанкование
embeddings = embed_chunks(chunks)        # 3. Эмбеддинги
index = faiss.IndexFlatIP(emb.shape[1])  # 4. Индекс
faiss.normalize_L2(embeddings)
index.add(embeddings)
faiss.write_index(index, str(index_path))    # 5. Сохранение
pickle.dump(chunks, open(chunks_path, "wb"))
```

Если документов нет — функция печатает ошибку и **не пишет** артефакты. Старые `index.faiss`/`chunks.pkl`, если они уже были, **остаются нетронутыми**.

## 6. Query — поиск и генерация

**Файл**: `src/rag/query.py`.

### As-Is pipeline (до спринта 01)

Текущий («As-Is») поток обработки одного поискового запроса от `user_query` до `contexts` — чистый семантический retrieval, единственный источник ранжирования — FAISS (косинусная близость по нормализованным эмбеддингам):

```
user_query
  ↓ model.encode([query])
  ↓ faiss.normalize_L2(q_emb)
  ↓ index.search(q_emb, TOP_K)        ← единственный источник ранжирования
  ↓ [chunks[i] for i in ids[0]]
contexts → build_prompt → ask_llm → answer
```

Ограничения этого подхода (из-за чего и стартовал спринт 01):

- На коротких запросах и аббревиатурах (`sqli`, `403`, `XSS`) эмбеддинги «размазывают» точные совпадения — нужный чанк может оказаться вне top-K.
- `scores`, возвращаемые `index.search`, отбрасываются — потребитель не видит, насколько уверенно найден чанк.

Целевой pipeline — см. `_board/sprints/01-advanced-search.md` § 5.4 (hybrid BM25 + vector с RRF, cross-encoder reranker, query expansion).

### Загрузка индекса (`_ensure_index_exists`)

При импорте модуля выполняется автозагрузка:

1. Если `index.faiss` и `chunks.pkl` существуют — читаются в глобальные `index` и `chunks`.
2. Если нет — вызывается `build_index()`, после чего повторная попытка загрузки.
3. Если документов в `DOCUMENTS_DIR` нет — печатается ошибка, `index = None`, `chunks = []`.

> Эта автозагрузка выполняется один раз при импорте `rag.query`. Импорт идёт уже на старте `assistant.py`. См. `current-state.md` про связанный нюанс старта MCP-сервера.

### `retrieve(query: str)`

```python
q_emb = model.encode([query])
faiss.normalize_L2(q_emb)
scores, ids = index.search(q_emb, TOP_K)   # TOP_K = 5 по умолчанию
return [
    {**chunks[i], "score": float(scores[0][rank])}
    for rank, i in enumerate(ids[0]) if i >= 0
]
```

Возвращает список словарей того же вида, что лежат в `chunks.pkl` (`text`, `source`, `chunk_id`), с дополнительным полем `score: float` — косинусной близостью из FAISS. Кэшированные `chunks` **не мутируются** — каждый возвращаемый dict собирается заново через `{**chunks[i], "score": ...}`.

При `verbose=True` в `CompanyKBAssistant.query` (`src/assistant.py`) печатается блок:

```
🔍 Retrieved 5 chunks for query: "..."
  1. [score=0.7821] src/docs/policy.md#3
  2. [score=0.7104] src/docs/security.md#1
  ...
```

**Защита от пустого индекса**: если `index is None or len(chunks) == 0` — возвращается `[]`. Дальнейший pipeline корректно работает с пустыми контекстами.

### `build_prompt(query, contexts)`

Промпт построен в формате псевдо-XML тегов (LLM-friendly):

```text
<role>You are a helpful assistant that answers questions about company information.</role>
<instructions>Answer the question ONLY based on the context provided below.
If the answer is not in the context, say "I don't have that information in the knowledge base."</instructions>

<context>
[Source: src/docs/policy.md]
{full chunk text}

[Source: src/docs/security.md]
{full chunk text}
...
</context>

<query>
{user question}
</query>

<assistant>
```

Если контекст пустой — отдельный шаблон с инструкцией «отвечай на основе общих знаний или скажи, что не знаешь».

### `ask_llm(prompt)`

```python
requests.post(
    OLLAMA_URL,                       # http://localhost:11434/api/generate
    json={"model": OLLAMA_MODEL,      # qwen3:0.6b по умолчанию
          "prompt": prompt,
          "stream": False}
)
return response.json()["response"]
```

Синхронный, блокирующий запрос. Никаких ретраев, таймаутов и фолбэков. Любая ошибка `requests` пробрасывается наверх и ловится в `main.py`.

### `ask(query: str)`

Лёгкая обёртка `retrieve` + `build_prompt` + `ask_llm`. Возвращает `(answer: str, contexts: list)`. Используется автономно (без MCP) в `python -m rag.query`.

## 7. Параметры производительности

Из корневого `README.md` (приблизительно, на типичной CPU-машине):

| Стадия                  | Время                       |
|-------------------------|-----------------------------|
| Сборка индекса (10 МБ docs) | ~30 сек (one-time)         |
| Эмбеддинг запроса       | ~50 мс                      |
| FAISS-поиск             | ~5 мс                       |
| Генерация LLM           | 2–5 сек (зависит от модели) |
| **Итого на запрос**     | **2–6 сек**                 |

Для ускорения:

- Уменьшить `TOP_K` (3 вместо 5).
- Уменьшить `CHUNK_SIZE` (500 вместо 700) — больше мелких чанков, более точные совпадения, меньше токенов в промпте → быстрее LLM.
- Использовать меньшую LLM (`qwen3:0.6b` уже самая маленькая в семействе).
- Перейти на стриминг (`stream=True`) — пользователь видит первые токены раньше.

## 8. Пересборка индекса

Когда нужна:

- Добавили / изменили / удалили документы в `DOCUMENTS_DIR`.
- Сменили `CHUNK_SIZE` или `CHUNK_OVERLAP`.
- Сменили `EMBEDDING_MODEL` (старый и новый индексы несовместимы — их нельзя смешивать).

Команда:

```bash
cd src
python main.py build-index
```

Альтернатива (то же самое, без обёртки):

```bash
python -m rag.build_index
```

## 9. Advanced Pipeline (in progress, спринт 01)

В спринте 01 поверх семантического retrieve строится «Advanced Pipeline». На текущий момент закрыты:

- **Hybrid Search (BM25 + Vector + RRF)** — реализован в `src/rag/search_engine.py::hybrid_retrieve`. BM25-индекс `rank_bm25.BM25Okapi` строится лениво в RAM поверх кэшированных `chunks` (без записи на диск, токенизация — `text.lower().split()`). Параллельно делается векторный поиск на `top_n = TOP_K_HYBRID` (по умолчанию 20). Два ранжирования сливаются через **Reciprocal Rank Fusion**:
  ```
  RRF(c) = Σ 1 / (RRF_K + rank_r(c))    для r in {vector, bm25}
  ```
  Возвращаются top-`top_n` чанков с полем `score = RRF`. Ценность видна на коротких/точных запросах (`403`, `sqli`, `RBAC`): BM25 вытягивает чанк с точным совпадением даже там, где эмбеддинги «размазывают» сигнал. Параметры — в `src/config.py`: `HYBRID_ENABLED`, `TOP_K_HYBRID`, `RRF_K`.
- **Reranker (cross-encoder)** — реализован в `src/rag/search_engine.py::rerank`. Кандидаты top-`TOP_K_HYBRID` от гибридного поиска перегоняются через `sentence_transformers.CrossEncoder("BAAI/bge-reranker-base")`. Модель грузится лениво при первом вызове (~278 МБ из HuggingFace), кэшируется в `~/.cache/huggingface/`. На CPU ~40 мс на 4 пары, ~200 мс на 20 пар — укладывается в бюджет +1 сек к baseline. После реранка остаётся top-`TOP_K` с полем `score = rerank logit` (выше = лучше). Если `RERANK_ENABLED=False` либо модель не загрузилась — silently fallback на отсортированный гибрид. Параметры — `RERANK_ENABLED`, `RERANKER_MODEL`.
- **Фасад `search(query)`** — публичный entry-point: `hybrid_retrieve` → `rerank`. Возвращает top-`TOP_K` чанков с полем `score`.

Целевой поток одного запроса (после закрытия задач 3.3–3.4 спринта 01):

```
user_query
  ↓ maybe_expand_query   (опц., короткие/аббревиатурные запросы)
  ↓ hybrid_retrieve(query, TOP_K_HYBRID)         ← BM25 + Vector + RRF
  ↓ rerank(query, candidates, TOP_K)             ← cross-encoder
contexts (Top-K) → build_prompt → ask_llm → answer
```

`src/rag/query.py::retrieve` остаётся низкоуровневым семантическим retrieve и используется `search_engine` изнутри, чтобы не сломать `python -m rag.query`.

## 10. Что НЕ реализовано (кандидаты в roadmap)

- **Инкрементальная индексация**: при изменении одного документа сейчас пересобирается весь индекс.
- **Версионирование индекса**: артефакты перезаписываются. Невозможно «откатиться» к предыдущему индексу.
- **Хранение исходного хеша документов**: нельзя автоматически детектировать, какие документы поменялись.
- **Query expansion**: LLM-переформулировка коротких запросов (закроется задачей 01.3.3).
- **Метаданные-фильтры**: нельзя сказать «искать только в `policies/`».
