---
name: interface-design
description: Maintains a persistent design system file across sessions so UI stays consistent. Captures spacing, color tokens, typography, depth strategy and component conventions in .interface-design/system.md. Use when starting a new UI project, when styles drift between sessions, or when you want to extract an implicit design system from existing code. Commands: init (create system), audit (check consistency), extract (read from existing code). Triggers on: "дизайн система", "design system", "стили разъезжаются", "сохрани дизайн", "консистентный UI", "interface-design init", "interface-design audit".
---

# Interface Design — Persistent Design System

Сохраняет решения по дизайну между сессиями в `.interface-design/system.md`. Решает проблему: Claude каждый раз изобретает стили заново → UI дрейфует.

---

## Commands

### `/interface-design init`

Создать дизайн-систему для проекта. Задай вопросы:

1. Что за продукт? (dashboard / landing / mobile-app / admin)
2. Целевая аудитория и tone: профессиональный, игривый, минималистичный?
3. Существующие цвета/шрифты если есть?
4. Стек: React/Vue/plain HTML? Tailwind/CSS modules/styled?

Затем создай `.interface-design/system.md`:

```markdown
# Design System — {Project} — {DATE}

## Aesthetic Direction
{1-2 предложения: brutalist / editorial / soft-ui / glassmorphism / etc}

## Color Tokens
Primary:    #hex  (HSL: H S% L%)
Secondary:  #hex
Accent:     #hex
Background: #hex
Surface:    #hex
Text:       #hex
Muted:      #hex

Dark mode:
Background: #hex
Surface:    #hex
Text:       #hex

## Typography
Font heading:  {font-name}, weights: 700, 800
Font body:     {font-name}, weights: 400, 500
Font mono:     {font-name}

Scale (px):    12 / 14 / 16 / 18 / 20 / 24 / 32 / 40 / 48 / 56
Line height:   1.2 (headings) / 1.6 (body)
Letter spacing: -0.02em (headings) / 0 (body)

## Spacing
Base unit: 4px
Scale: 4 / 8 / 12 / 16 / 24 / 32 / 48 / 64 / 96 / 128

## Border Radius
Small:  4px  (inputs, badges)
Medium: 8px  (cards, buttons)
Large:  16px (modals, panels)
Full:   9999px (pills, avatars)

## Shadows / Depth
Elevation 1 (cards):    0 1px 3px rgba(0,0,0,0.1)
Elevation 2 (dropdowns): 0 4px 12px rgba(0,0,0,0.15)
Elevation 3 (modals):   0 16px 48px rgba(0,0,0,0.2)

## Animation
Duration: 50ms (micro) / 150ms (default) / 300ms (page) / 500ms (hero)
Easing:   ease-out (enter) / ease-in (exit) / spring(1,90,10,0) (interactive)

## Component Conventions
Button primary:   bg-primary text-white px-4 py-2 rounded-medium font-500
Button secondary: border border-primary text-primary px-4 py-2 rounded-medium
Input:            border bg-surface px-3 py-2 rounded-small focus:ring-2
Card:             bg-surface rounded-large shadow-elevation1 p-6

## Grid / Layout
Max width:      1280px
Columns:        12
Gutter:         24px (desktop) / 16px (mobile)
Breakpoints:    sm:640 md:768 lg:1024 xl:1280

## Do / Don't
DO:   {конкретные паттерны принятые для этого проекта}
DON'T: generic purple gradients, Inter everywhere, card-in-card, too many shadows
```

---

### `/interface-design audit`

Прочитай `.interface-design/system.md`, затем прочитай все CSS/компонентные файлы.

Найди отклонения:
- Цвета не из палитры
- Отступы не кратные base unit
- Шрифты не из type scale
- Компоненты с нестандартными border-radius

Выдай отчёт:
```
## Design Drift Report — {DATE}

### Нарушения
| Файл | Строка | Нарушение | Правильно |
|------|--------|-----------|-----------|
| ... | ... | color #ff5500 не в палитре | use var(--accent) |

### Рекомендации
- ...
```

---

### `/interface-design extract`

Прочитай существующий CSS/компоненты и восстанови систему.

Команды для анализа:
```bash
# Найти все уникальные цвета
grep -rh "color\|background\|border" src/ --include="*.css" | grep -oE '#[0-9a-fA-F]{3,6}' | sort | uniq -c | sort -rn

# Найти все font-size
grep -rh "font-size" src/ | grep -oE '[0-9]+px' | sort -n | uniq

# Найти все border-radius
grep -rh "border-radius" src/ | grep -oE '[0-9]+px' | sort -n | uniq
```

Заполни `system.md` на основе найденных паттернов.

---

## Rules для всех сессий

Если `.interface-design/system.md` существует — **всегда читай его перед** созданием или изменением любого UI компонента.

Если новый компонент требует значения которого нет в системе:
1. Используй ближайшее из шкалы
2. Добавь новый токен в `system.md` с комментарием

Никогда не изобретай цвета, отступы или радиусы вне системы.
