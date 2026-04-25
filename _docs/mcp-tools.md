# MCP: сервер, клиент и инструменты

Документ описывает реализацию MCP-слоя в `src/mcp/`.

## 1. Что такое MCP в этом проекте

**MCP (Model Context Protocol)** — стандартизированный JSON-RPC протокол, по которому LLM-агент может вызывать «инструменты» (tools), выставленные сервером. В проекте MCP используется для **прямого доступа LLM к документам** в обход RAG-индекса:

- читать документ целиком (а не только top-K чанков),
- получать список всех документов,
- искать документ по имени.

**Кто решает, использовать MCP или нет** — сама LLM. Решение принимается отдельным «decision-промптом» в `assistant.py::_llm_decide_mcp_usage`.

## 2. Сервер — `src/mcp/server.py`

### Инициализация

```python
from fastmcp import FastMCP
mcp = FastMCP("doc-tools", version="1.0.0")
```

Транспорт — **stdio** (по умолчанию для FastMCP при `mcp.run()`).

### Запуск

Сервер не стартует сам по себе — он запускается клиентом как subprocess (`python src/mcp/server.py` через `subprocess.Popen`). Stdin/stdout subprocess'а — канал JSON-RPC.

### Доступные инструменты

| Инструмент          | Сигнатура                              | Описание                                                                                       |
|---------------------|----------------------------------------|------------------------------------------------------------------------------------------------|
| `read_document`     | `read_document(file_path: str) -> str` | Читает файл целиком как UTF-8 строку. Доступ ограничен содержимым `DOCUMENTS_DIR`.             |
| `list_documents`    | `list_documents() -> str`              | Возвращает список всех файлов с поддерживаемыми расширениями в `DOCUMENTS_DIR` (рекурсивно), отсортированных алфавитно. |
| `search_documents`  | `search_documents(query: str) -> str`  | Регистр-нечувствительный поиск по **имени файла** (не содержимому). Возвращает список совпадений.|

#### `read_document(file_path)`

```python
@mcp.tool
def read_document(file_path: str) -> str:
    path = Path(file_path)
    if not str(path.resolve()).startswith(str(Path(DOCUMENTS_DIR).resolve())):
        return f"Error: Access denied. File must be in {DOCUMENTS_DIR}"
    with open(path, "r", encoding="utf-8") as f:
        return f.read()
```

Возможные ответы:

- содержимое файла как строка,
- `Error: Access denied. File must be in {DOCUMENTS_DIR}` — если путь вне разрешённого каталога,
- `Error: File not found: {file_path}` — если файла нет,
- `Error reading file: {error}` — общая ошибка чтения.

> **Безопасность**: проверка использует `Path.resolve()` (canonicalization), что устраняет path traversal через `..`. Но `DOCUMENTS_DIR` берётся **относительно cwd процесса MCP-сервера**. См. `current-state.md` § «Относительный путь DOCUMENTS_DIR».

#### `list_documents()`

```python
@mcp.tool
def list_documents() -> str:
    base_dir = Path(DOCUMENTS_DIR)
    if not base_dir.exists():
        return f"Error: Documents directory {DOCUMENTS_DIR} does not exist"
    documents = []
    for path in base_dir.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".txt", ".md", ".pdf", ".docx"}:
            documents.append(str(path.relative_to(base_dir)))
    if not documents:
        return "No documents found in the knowledge base."
    return "\n".join(f"- {doc}" for doc in sorted(documents))
```

Возвращает многострочный markdown-список с относительными путями.

#### `search_documents(query)`

Аналогично `list_documents`, но фильтрует по `query.lower() in path.name.lower()`. **Поиск только по имени файла**, не по содержимому. Для семантического поиска по содержимому — RAG.

### Расширение списка инструментов

Чтобы добавить инструмент, нужно:

1. Объявить функцию с декоратором `@mcp.tool` в `src/mcp/server.py`.
2. Расширить `decision_prompt` в `src/assistant.py::_llm_decide_mcp_usage` — добавить инструмент в список «Available MCP tools» и при необходимости новый пример JSON-ответа.
3. Описать новый инструмент в этом документе (раздел «Доступные инструменты»).

## 3. Клиент — `src/mcp/client.py`

### Класс `MCPClient`

Тонкая обёртка над `subprocess.Popen` + JSON-RPC по stdin/stdout. **Не использует** сторонние MCP-SDK.

#### Жизненный цикл

```python
client = MCPClient([sys.executable, str(server_py)])  # 1. Запуск subprocess + initialize()
result = client.call_tool("list_documents", {})       # 2. JSON-RPC tools/call
client.close()                                        # 3. terminate + wait
```

#### Конструктор

```python
self.proc = subprocess.Popen(
    cmd,
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    cwd=Path(__file__).parent.parent,   # cwd = src/
)
```

`cwd=src/` важен — `DOCUMENTS_DIR=./docs` в `config.py` интерпретируется относительно этого каталога.

#### `initialize()`

Отправляет JSON-RPC `initialize` с `protocolVersion: "2024-11-05"`, передаёт `clientInfo` и пустые `capabilities`. Без этого вызова FastMCP-сервер не отвечает на `tools/call`.

#### `call_tool(name, arguments)`

Отправляет:

```json
{
  "jsonrpc": "2.0",
  "id": <auto-incremented>,
  "method": "tools/call",
  "params": { "name": "<tool>", "arguments": { ... } }
}
```

Читает ровно одну строку ответа из stdout, парсит JSON. **Без таймаута**: если сервер не отвечает — поток зависнет навсегда. См. `current-state.md`.

#### `close()`

`terminate()` + `wait()`. Stderr subprocess'а в текущей реализации **не читается** — потенциальные ошибки сервера теряются.

### Потокобезопасность

Внутри есть `threading.Lock`, оборачивающий `_send`. Это защищает от одновременных вызовов из нескольких потоков, но в текущем CLI-сценарии вызовы линейные.

## 4. Decision-протокол (когда LLM решает использовать MCP)

### Запрос к LLM

`assistant.py::_llm_decide_mcp_usage` собирает промпт со всеми элементами:

1. **Текст вопроса** пользователя.
2. **Сводка контекстов** RAG: первые 3 чанка с `[1..3]. From {source}: {first 200 chars}…`.
3. **Список доступных инструментов** с краткими подсказками.
4. **Decision rules** — когда стоит использовать MCP.
5. **Формат строгого JSON-ответа** + примеры.

Запрос идёт через `ollama.Client().chat(...)` с системным сообщением «Always respond with valid JSON only».

### Формат ответа

LLM должна вернуть один из вариантов:

```json
{"use_mcp": false, "tool": null, "args": {}}
{"use_mcp": true, "tool": "list_documents", "args": {}}
{"use_mcp": true, "tool": "read_document", "args": {"file_path": "docs/policy.md"}}
{"use_mcp": true, "tool": "search_documents", "args": {"query": "vacation"}}
```

Парсер устойчив к обёртке в markdown ```` ```json ... ``` ````. При невалидном JSON — `except Exception`, решение «не использовать MCP», запрос идёт дальше как обычный RAG.

### Куда попадает результат вызова

После успешного `call_tool` строка-результат добавляется в финальный промпт **отдельным блоком**:

```text
<additional_info_from_mcp_tool>
{result}
</additional_info_from_mcp_tool>
```

Этот блок **не заменяет** RAG-контекст, а **дополняет** его. Финальная LLM видит и контексты, и MCP-результат.

## 5. Безопасность

### Реализованное

- **Path containment в `read_document`**: `Path(file_path).resolve()` сравнивается с `Path(DOCUMENTS_DIR).resolve()` через `startswith`. Это блокирует path traversal (`../../../etc/passwd`).
- **Whitelist расширений в `list_documents` / `search_documents`**: `.txt`, `.md`, `.pdf`, `.docx`.
- **Локальность**: stdio-канал не выходит за пределы машины. Сетевых вызовов в MCP-сервере нет.

### Известные риски

- **Относительный `DOCUMENTS_DIR`**: проверка корректна **только если cwd MCP-сервера = `src/`**. Клиент это обеспечивает (`cwd=src/`), но при ручном запуске `python src/mcp/server.py` из корня репозитория `Path("./docs")` будет указывать на корневой `./docs`, и проверка станет другой. См. `current-state.md`.
- **Нет таймаута чтения**: `MCPClient._send` блокируется навсегда, если сервер завис.
- **Stderr не читается**: ошибки сервера теряются.
- **Pickle-десериализация `chunks.pkl`**: к MCP не относится напрямую, но если злоумышленник заменит `chunks.pkl` — это RCE через `pickle.load`. Контролируйте файлы артефактов.

## 6. Тестирование MCP вручную

### Список инструментов

```bash
cd src
python -c "
import json, sys
from pathlib import Path
from mcp.client import MCPClient
client = MCPClient([sys.executable, str(Path('mcp/server.py'))])
print(client.call_tool('list_documents', {}))
client.close()
"
```

### Чтение документа

```python
client.call_tool("read_document", {"file_path": "docs/example.md"})
```

### Поиск по имени

```python
client.call_tool("search_documents", {"query": "policy"})
```

## 7. Что НЕ реализовано (кандидаты в roadmap)

- **Полнотекстовый поиск по содержимому** через MCP (сейчас — только по имени файла).
- **Инструмент для пересборки индекса** (`rebuild_index`).
- **Инструмент для добавления документа** в `DOCUMENTS_DIR` через MCP (с проверкой расширения и размера).
- **HTTP-транспорт** MCP (сейчас только stdio).
- **Prompt и Resources** MCP-фичи (сейчас только Tools).
- **Логирование вызовов** инструментов (кто, что, аргументы, длительность).
- **Лимит на размер ответа** `read_document` (большой `.docx` может перегрузить контекст LLM).
