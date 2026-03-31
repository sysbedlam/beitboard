/**
 * BeitBoard Widget: Тамагочи 🥚
 * Виртуальный питомец с уходом и развитием
 */
Dashboard.registerWidget({
  type: 'tamagochi',
  label: 'Тамагочи',
  icon: '🥚',
  defaultW: 3, defaultH: 5,
  minW: 2, minH: 4,

  build(wid, config) {
    return `
      <div class="widget" id="widget-${wid}" data-wid="${wid}" data-config='${JSON.stringify(config||{})}'>
        <div class="widget-header">
          <div class="widget-dot" style="background:#f472b6"></div>
          <div class="widget-title" id="tama-title-${wid}">Тамагочи</div>
          <div class="widget-actions">
            <button class="w-btn" onclick="tamaReset('${wid}')">↺</button>
            <button class="w-btn" onclick="Dashboard.removeWidget('${wid}')">⊖</button>
          </div>
        </div>
        <div class="widget-body" id="tama-body-${wid}" style="display:flex;flex-direction:column;align-items:center;padding:10px 12px;gap:8px;height:100%;">
          <div style="color:var(--muted);font-size:11px;">загрузка...</div>
        </div>
      </div>`;
  },

  async init(wid, config) {
    const cfg = config && Object.keys(config).length ? config : null;
    if (!cfg || !cfg.pet) {
      tamaShowPicker(wid);
    } else {
      tamaRender(wid, cfg);
      tamaStartTick(wid);
    }
  }
});

// ── Питомцы ────────────────────────────────────────────
const TAMA_PETS = {
  cat:  { emoji: '🐱', name: 'Котик',   phrases: { happy:'Мурр~ ♡', hungry:'Мяу! Есть хочу!', thirsty:'Мяу... пить...', bored:'Поиграй со мной!', tired:'Zzzz...', sick:'Мне плохо...', joy:'МУРРРР!! ♡♡♡' }},
  dog:  { emoji: '🐶', name: 'Собака',  phrases: { happy:'Гав! Всё хорошо!', hungry:'Гав-гав! Кушать!', thirsty:'Гав... пить...', bored:'Играть! Играть!', tired:'Хр-хр...', sick:'Тихий скулёж...', joy:'ГАВ-ГАВ-ГАВ!! 🎉' }},
  hamster:{ emoji:'🐹', name:'Хомяк',  phrases: { happy:'Пи-пи~ всё ок!', hungry:'Пи! Пи! Кушать!', thirsty:'Пи-пи... водички', bored:'Пи-пи! Беги со мной!', tired:'Zz...Zz...', sick:'Пи... плохо...', joy:'ПИ-ПИ-ПИ!! ✨' }},
  fox:  { emoji: '🦊', name: 'Лиса',   phrases: { happy:'Всё прекрасно~', hungry:'Эй! Я голодна!', thirsty:'Хочу воды...', bored:'Скучно... давай играть', tired:'Сплю...', sick:'Мне нехорошо...', joy:'УРА! Я счастлива! ♡' }},
  frog: { emoji: '🐸', name: 'Лягушка',phrases: { happy:'Ква~ хорошо!', hungry:'КВА! Хочу есть!', thirsty:'Ква... водичка...', bored:'КВА! Прыгнем вместе?', tired:'кваа...zz...', sick:'Ква... болею...', joy:'КВА-КВА-КВА!! 🎊' }},
};

const TAMA_STAGES = [
  { name: 'Яйцо',   min: 0,   emoji: '🥚' },
  { name: 'Малыш',  min: 5,   emoji: null }, // берём из питомца
  { name: 'Юный',   min: 20,  emoji: null },
  { name: 'Взрослый',min:50,  emoji: null },
  { name: 'Мудрый', min: 100, emoji: null },
];

// ── Состояние ──────────────────────────────────────────
function tamaGetState(wid) {
  const el = document.getElementById('widget-' + wid);
  try { return JSON.parse(el?.dataset.config || '{}'); } catch { return {}; }
}

async function tamaSave(wid, state) {
  const el = document.getElementById('widget-' + wid);
  if (el) el.dataset.config = JSON.stringify(state);
  await Dashboard.api('PUT', `/api/widgets/${wid}/config`, state);
}

// ── Выбор питомца ──────────────────────────────────────
function tamaShowPicker(wid) {
  const body = document.getElementById('tama-body-' + wid);
  if (!body) return;
  body.innerHTML = `
    <div style="font-family:'Unbounded',sans-serif;font-size:9px;letter-spacing:2px;color:var(--muted);margin-bottom:4px;">ВЫБЕРИ ПИТОМЦА</div>
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;width:100%;">
      ${Object.entries(TAMA_PETS).map(([key, p]) => `
        <div onclick="tamaCreate('${wid}','${key}')"
          style="display:flex;flex-direction:column;align-items:center;gap:4px;padding:10px 6px;background:var(--surface2);border:1px solid var(--border2);border-radius:10px;cursor:pointer;transition:all .15s;"
          onmouseover="this.style.borderColor='var(--accent)'"
          onmouseout="this.style.borderColor='var(--border2)'">
          <span style="font-size:28px;">${p.emoji}</span>
          <span style="font-size:10px;color:var(--muted);">${p.name}</span>
        </div>`).join('')}
    </div>`;
}

async function tamaCreate(wid, petKey) {
  const state = {
    pet: petKey,
    name: TAMA_PETS[petKey].name,
    hunger: 80,
    thirst: 80,
    mood: 80,
    energy: 80,
    age: 0,          // количество уходов
    lastTick: Date.now(),
    born: Date.now(),
  };
  await tamaSave(wid, state);
  tamaRender(wid, state);
  tamaStartTick(wid);
}

// ── Рендер ─────────────────────────────────────────────
function tamaRender(wid, state) {
  const body = document.getElementById('tama-body-' + wid);
  const title = document.getElementById('tama-title-' + wid);
  if (!body) return;

  const pet = TAMA_PETS[state.pet];
  if (!pet) { tamaShowPicker(wid); return; }

  // Стадия развития
  const stage = TAMA_STAGES.slice().reverse().find(s => state.age >= s.min) || TAMA_STAGES[0];
  const emoji = stage.min === 0 ? '🥚' : pet.emoji;

  if (title) title.textContent = state.name || pet.name;

  // Состояние питомца
  const avg = (state.hunger + state.thirst + state.mood + state.energy) / 4;
  let phrase = pet.phrases.happy;
  let faceStyle = '';

  if (state.energy < 20) { phrase = pet.phrases.tired; faceStyle = 'opacity:0.6;'; }
  else if (state.hunger < 20) phrase = pet.phrases.hungry;
  else if (state.thirst < 20) phrase = pet.phrases.thirsty;
  else if (state.mood < 20) phrase = pet.phrases.bored;
  else if (avg < 30) { phrase = pet.phrases.sick; faceStyle = 'filter:grayscale(0.5);'; }

  // Дни жизни
  const days = Math.floor((Date.now() - (state.born || Date.now())) / 86400000);

  body.innerHTML = `
    <div style="font-size:11px;color:var(--muted);letter-spacing:1px;">${stage.name} · ${days} дн.</div>

    <div id="tama-face-${wid}" style="font-size:56px;line-height:1;cursor:pointer;transition:transform .2s;${faceStyle}"
      onclick="tamaPet('${wid}')" title="Погладить">${emoji}</div>

    <div style="font-size:11px;color:var(--muted);text-align:center;min-height:16px;" id="tama-phrase-${wid}">${phrase}</div>

    <div style="width:100%;display:flex;flex-direction:column;gap:5px;">
      ${tamaBar('🍖', 'Еда',      state.hunger, '#f97316')}
      ${tamaBar('💧', 'Вода',     state.thirst, '#38bdf8')}
      ${tamaBar('😊', 'Настрой',  state.mood,   '#f472b6')}
      ${tamaBar('⚡', 'Энергия',  state.energy, '#22c55e')}
    </div>

    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:5px;width:100%;margin-top:auto;">
      <button onclick="tamaAction('${wid}','feed')"    style="${tamaBtnStyle('#f97316')}">🍖<br><span style="font-size:9px;">Кормить</span></button>
      <button onclick="tamaAction('${wid}','drink')"   style="${tamaBtnStyle('#38bdf8')}">💧<br><span style="font-size:9px;">Поить</span></button>
      <button onclick="tamaAction('${wid}','play')"    style="${tamaBtnStyle('#f472b6')}">🎮<br><span style="font-size:9px;">Играть</span></button>
      <button onclick="tamaAction('${wid}','sleep')"   style="${tamaBtnStyle('#22c55e')}">😴<br><span style="font-size:9px;">Спать</span></button>
    </div>`;
}

function tamaBar(icon, label, value, color) {
  const v = Math.max(0, Math.min(100, value));
  const col = v < 20 ? '#f87171' : v < 50 ? '#fbbf24' : color;
  return `
    <div style="display:flex;align-items:center;gap:6px;">
      <span style="font-size:12px;width:16px;">${icon}</span>
      <div style="flex:1;background:var(--surface2);border-radius:4px;height:6px;overflow:hidden;">
        <div style="width:${v}%;height:100%;background:${col};border-radius:4px;transition:width .4s;"></div>
      </div>
      <span style="font-size:10px;color:var(--muted);width:28px;text-align:right;">${Math.round(v)}%</span>
    </div>`;
}

function tamaBtnStyle(color) {
  return `background:var(--surface2);border:1px solid var(--border2);border-radius:8px;padding:6px 4px;cursor:pointer;color:var(--text);font-size:16px;line-height:1.3;transition:all .15s;width:100%;font-family:'JetBrains Mono',monospace;` +
    `onmouseover="this.style.borderColor='${color}'"`;
}

// ── Действия ───────────────────────────────────────────
async function tamaAction(wid, action) {
  const state = tamaGetState(wid);
  const pet = TAMA_PETS[state.pet];
  if (!pet) return;

  const face = document.getElementById('tama-face-' + wid);
  const phrase = document.getElementById('tama-phrase-' + wid);

  // Анимация
  if (face) {
    face.style.transform = 'scale(1.4)';
    setTimeout(() => face.style.transform = 'scale(1)', 300);
  }

  switch(action) {
    case 'feed':
      state.hunger = Math.min(100, (state.hunger||0) + 25);
      state.mood   = Math.min(100, (state.mood||0) + 5);
      if (phrase) phrase.textContent = '😋 ' + (state.hunger > 80 ? 'Объелся немного...' : pet.phrases.joy);
      break;
    case 'drink':
      state.thirst = Math.min(100, (state.thirst||0) + 25);
      state.mood   = Math.min(100, (state.mood||0) + 5);
      if (phrase) phrase.textContent = '💧 ' + (state.thirst > 80 ? 'Хватит, спасибо!' : pet.phrases.joy);
      break;
    case 'play':
      state.mood   = Math.min(100, (state.mood||0) + 30);
      state.energy = Math.max(0,   (state.energy||0) - 10);
      state.hunger = Math.max(0,   (state.hunger||0) - 5);
      if (phrase) phrase.textContent = '🎮 ' + pet.phrases.joy;
      break;
    case 'sleep':
      state.energy = Math.min(100, (state.energy||0) + 35);
      state.mood   = Math.min(100, (state.mood||0) + 5);
      if (phrase) phrase.textContent = '😴 Хорошо поспал!';
      break;
  }

  state.age = (state.age || 0) + 1;
  await tamaSave(wid, state);

  // Перерисовываем шкалы
  setTimeout(() => tamaRender(wid, state), 400);
}

// Погладить
async function tamaPet(wid) {
  const state = tamaGetState(wid);
  const pet = TAMA_PETS[state.pet];
  if (!pet) return;
  state.mood = Math.min(100, (state.mood||0) + 10);
  state.age = (state.age || 0) + 1;
  const face = document.getElementById('tama-face-' + wid);
  const phrase = document.getElementById('tama-phrase-' + wid);
  if (face) { face.style.transform = 'scale(1.2) rotate(-5deg)'; setTimeout(()=>face.style.transform='scale(1)',200); }
  if (phrase) phrase.textContent = '🥰 ' + pet.phrases.happy;
  await tamaSave(wid, state);
}

// Сброс
async function tamaReset(wid) {
  if (!confirm('Завести нового питомца?')) return;
  await tamaSave(wid, {});
  const el = document.getElementById('widget-' + wid);
  if (el) el.dataset.config = '{}';
  clearInterval(window['_tama_' + wid]);
  tamaShowPicker(wid);
}

// ── Тик — шкалы падают со временем ────────────────────
function tamaStartTick(wid) {
  clearInterval(window['_tama_' + wid]);

  // Проверяем сразу при загрузке
  tamaTickCheck(wid);

  // И каждые 5 минут
  window['_tama_' + wid] = setInterval(() => tamaTickCheck(wid), 5 * 60 * 1000);
}

async function tamaTickCheck(wid) {
  const state = tamaGetState(wid);
  if (!state.pet) return;

  const now = Date.now();
  const last = state.lastTick || now;
  const elapsed = now - last; // миллисекунды

  // За каждый час -5 от каждой шкалы
  const hours = elapsed / 3600000;
  if (hours < 0.08) return; // меньше 5 минут — не трогаем

  state.hunger = Math.max(0, (state.hunger||80) - hours * 5);
  state.thirst = Math.max(0, (state.thirst||80) - hours * 7); // жажда быстрее
  state.mood   = Math.max(0, (state.mood||80)   - hours * 3);
  state.energy = Math.max(0, (state.energy||80) - hours * 2);
  state.lastTick = now;

  await tamaSave(wid, state);
  tamaRender(wid, state);
}
