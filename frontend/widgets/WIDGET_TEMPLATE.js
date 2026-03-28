/**
 * BeitBoard Widget Template
 * Скопируй этот файл, переименуй и измени под свой виджет
 * 
 * Для добавления виджета:
 * 1. Создай файл my_widget.js в папке widgets/
 * 2. Зарегистрируй через Dashboard.registerWidget({...})
 * 3. Обнови страницу — виджет появится в меню + ВИДЖЕТ
 */
Dashboard.registerWidget({
  // Уникальный тип — латиница, без пробелов
  type: 'my_widget',

  // Название в меню
  label: 'Мой виджет',

  // Иконка в меню
  icon: '🔧',

  // Размер по умолчанию (в ячейках GridStack, 12 колонок)
  defaultW: 3, defaultH: 4,
  minW: 2, minH: 2,

  /**
   * build(wid, config) — возвращает HTML виджета
   * wid — уникальный id экземпляра (например "my_widget-1234567890")
   * config — объект с настройками виджета
   */
  build(wid, config) {
    return `
      <div class="widget" id="widget-${wid}" data-wid="${wid}">
        <div class="widget-header">
          <div class="widget-dot" style="background:#888"></div>
          <div class="widget-title">Мой виджет</div>
          <div class="widget-actions">
            <button class="w-btn" onclick="Dashboard.removeWidget('${wid}')">⊖</button>
          </div>
        </div>
        <div class="widget-body" id="body-${wid}" style="padding:16px;">
          <p style="color:var(--muted)">Загрузка...</p>
        </div>
      </div>`;
  },

  /**
   * init(wid, config) — вызывается после добавления виджета на страницу
   * Здесь загружай данные и рендери содержимое
   */
  async init(wid, config) {
    const el = document.getElementById('body-' + wid);
    if (!el) return;
    // Пример: простой контент
    el.innerHTML = '<p style="color:var(--text)">Привет из моего виджета! 👋</p>';
    // Пример: запрос к API
    // const data = await Dashboard.api('GET', '/api/my-endpoint');
  }
});
