# Telegram aria2c Download Bot

Telegram-бот для управления загрузками через aria2c. Отправляете ссылку — файл скачивается на диск. Полный контроль: прогресс в реальном времени, пауза, отмена, inline-кнопки.

## Быстрый старт

```bash
cp .env.example .env
# Заполните BOT_TOKEN и ALLOWED_USER_ID в .env
docker compose up -d --build
```

Логи:

```bash
docker compose logs -f
```

## Архитектура

Два контейнера в Docker Compose:

| Контейнер | Образ | Роль |
|-----------|-------|------|
| `aria2` | Alpine + aria2c | Демон загрузок, JSON-RPC на порту 6800 |
| `bot` | Python 3.12-slim + aiogram v3 | Telegram-бот, подключается к aria2c по WebSocket |

```
Telegram → aiogram → AuthMiddleware → handlers
                                         ↓
                              aria2_client (WebSocket)
                                         ↓
                                    aria2c демон → ./downloads/
```

- Прогресс опрашивается каждые 5 секунд (`tellActive`)
- Завершение и ошибки приходят push-уведомлениями через WebSocket (`onDownloadComplete`, `onDownloadError`)
- Файлы сохраняются в bind-mount `./downloads`

## Переменные окружения

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `BOT_TOKEN` | Токен Telegram-бота (от @BotFather) | — |
| `ALLOWED_USER_ID` | Telegram ID пользователя, которому разрешён доступ | — |
| `ARIA2_RPC_SECRET` | Секрет для RPC-авторизации aria2c | `""` |
| `ARIA2_RPC_URL` | WebSocket URL aria2c | `ws://aria2:6800/jsonrpc` |
| `DOWNLOAD_DIR` | Директория загрузок внутри контейнера | `/downloads` |
| `USB_MOUNT_PATH` | Директория с USB-дисками в контейнере | `/usb` |
| `PROGRESS_UPDATE_INTERVAL` | Интервал обновления прогресса (секунды) | `5` |

## Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Приветствие |
| `/help` | Список команд |
| `/downloads` | Активные загрузки с inline-кнопками |
| `/stats` | Статистика aria2c (скорость, кол-во загрузок) |
| `/pause <gid>` | Поставить загрузку на паузу |
| `/resume <gid>` | Возобновить загрузку |
| `/cancel <gid>` | Отменить загрузку |
| `/pauseall` | Пауза всех загрузок |
| `/resumeall` | Возобновить все загрузки |
| `/cancelall` | Отменить все загрузки |
| `/copyusb` | Скопировать файл на USB-флешку |
| *(любой URL)* | Автоматически ставится на скачивание |

## Структура проекта

```
telegram_aria2c/
├── docker-compose.yml
├── .env.example
├── .gitignore
├── aria2/
│   ├── Dockerfile
│   ├── aria2.conf
│   └── entrypoint.sh
└── bot/
    ├── Dockerfile
    ├── requirements.txt
    ├── main.py
    ├── config.py
    ├── aria2_client.py
    ├── callback_types.py
    ├── handlers/
    │   ├── __init__.py
    │   ├── commands.py
    │   ├── downloads.py
    │   └── callbacks.py
    ├── middlewares/
    │   ├── __init__.py
    │   └── auth.py
    ├── services/
    │   ├── __init__.py
    │   ├── download_manager.py
    │   └── progress_updater.py
    └── utils/
        ├── __init__.py
        └── formatting.py
```

## Как получить BOT_TOKEN и ALLOWED_USER_ID

1. **BOT_TOKEN** — откройте [@BotFather](https://t.me/BotFather) в Telegram, создайте бота командой `/newbot`, скопируйте токен.
2. **ALLOWED_USER_ID** — отправьте любое сообщение боту [@userinfobot](https://t.me/userinfobot), он вернёт ваш числовой ID.

## Настройки aria2c

Конфигурация в `aria2/aria2.conf`:

- До 5 параллельных загрузок
- 16 соединений на сервер, split на 16 частей
- Докачка (`continue=true`)
- 64 MB disk-cache
