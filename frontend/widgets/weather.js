/**
 * BeitBoard Widget: Weather
 * Показывает погоду для выбранного города
 */
Dashboard.registerWidget({
  type: 'weather',
  label: 'Погода',
  icon: '🌤',
  defaultW: 6, defaultH: 3,
  minW: 3, minH: 2,

  build(wid, config) {
    return `
      <div class="widget" id="widget-${wid}" data-wid="${wid}" data-config='${JSON.stringify(config||{})}'>
        <div class="widget-header">
          <div class="widget-dot" style="background:var(--accent)"></div>
          <div class="widget-title">Погода</div>
          <div class="widget-actions">
            <button class="w-btn" onclick="Dashboard.widgetConfig('${wid}')">⚙</button>
            <button class="w-btn" onclick="Dashboard.removeWidget('${wid}')">⊖</button>
          </div>
        </div>
        <div class="widget-body" id="weather-content-${wid}" style="display:flex;align-items:center;">
          <span style="color:var(--muted);padding:16px;font-size:11px">загрузка...</span>
        </div>
      </div>`;
  },

  async init(wid, config) {
    const cfg = config || {};
    const lat = cfg.lat || '45.0448';
    const lon = cfg.lon || '38.9760';
    const city = cfg.city || 'Краснодар';
    const el = document.getElementById('weather-content-' + wid);
    if (!el) return;
    try {
      const c = await Dashboard.api('GET', `/api/weather?lat=${lat}&lon=${lon}&city=${encodeURIComponent(city)}`);
      const codes = {0:'ясно',1:'почти ясно',2:'переменная облачность',3:'пасмурно',45:'туман',61:'дождь',63:'дождь',80:'ливень',95:'гроза'};
      el.innerHTML = `
        <div class="weather-body">
          <div class="weather-temp">${Math.round(c.temperature_2m)}°</div>
          <div class="weather-info">
            <div class="weather-desc">${codes[c.weathercode]||'—'}</div>
            <div class="weather-city">${c.city||city}</div>
          </div>
          <div class="weather-details">
            <div class="weather-item"><span class="wlabel">ощущается</span><span class="wval">${Math.round(c.apparent_temperature)}°</span></div>
            <div class="weather-item"><span class="wlabel">влажность</span><span class="wval">${c.relativehumidity_2m}%</span></div>
            <div class="weather-item"><span class="wlabel">ветер</span><span class="wval">${Math.round(c.windspeed_10m)} м/с</span></div>
          </div>
          <button class="weather-refresh" onclick="Dashboard.widgets['weather'].init('${wid}')">↻</button>
        </div>`;
    } catch(e) {
      el.innerHTML = '<span style="color:var(--muted);padding:16px">нет данных</span>';
    }
  },

  config: {
    fields: [
      { key: 'city', label: 'Город', type: 'city-search' }
    ]
  }
});
