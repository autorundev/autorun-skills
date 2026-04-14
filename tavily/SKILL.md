---
name: tavily
description: Извлечение контента из URL (extract) и веб-поиск (search) через Tavily API. Автоматический fallback когда WebFetch не справляется.
---

# Tavily — fallback для WebFetch

Используй когда WebFetch вернул ошибку (403, 429, timeout), мусор или пустой контент.
**Правило:** WebFetch не дал результат → сразу Tavily, не спрашивая пользователя.

## Режимы

### Extract — контент по URL
```bash
python3 ~/.claude/skills/tavily/tavily_client.py extract "https://example.com/article"
```

Несколько URL (до 20):
```bash
python3 ~/.claude/skills/tavily/tavily_client.py extract "URL1" "URL2"
```

### Search — поиск в интернете
```bash
python3 ~/.claude/skills/tavily/tavily_client.py search "запрос"
```

## Настройка

Нужен `TAVILY_API_KEY` в `~/vectoros/.env`. Получить на https://tavily.com (бесплатный tier: 1000 запросов/мес).

## Обработка ошибок

- Нет API ключа → сказать пользователю добавить в .env
- URL failed → сообщить
- Timeout → повторить 1 раз
