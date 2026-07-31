# Land Investment Monitor

Рабочий MVP по приложенному ТЗ: принимает цель обычным русским текстом, нормализует
объявления, считает локальную медиану цены за сотку, выявляет недооценённые лоты,
добавляет «душевные» и инвестиционные признаки, строит три вкладки Excel и готовит
Telegram-дайджест.

## Что уже работает

- JSON/CSV/Apify-совместимый импорт объявлений.
- Опциональный сбор публичного JSON-LD через Scrapling: только после явного opt-in,
  проверки `robots.txt` и без обхода авторизации, paywall или CAPTCHA.
- Команда `goal`: создание или корректировка поиска обычной фразой.
- Детерминированный анализ ключевых слов и опциональный OpenAI Structured Outputs.
- Цена за сотку, средняя по кластеру, медиана сопоставимых лотов в радиусе 1 км.
- Статус `КРАСНЫЙ`, если цена на 20%+ ниже локальной медианы.
- Потенциальная валовая маржа до расходов, дисконт к кадастровой стоимости.
- Вода, деревья, станция, будущая инфраструктура, неблагоприятная зона, фото,
  срочность, риски документов, подъезд и коммуникации.
- Координаты, кадастровый номер, ежегодные взносы, охрана/КПП и расстояние до
  повседневной инфраструктуры выводятся отдельными полями.
- Расстояние и оценочное время до `Москва, улица Смоленская, 10`; live OSRM включается
  отдельно.
- Три вкладки: `Для души`, `Инвест-топ`, `Двойной профит`.
- Telegram-дайджест и однопользовательский long-polling control loop.

## Быстрый офлайн-запуск

Из корня проекта:

```bash
python3 -m unittest discover -s tests -v

python3 -m land_monitor.cli run \
  --input examples/demo_listings.json \
  --goal config/goal.json \
  --features examples/feature_points.json \
  --cadastre examples/cadastral_values.csv \
  --out outputs/report-data.json
```

Демонстрационные данные намеренно используют `demo://`-ссылки и не являются
рыночными предложениями.

## Задать цель словами

```bash
python3 -m land_monitor.cli goal \
  "Ищу от 30 соток до 6 млн, ИЖС без взносов, вода и дубы; красный порог 25%" \
  --base config/goal.json \
  --out state/goal.json
```

Если установлены optional-зависимости и `OPENAI_API_KEY`, можно добавить
`--use-openai`. Интеграция использует Responses API и Structured Outputs; правила
ранжирования остаются детерминированными и аудируемыми.

Официальная документация по используемому формату:
https://developers.openai.com/api/docs/guides/structured-outputs

## Excel

В этом Codex workspace отчёт строит `scripts/build_workbook.mjs` через
`@oai/artifact-tool`. Скрипт читает `report-data.json`, оставляет ключевые расчёты
формулами Excel, добавляет комментарии и проверяет ошибки формул.

```bash
node scripts/build_workbook.mjs \
  outputs/report-data.json \
  outputs/land-investment-report.xlsx \
  outputs/qa
```

## Telegram

Скопируйте `.env.example` в безопасное хранилище переменных окружения; не коммитьте
токен.

Отправить готовый дайджест:

```bash
python3 -m land_monitor.cli digest --report outputs/report-data.json --send
```

Принимать корректировки цели словами и пересчитывать отчёт:

```bash
python3 -m land_monitor.cli bot \
  --input examples/demo_listings.json \
  --goal state/goal.json \
  --features examples/feature_points.json \
  --cadastre examples/cadastral_values.csv \
  --out outputs/report-data.json
```

`TELEGRAM_CHAT_ID` одновременно служит белым списком единственного управляющего чата.

## Ежедневный запуск

`scripts/run_monitor.sh` пересчитывает JSON, Excel и при явном включении отправляет
Telegram-дайджест. По умолчанию он ожидает свежий разрешённый импорт в
`state/listings.json` и не подменяет его демонстрационными данными.

Пример ручного запуска:

```bash
LAND_MONITOR_NODE=/Users/admin/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node \
  bash scripts/run_monitor.sh
```

Пример cron находится в `config/schedule.example.cron`. Для отправки дайджеста
добавьте в защищённое окружение `LAND_MONITOR_SEND_TELEGRAM=true`,
`TELEGRAM_BOT_TOKEN` и `TELEGRAM_CHAT_ID`. Для семантического анализа —
`LAND_MONITOR_USE_OPENAI=true` и `OPENAI_API_KEY`.

Планировщик только пересчитывает уже полученный импорт. Обновление
`state/listings.json` должно выполняться перед ним отдельным адаптером разрешённого
источника или лицензированного экспорта.

## Подключение реальных источников

Приоритет подключения:

1. Официальный API или лицензированный экспорт площадки.
2. Apify/готовый провайдер, если его условия разрешают нужное использование.
3. Собственный Scrapling-адаптер только для разрешённого публичного контента.

Для live Scrapling нужны:

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[scraping]'
.venv/bin/scrapling install --force
export LAND_MONITOR_ALLOW_LIVE_SCRAPING=true
```

Затем:

```bash
.venv/bin/land-monitor collect \
  --source example \
  --search-url 'https://example.com/authorized-search' \
  --out state/collected.json
```

Селекторы и нормализация Авито, ЦИАН, Яндекс.Недвижимости, Домклик и N1 должны
версионироваться отдельно и тестироваться на сохранённых разрешённых фикстурах.
Прямой «обход блокировок» не является частью безопасного MVP.

## Кадастр и НСПД

С декабря 2024 года публичная кадастровая карта перенесена в Национальную систему
пространственных данных. MVP не привязан к неофициальному и нестабильному endpoint:
кадастровые данные входят через `examples/cadastral_values.csv` или будущий
провайдер с документированным контрактом.

- Официальный сервис Роскадастра:
  https://kadastr.ru/services/publichnaya-kadastrovaya-karta/
- Портал НСПД:
  https://nspd.gov.ru/map

`Kadastr RU` — стороннее приложение; оно не скачивается и не устанавливается
автоматически. Для production-провайдера нужны проверенные условия, источник,
лимиты, дата актуальности и обработка расхождений с выпиской ЕГРН.

## Что означает «маржа»

`потенциальная маржа = локальная медиана × площадь − цена объявления`.

Это сигнал для ручной проверки, а не гарантия прибыли. Он не включает налоги,
комиссии, торг, юридическую проверку, межевание, ограничения, подключение
коммуникаций, финансирование, ремонт/расчистку и срок перепродажи.
