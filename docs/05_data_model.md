# Модели данных 

##  Общая схема

Система использует SQLite базу данных с 8 основными таблицами.
Связи между таблицами организованы через внешние ключи.

## Таблицы 

### users

Хранит информацию о пользователях бота.

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | Integer | Первичный ключ |
| `telegram_id` | Integer, unique | ID пользователя в Telegram |
| `username` | String | Имя пользователя |
| `role` | String | Роль: `starosta` / `group_member` / `individual` |
| `group_id` | Integer, FK → groups.id | ID группы (если состоит) |
| `created_at` | DateTime | Дата регистрации |

### Group

Хранит информацию об учебных группах.

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | Integer | Первичный ключ |
| `group_code` | String, unique | Уникальный код для приглашения |
| `group_name` | String | Название группы |
| `starosta_id` | Integer | Telegram ID старосты |

### GroupMember(Base)

Связывает пользователей и группы (многие ко многим).

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | Integer | Первичный ключ |
| `group_id` | Integer, FK → groups.id | ID группы |
| `user_id` | Integer, FK → users.id | ID пользователя |

### Subject(Base):

Хранит предметы (могут быть общими для группы или личными).

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | Integer | Первичный ключ |
| `name` | String | Название предмета |
| `group_id` | Integer, FK → groups.id | Для предметов группы |
| `user_id` | Integer, FK → users.id | Для личных предметов |

### Task(Base):

Xранит задания.

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | Integer | Первичный ключ |
| `subject_id` | Integer, FK → subjects.id | Предмет |
| `title` | String | Название задания |
| `deadline` | DateTime | Дедлайн |
| `group_id` | Integer, FK → groups.id | Групповое/личное |
| `created_by` | Integer | Telegram ID создателя |

### UserTask(Base):

Связывает задания с пользователями.

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | Integer | Первичный ключ |
| `task_id` | Integer, FK → tasks.id | ID задания |
| `user_id` | Integer, FK → users.id | ID пользователя |
| `status` | String | Статус: `active` / `done` |
| `completed_at` | DateTime, nullable | Дедлайн |

### ReminderSetting(Base):

Индивидуальные настройки напоминаний.

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | Integer | Первичный ключ |
| `user_id` | Integer, FK → users.id, unique | ID пользователя |
| `mode` | String | Режим: `auto` / `custom` / `off` |
| `reminder_24h_time` | String, nullable | Время напоминания за 24 часа |
| `reminder_3h_enabled` | Boolean | Включено ли напоминание за 3 часа |

### Meme(Base):
Хранит мемы для мотивации.

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | Integer | Первичный ключ |
| `type` | String | Тип: `photo` / `text` |
| `content` | String | текст мема или путь к фото |