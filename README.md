Пара вариантов забирать данные для своих нужд

## I. Группы и каналы в telegram

Не хотел тянуть новые зависимости в HA, а аддон/контейнер для одного файла это перебор, поэтому запускаю сервер в одном из LXC контейнеров, но любой вариант с pip подойдет.

---

### 1. Получение API ID и API Hash
Эти данные нужны, чтобы ваш скрипт мог представляться как "приложение" Telegram.

1. Зайдите на сайт **[my.telegram.org](https://my.telegram.org)**.
2. Введите свой номер телефона, получите код в Telegram и войдите.
3. Перейдите в раздел **API development tools**.
4. Создайте новое приложение:
   *   **App title:** любое (например, `HomeAssistantBot`).
   *   **Short name:** любое (например, `habot`).
   *   **Platform:** Desktop.
5. Скопируйте **App api_id** и **App api_hash** и вставьте их в начало вашего Python-скрипта.

---

### 2. Установка 

__a. Вариант с venv__

Допустим, что вы скопировали папку tg (с одним файлом) себе в домашнюю директорию.

```
cd tg
python3 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install quart telethon
```

Убедитесь, что в файле скрипта (`tele.py`) прописаны ваши `api_id` и `api_hash`.
```
python3 tele.py
```
*   При первом запуске скрипт попросит ввести номер телефона и код подтверждения.
*   После ввода создастся файл `telegram_ha_session.session`.
*   Сервер запустится.

Достаточно в crontab или systemd автозапуск прописать и забыть. Например:
```
@reboot cd /home/user/tg && /home/user/tg/venv/bin/python tele.py > /home/user/tg/logfile.log 2>&1
```
__b. Вариант с uv__

Если установлен это менеджер, достаточно скопировать файл, внести в него ваши id и запустить сервер одной командой

```
uv run tele.py
```

---

### 3. Настройка Home Assistant

В  `configuration.yaml` добавьте новую запись в раздел `rest_command`

```yaml
rest_command:
  get_telegram_messages_from_channel:
    # Замените IP на адрес вашего сервера. Порт можно изменить в конце `tele.py`
    url: "http://192.168.1.xxx:5000/get_messages?channel={{ channel }}&limit={{ limit | default(10) }}"
    method: GET
    timeout: 20
    content_type: 'application/json'
```
*выполните перезагрузку*


### 4. Использование

Теперь можно вызвать команду с требуемыми параметрами и получить результат в переменную, например для постобработки данных с помощью LLM:


```yaml
...

action:
  - action: rest_command.get_telegram_messages_from_channel
    data:
      channel: "@bbcrussian"
      limit: 7
    response_variable: tg_data
  - action: conversation.process
    metadata: {}
    data:
      text: >-
        Изучи последние новости и подготовь очень краткий обзор.
        Вот список новостей: {{ tg_data.content.messages }}
      agent_id: conversation.gemini
    response_variable: news
...

```

## II. RSS ленты через Shell Command


### Шаг 1. Подготовка

Создайте в File Editor или другим способом файл скрипта. У меня это `fetch_news.py` в каталоге `/config/scripts/`
```python
#!/usr/bin/env python3
import feedparser
import sys

if len(sys.argv) > 1:
    rss_url = sys.argv[1]
else:
    rss_url = "https://rss.nytimes.com/services/xml/rss/nyt/World.xml"

try:
    if len(sys.argv) > 2:
        limit = int(sys.argv[2])
    else:
        limit = 10
except ValueError:
    limit = 10

feed = feedparser.parse(rss_url)

news_list = []

for i, entry in enumerate(feed.entries[:limit], 1):
    title = entry.get("title", "")
    description = entry.get("description", "")
    
    title = title.strip()
    description = description.strip()

    if description:
        news_list.append(f"{i}. {title}. {description}")
    else:
        news_list.append(f"{i}. {title}")

print("\n".join(news_list))
```

А в `configuration.yaml`  добавьте блок `shell_command` с указанием пути к файлу:

```yaml
shell_command:
  fetch_news: 'python3 /config/scripts/fetch_news.py "{{ url }}" "{{ count }}"'
```
*выполните перезагрузку*

### Шаг 2. Использование в автоматизациях
Теперь можно вызывать команду и забирать результат из переменной .

**Пример автоматизации:**
```yaml
action:
  - action: shell_command.fetch_news
    data:
      url: "https://feeds.skynews.com/feeds/rss/world.xml"
      count: 5
    response_variable: news_data

```
Результат будет доступен в переменной `{{ news_data.stdout }}`

---

Надеюсь, суть ясна. Если есть вопросы - скормите README llm и требуйте пояснений.

Ещё можно использовать пакет BeautifulSoup, но он под более уникальные задачи, с заголовков новостей много контекста не собрать, а возни с подбором селекторов под каждый ресурс много.
