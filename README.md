# GigaChat Python SDK

[![PyPI version](https://img.shields.io/pypi/v/gigachat.svg)](https://pypi.org/project/gigachat/)
[![License](https://img.shields.io/github/license/ai-forever/gigachat)](https://opensource.org/license/MIT)

Python-библиотека для работы с [REST API GigaChat](https://developers.sber.ru/docs/ru/gigachat/api/reference/rest/gigachat-api). Библиотека предоставляет удобный доступ к API из приложений на Python 3.8+, включает типизацию параметров запросов и полей ответов, поддерживает синхронный и асинхронный режимы работы.

Является частью экосистемы [GigaChain](https://github.com/ai-forever/gigachain) и входит в состав [langchain-gigachat](https://github.com/ai-forever/langchain-gigachat).

## Документация

Документация REST API доступна на [developers.sber.ru](https://developers.sber.ru/docs/ru/gigachat/api/reference/rest/gigachat-api). Примеры использования библиотеки находятся в папке [examples](examples/).

## Установка

```sh
pip install gigachat
```

## Быстрый старт

Для работы с библиотекой необходим ключ авторизации. Получите его в [личном кабинете GigaChat API](https://developers.sber.ru/docs/ru/gigachat/individuals-quickstart).

```python
import os
from gigachat import GigaChat

with GigaChat(
    credentials=os.environ.get("GIGACHAT_CREDENTIALS"),
    verify_ssl_certs=False,
) as giga:
    response = giga.chat("Привет! Расскажи о себе.")
    print(response.choices[0].message.content)
```

Рекомендуем хранить ключ авторизации в переменной окружения `GIGACHAT_CREDENTIALS`, а не в коде.

## Асинхронное использование

Библиотека поддерживает асинхронный режим работы с использованием `async/await`:

```python
import asyncio
import os
from gigachat import GigaChat

async def main():
    async with GigaChat(
        credentials=os.environ.get("GIGACHAT_CREDENTIALS"),
        verify_ssl_certs=False,
    ) as giga:
        response = await giga.achat("Объясни разницу между синхронным и асинхронным кодом.")
        print(response.choices[0].message.content)

asyncio.run(main())
```

## Потоковые ответы

Для получения ответа по частям используйте методы `stream` и `astream`:

```python
from gigachat import GigaChat

with GigaChat(credentials="...", verify_ssl_certs=False) as giga:
    for chunk in giga.stream("Напиши короткую историю о космосе."):
        print(chunk.choices[0].delta.content, end="", flush=True)
```

Асинхронный вариант:

```python
import asyncio
from gigachat import GigaChat

async def main():
    async with GigaChat(credentials="...", verify_ssl_certs=False) as giga:
        async for chunk in giga.astream("Напиши короткую историю о космосе."):
            print(chunk.choices[0].delta.content, end="", flush=True)

asyncio.run(main())
```

## Основные возможности

### Выбор модели

Укажите модель при инициализации клиента или в параметрах запроса:

```python
with GigaChat(credentials="...", model="GigaChat-Pro", verify_ssl_certs=False) as giga:
    response = giga.chat("Привет!")
```

Список доступных моделей можно получить методом `get_models()`.

### Эмбеддинги

```python
from gigachat import GigaChat

with GigaChat(credentials="...", verify_ssl_certs=False) as giga:
    embeddings = giga.embeddings(["Первый текст", "Второй текст"])
    print(f"Размерность: {len(embeddings.data[0].embedding)}")
```

### Работа с файлами

```python
from pathlib import Path
from gigachat import GigaChat

with GigaChat(credentials="...", verify_ssl_certs=False) as giga:
    # Загрузка файла
    uploaded = giga.upload_file(Path("document.pdf"), purpose="general")
    print(f"Файл загружен: {uploaded.id}")
    
    # Список файлов
    files = giga.get_files()
    for f in files.data:
        print(f.filename)
    
    # Удаление файла
    giga.delete_file(uploaded.id)
```

### Подсчет токенов

```python
from gigachat import GigaChat

with GigaChat(credentials="...", verify_ssl_certs=False) as giga:
    result = giga.tokens_count(["Текст для подсчета токенов"])
    print(f"Количество токенов: {result[0].tokens}")
```

### Проверка баланса

```python
from gigachat import GigaChat

with GigaChat(credentials="...", scope="GIGACHAT_API_B2B", verify_ssl_certs=False) as giga:
    balance = giga.get_balance()
    print(f"Доступно токенов: {balance.balance}")
```

### Работа с функциями

Библиотека поддерживает вызов функций (function calling). Подробный пример в файле [examples/example_functions.py](examples/example_functions.py).

## Конфигурация клиента

Основные параметры при инициализации `GigaChat`:

| Параметр | Описание | По умолчанию |
|----------|----------|--------------|
| `credentials` | Ключ авторизации из личного кабинета | — |
| `scope` | Версия API: `GIGACHAT_API_PERS` (физлица), `GIGACHAT_API_B2B` (ИП/юрлица, предоплата), `GIGACHAT_API_CORP` (постоплата) | `GIGACHAT_API_PERS` |
| `model` | Модель по умолчанию | `GigaChat` |
| `base_url` | Адрес API | `https://gigachat.devices.sberbank.ru/api/v1` |
| `verify_ssl_certs` | Проверка SSL-сертификатов | `True` |
| `timeout` | Таймаут запросов в секундах | `30.0` |
| `profanity_check` | Проверка на ненормативную лексику | `None` |

Для работы с моделями в раннем доступе используйте `base_url="https://gigachat-preview.devices.sberbank.ru/api/v1"`.

## Переменные окружения

Параметры можно задать через переменные окружения с префиксом `GIGACHAT_`:

```sh
export GIGACHAT_CREDENTIALS="ваш_ключ_авторизации"
export GIGACHAT_SCOPE="GIGACHAT_API_PERS"
export GIGACHAT_VERIFY_SSL_CERTS=False
export GIGACHAT_MODEL="GigaChat-Pro"
export GIGACHAT_BASE_URL="https://gigachat.devices.sberbank.ru/api/v1"
```

## Сертификаты и безопасность

Для корректной работы с API рекомендуется установить корневой сертификат НУЦ Минцифры:

```sh
curl -k "https://gu-st.ru/content/Other/doc/russian_trusted_root_ca.cer" -w "\n" >> $(python -m certifi)
```

После установки сертификата можно использовать `verify_ssl_certs=True` (по умолчанию).

Параметр `verify_ssl_certs=False` допустим только для тестирования. Отключение проверки сертификатов снижает безопасность.

### Авторизация по сертификатам (mTLS)

```python
giga = GigaChat(
    base_url="https://gigachat.devices.sberbank.ru/api/v1",
    ca_bundle_file="certs/ca.pem",
    cert_file="certs/tls.pem",
    key_file="certs/tls.key",
    key_file_password="password",
)
```

## Обработка ошибок

Библиотека предоставляет иерархию исключений для обработки ошибок:

```python
from gigachat import GigaChat
from gigachat.exceptions import GigaChatException, AuthenticationError, ResponseError

try:
    with GigaChat(credentials="...", verify_ssl_certs=False) as giga:
        response = giga.chat("Привет!")
except AuthenticationError:
    print("Ошибка авторизации. Проверьте ключ и scope.")
except ResponseError as e:
    print(f"Ошибка API: {e}")
except GigaChatException as e:
    print(f"Общая ошибка: {e}")
```

## Типизация

Библиотека использует Pydantic для моделей данных. Ответы API типизированы и поддерживают автодополнение в IDE:

```python
from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole

chat = Chat(
    messages=[
        Messages(role=MessagesRole.SYSTEM, content="Ты полезный ассистент."),
        Messages(role=MessagesRole.USER, content="Привет!"),
    ],
    temperature=0.7,
    max_tokens=100,
)

with GigaChat(credentials="...", verify_ssl_certs=False) as giga:
    response = giga.chat(chat)
    # response имеет тип ChatCompletion
    print(response.choices[0].message.content)
```

## Требования

Python 3.8 или выше.

Основные зависимости: `httpx`, `pydantic`.

## Участие в разработке

```sh
# Установка зависимостей
poetry install

# Запуск линтеров
make lint

# Запуск тестов
make test

# Форматирование кода
make fmt
```

Вопросы и предложения принимаются через [GitHub Issues](https://github.com/ai-forever/gigachat/issues).

## Лицензия

MIT
