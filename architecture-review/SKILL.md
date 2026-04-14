---
name: architecture-review
description: Universal architecture review skill. Audits system design for complexity, coupling, scalability, maintainability, and security posture. Works on any codebase — backend services, bots, APIs, infrastructure. Triggers on: "ревью архитектуры", "architecture review", "проверь архитектуру", "насколько хорошо спроектировано", "design review", "что не так с архитектурой", "технический долг", "overfitting к требованиям", "structural review".
---

# Architecture Review

Универсальный аудит системного дизайна. Адаптируй глубину под размер проекта: для микросервиса — 20 мин, для полного стека — несколько часов.

---

## Before You Start

Прочитай перед запуском:
- Главный CLAUDE.md проекта (структура, конвенции)
- README / docs/INFRA.md / docs/SERVICES.md если есть
- Основные entry points (main, router, bot handler)
- `git log --oneline -20` — понять направление развития

Задай себе три вопроса:
1. Что система делает (одна фраза)?
2. Каков главный инвариант (что никогда не должно сломаться)?
3. Где самое страшное место (куда страшнее всего залезть)?

---

## Review Protocol

### Step 1: Boundary Analysis

**Что проверяем:** чёткость границ между компонентами.

```
□ Каждый модуль имеет одну ответственность?
□ Зависимости направлены в одну сторону (нет циклов)?
□ Публичный интерфейс минимален (не экспортируется лишнее)?
□ Данные не утекают через границы (нет shared mutable state)?
```

**Команды для анализа:**
```bash
# Python: найти циклические импорты
python3 -c "import modulegraph" 2>/dev/null || pip install modulegraph -q
# Или вручную:
grep -r "^from\|^import" src/ | sort | uniq -c | sort -rn | head -30

# Найти God Objects (классы > 300 строк)
find . -name "*.py" | xargs wc -l | sort -rn | head -20
```

**Red flags:**
- Модуль импортирует > 10 других модулей из того же проекта
- Один файл > 500 строк
- Класс делает и I/O, и бизнес-логику, и хранение
- `utils.py` размером > 200 строк (свалка)

---

### Step 2: Data Flow Review

**Что проверяем:** как данные движутся через систему.

```
□ Входная точка (user input / webhook / API) явно помечена?
□ Данные валидируются на входе, не в середине пайплайна?
□ Мутация данных происходит в одном месте?
□ Нет скрытых сайд-эффектов в read-only операциях?
□ Ошибки всплывают до вызывающего, не глотаются?
```

**Нарисуй схему (даже ASCII):**
```
User → [Triage] → [Router] → [Module A] → [Vault] → [Response]
                           ↘ [Module B] → [External API]
```

**Red flags:**
- Нет единой точки валидации входных данных
- `try: ... except: pass` без логирования
- Функция с параметром `**kwargs` без документации
- Глобальные переменные для состояния

---

### Step 3: Coupling & Cohesion

**Что проверяем:** насколько компоненты независимы.

```
□ Можно ли заменить компонент A не трогая B?
□ Тесты на A не требуют поднимать всю систему?
□ Конфигурация передаётся, не захардкожена внутри?
□ Внешние зависимости (DB, API) изолированы за интерфейсом?
```

**Метрика связности (вручную):**
```bash
# Сколько файлов надо изменить при переименовании ключевой сущности?
grep -r "VaultRecord\|UserSession\|ClassName" src/ | wc -l
# > 20 файлов → tight coupling
```

**Red flags:**
- Смена формата хранения требует правок в 5+ файлах
- Нет абстракции над внешним API (прямые requests.get везде)
- Тест создаёт реальные файлы/соединения без возможности mock
- Конфигурация читается из os.environ в середине бизнес-логики

---

### Step 4: Scalability Posture

**Что проверяем:** как система поведёт себя под нагрузкой или при росте.

```
□ Нет N+1 запросов в циклах?
□ Кэширование есть там где нужно?
□ Блокирующие I/O не в горячем пути?
□ Размер контекста/памяти ограничен (нет unbounded growth)?
□ Есть таймауты на внешние вызовы?
```

**Команды:**
```bash
# Найти потенциальные N+1 (запросы в цикле)
grep -n "for.*in" src/*.py | head -20
# Проверить каждый цикл — нет ли внутри db/api вызовов

# Найти отсутствие таймаутов
grep -r "requests.get\|httpx.get\|aiohttp" src/ | grep -v "timeout"
```

**Red flags:**
- `for item in all_items: db.query(item.id)` — N+1
- `context = load_entire_vault()` без пагинации
- `requests.get(url)` без timeout
- Накопление логов/истории без ротации

---

### Step 5: Operational Readiness

**Что проверяем:** насколько система готова к production-эксплуатации.

```
□ Логи содержат достаточно для диагностики (но не секреты)?
□ Ошибки не теряются (не глотаются в except)?
□ Health check / smoke test существует?
□ Graceful shutdown реализован?
□ Секреты в env, не в коде?
□ Backup / recovery задокументированы?
```

**Команды:**
```bash
# Найти залогированные секреты
grep -r "password\|token\|secret\|key" src/ | grep -v "env\|config\|test" | grep "log\|print"

# Найти голые except без логирования
grep -n "except:" src/*.py

# Проверить наличие health check
find . -name "*.py" | xargs grep -l "health\|ping\|status" 2>/dev/null
```

**Red flags:**
- `except Exception: pass` — ошибка исчезает
- Токены/ключи в исходном коде
- Нет документации "что делать если упало"
- Docker без restart policy или healthcheck

---

### Step 6: Complexity Budget

**Что проверяем:** не переусложнена ли система для своих задач.

```
□ Каждая абстракция оправдана (есть 2+ использования)?
□ Нет архитектуры "на будущее" без текущей необходимости?
□ Новый разработчик поймёт систему за день?
□ Количество слоёв соответствует сложности задачи?
```

**Вопрос на засыпку:** если бы систему писали заново сейчас — какие решения не повторили бы?

**Red flags:**
- Микросервисы для задачи одного человека
- Event-driven система с одним потребителем
- 4+ уровня абстракции для CRUD
- "Это сложно, только я понимаю как это работает"

---

### Step 7: Security Posture (High-Level)

**Что проверяем:** базовая безопасность (глубокий аудит — отдельный скилл `vectoros-security-audit`).

```
□ Пользовательский ввод валидируется и санитизируется?
□ Права минимальны (principle of least privilege)?
□ Зависимости не устарели критично?
□ Нет путей обхода авторизации?
```

**Команды:**
```bash
# Python: проверить устаревшие зависимости с CVE
pip-audit 2>/dev/null || pip install pip-audit -q && pip-audit

# Найти потенциальные injection точки
grep -rn "eval\|exec\|os.system\|subprocess.shell=True" src/
```

---

## Review Report Format

```markdown
# Architecture Review — {Project} — {DATE}

## TL;DR
{2-3 предложения: что хорошо, что плохо, главный риск}

## Strengths
- ...

## Critical Issues (fix before next release)
| # | Проблема | Файл/Компонент | Рекомендация |
|---|----------|----------------|--------------|
| 1 | ...      | ...            | ...          |

## Debt Items (fix in next sprint)
- ...

## Design Questions (обсудить с командой)
- ...

## Verdict
**Complexity**: Low / Medium / High (relative to task)
**Maintainability**: 1-5
**Scalability**: 1-5
**Production readiness**: 1-5

## Next Steps
1. ...
2. ...
```

---

## Quick Heuristics

| Симптом | Диагноз | Лечение |
|---------|---------|---------|
| "Не трогай этот файл, он магический" | High coupling / No tests | Изолировать за интерфейсом, покрыть тестами |
| Функция > 100 строк | Missing decomposition | Разбить по Single Responsibility |
| `utils.py` > 200 строк | Missing domain model | Сгруппировать по доменам |
| Тест поднимает всю систему | Missing seams | Ввести dependency injection |
| "Я добавлю это на будущее" | YAGNI violation | Удалить, добавить когда понадобится |
| Изменение в одном месте ломает другое | Hidden coupling | Явные интерфейсы + тесты |
