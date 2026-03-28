/**
 * BeitBoard Widget: Clock
 * Часы с выбором города/часового пояса
 */
Dashboard.registerWidget({
  type: 'clock',
  label: 'Часы',
  icon: '🕐',
  defaultW: 3, defaultH: 3,
  minW: 2, minH: 2,

  build(wid, config) {
    return `
      <div class="widget" id="widget-${wid}" data-wid="${wid}" data-config='${JSON.stringify(config||{})}'>
        <div class="widget-header">
          <div class="widget-dot" style="background:var(--accent2)"></div>
          <div class="widget-title">Часы</div>
          <div class="widget-actions">
            <button class="w-btn" onclick="clockConfig('${wid}')">⚙</button>
            <button class="w-btn" onclick="Dashboard.removeWidget('${wid}')">⊖</button>
          </div>
        </div>
        <div class="widget-body" id="clock-body-${wid}" style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;gap:4px;">
          <div id="clock-time-${wid}" style="font-family:'JetBrains Mono',monospace;font-size:36px;font-weight:700;color:var(--text);letter-spacing:2px;">--:--:--</div>
          <div id="clock-date-${wid}" style="font-size:11px;color:var(--muted);letter-spacing:1px;"></div>
          <div id="clock-city-${wid}" style="font-size:10px;color:var(--accent);letter-spacing:2px;text-transform:uppercase;margin-top:4px;"></div>
        </div>
      </div>`;
  },

  init(wid, config) {
    const cfg = config || {};
    const tz = cfg.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone;
    const city = cfg.city || 'Местное время';

    document.getElementById('clock-city-' + wid).textContent = city;

    // Запускаем тикание
    function tick() {
      const now = new Date();
      const timeEl = document.getElementById('clock-time-' + wid);
      const dateEl = document.getElementById('clock-date-' + wid);
      if (!timeEl) return; // виджет удалён

      const timeStr = now.toLocaleTimeString('ru-RU', {
        timeZone: tz,
        hour: '2-digit', minute: '2-digit', second: '2-digit'
      });
      const dateStr = now.toLocaleDateString('ru-RU', {
        timeZone: tz,
        weekday: 'long', day: 'numeric', month: 'long'
      });

      timeEl.textContent = timeStr;
      dateEl.textContent = dateStr;
    }

    tick();
    // Сохраняем interval id чтобы можно было остановить
    window['_clock_' + wid] = setInterval(tick, 1000);
  }
});

// Конфиг виджета часов
window.clockConfig = function(wid) {
  const timezones = [
    { city: 'Москва',          tz: 'Europe/Moscow' },
    { city: 'Краснодар',       tz: 'Europe/Moscow' },
    { city: 'Санкт-Петербург', tz: 'Europe/Moscow' },
    { city: 'Екатеринбург',    tz: 'Asia/Yekaterinburg' },
    { city: 'Новосибирск',     tz: 'Asia/Novosibirsk' },
    { city: 'Владивосток',     tz: 'Asia/Vladivostok' },
    { city: 'Лондон',          tz: 'Europe/London' },
    { city: 'Берлин',          tz: 'Europe/Berlin' },
    { city: 'Париж',           tz: 'Europe/Paris' },
    { city: 'Дубай',           tz: 'Asia/Dubai' },
    { city: 'Токио',           tz: 'Asia/Tokyo' },
    { city: 'Пекин',           tz: 'Asia/Shanghai' },
    { city: 'Нью-Йорк',       tz: 'America/New_York' },
    { city: 'Лос-Анджелес',   tz: 'America/Los_Angeles' },
  ];

  const widgetEl = document.getElementById('widget-' + wid);
  let cfg = {};
  try { cfg = JSON.parse(widgetEl?.dataset.config || '{}'); } catch(e) {}

  const select = timezones.map(t =>
    `<option value="${t.tz}" data-city="${t.city}" ${cfg.timezone === t.tz ? 'selected' : ''}>${t.city}</option>`
  ).join('');

  // Простой prompt-like диалог
  const modal = document.createElement('div');
  modal.style.cssText = `position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:1000;display:flex;align-items:center;justify-content:center;`;
  modal.innerHTML = `
    <div style="background:var(--surface);border:1px solid var(--border2);border-radius:14px;padding:24px;min-width:280px;">
      <div style="font-family:'Unbounded',sans-serif;font-size:11px;letter-spacing:2px;color:var(--muted);margin-bottom:16px;">НАСТРОЙКИ ЧАСОВ</div>
      <select id="clock-tz-select" style="width:100%;background:var(--surface2);border:1px solid var(--border2);border-radius:8px;padding:8px 12px;color:var(--text);font-family:'JetBrains Mono',monospace;font-size:12px;outline:none;">
        ${select}
      </select>
      <div style="display:flex;gap:8px;margin-top:16px;justify-content:flex-end;">
        <button onclick="this.closest('div[style*=fixed]').remove()" style="background:none;border:1px solid var(--border2);border-radius:8px;padding:7px 16px;color:var(--muted);cursor:pointer;font-size:12px;">Отмена</button>
        <button id="clock-save-btn" style="background:var(--accent);border:none;border-radius:8px;padding:7px 16px;color:#0f172a;cursor:pointer;font-size:12px;font-weight:600;">Сохранить</button>
      </div>
    </div>`;

  document.body.appendChild(modal);

  document.getElementById('clock-save-btn').onclick = async () => {
    const sel = document.getElementById('clock-tz-select');
    const tz = sel.value;
    const city = sel.options[sel.selectedIndex].dataset.city;
    const config = { timezone: tz, city };

    // Сохраняем в БД
    await Dashboard.api('PUT', `/api/widgets/${wid}/config`, config);

    // Обновляем data-config
    if (widgetEl) widgetEl.dataset.config = JSON.stringify(config);

    // Перезапускаем часы
    clearInterval(window['_clock_' + wid]);
    document.getElementById('clock-city-' + wid).textContent = city;
    Dashboard.widgets['clock'].init(wid, config);

    modal.remove();
  };
};
