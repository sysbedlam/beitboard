# BeitBoard

Self-hosted dashboard для домашнего сервера и NAS.

**by [beit24.ru](https://beit24.ru)**

![BeitBoard](https://img.shields.io/badge/version-1.0-38bdf8) ![Docker](https://img.shields.io/badge/docker-compose-22c55e) ![Python](https://img.shields.io/badge/python-3.11-38bdf8)

**[🚀 Живое демо](https://dashboard.beit24.ru)** · **[📖 Страница проекта](https://beit24.ru/projects/beitboard.php)**

---

## Возможности

- 📌 **Секции со ссылками** — организуй ссылки в группы, перетаскивай для сортировки
- 🌤 **Виджеты** — погода, календарь, заметки, задачи
- 🔌 **Система плагинов** — добавляй свои виджеты одним JS файлом
- 🖼 **Фавиконы** — автоматически подтягиваются с сайтов, включая локальные ресурсы
- 🎨 **Иконки** — 1000+ иконок из [dashboard-icons](https://github.com/walkxcode/dashboard-icons)
- 🌙 **Тёмная/светлая тема**
- 📐 **Drag & Drop** — перетаскивай и изменяй размер виджетов
- 💾 **SQLite** — вся конфигурация хранится локально

---

## Быстрый старт

### Требования
- Docker
- Docker Compose

### Установка

```bash
git clone https://github.com/sysbedlam/beitboard.git
cd beitboard
docker compose up -d
```

Открой браузер: **http://localhost:8282**

### Synology NAS

1. Скопируй папку на NAS (например `/volume1/docker/beitboard/`)
2. В Container Manager → Проекты → Создать из папки
3. Открой через `http://nas-ip:8282`

Если используешь Nginx Proxy Manager — убери секцию `ports` из `docker-compose.yml`.

---

## Структура

```
beitboard/
├── backend/
│   ├── app.py              # Flask API
│   └── requirements.txt
├── frontend/
│   ├── index.html          # Главная страница
│   ├── widgets/            # Плагины виджетов
│   │   ├── clock.js        # Пример: часы
│   │   ├── cat.js          # Пример: котик
│   │   └── WIDGET_TEMPLATE.js  # Шаблон для своего виджета
│   └── gridstack-all.js    # GridStack (локально)
├── data/                   # База данных и кэш (не в git)
├── docker-compose.yml
└── nginx.conf
```

---

## Создание виджета

Скопируй `WIDGET_TEMPLATE.js` в `frontend/widgets/my_widget.js` и зарегистрируй:

```javascript
Dashboard.registerWidget({
  type: 'my_widget',
  label: 'Мой виджет',
  icon: '🔧',
  defaultW: 3, defaultH: 4,
  minW: 2, minH: 2,

  build(wid, config) {
    return `<div class="widget" id="widget-${wid}" data-wid="${wid}">
      ...твой HTML...
    </div>`;
  },

  async init(wid, config) {
    // загрузка данных
  }
});
```

Обнови страницу — виджет появится в меню **+ ДОБАВИТЬ**.

---

## Стек

| Компонент | Технология |
|-----------|-----------|
| Backend | Python 3.11, Flask, SQLite |
| Frontend | Vanilla JS, GridStack 10.3 |
| Proxy | nginx |
| Container | Docker Compose |

---

## Лицензия

MIT — используй свободно, звёздочку не забудь ⭐

---
Thanks Claude AI
*Built with ❤️ by [beit24.ru](https://beit24.ru)*
