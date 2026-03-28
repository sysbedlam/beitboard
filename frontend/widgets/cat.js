/**
 * BeitBoard Widget: Cat 🐱
 * Котик который любит тебя
 */
Dashboard.registerWidget({
  type: 'cat',
  label: 'Котик',
  icon: '🐱',
  defaultW: 3, defaultH: 4,
  minW: 2, minH: 3,

  build(wid, config) {
    return `
      <div class="widget" id="widget-${wid}" data-wid="${wid}">
        <div class="widget-header">
          <div class="widget-dot" style="background:#f472b6"></div>
          <div class="widget-title">Котик</div>
          <div class="widget-actions">
            <button class="w-btn" onclick="Dashboard.removeWidget('${wid}')">⊖</button>
          </div>
        </div>
        <div class="widget-body" id="cat-body-${wid}" style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;gap:12px;cursor:pointer;user-select:none;" onclick="catPet('${wid}')">
          <div id="cat-face-${wid}" style="font-size:52px;transition:transform .15s;">🐱</div>
          <div id="cat-phrase-${wid}" style="font-size:11px;color:var(--muted);text-align:center;min-height:16px;transition:opacity .3s;font-family:'JetBrains Mono',monospace;"></div>
          <div id="cat-hearts-${wid}" style="font-size:18px;min-height:24px;letter-spacing:4px;"></div>
        </div>
      </div>`;
  },

  init(wid, config) {
    // Показываем начальную фразу через секунду
    setTimeout(() => {
      const phrase = document.getElementById('cat-phrase-' + wid);
      if (phrase) phrase.textContent = 'погладь меня...';
    }, 800);
  }
});

const CAT_PHRASES = [
  'мурр... 😊',
  'я тебя люблю!',
  'ты лучший!',
  'мяу~ ♡',
  'ещё! ещё!',
  'пурр-пурр-пурр...',
  '*топчется лапками*',
  'никуда не уходи',
  'мне хорошо с тобой',
  'мур-р-р-р...',
  'ты мой любимый человек',
  'дай ещё почешу',
  '*трётся об тебя*',
  'я сыт и счастлив',
  'буду тут сидеть',
];

const CAT_FACES = ['😸','😻','🐱','😺','🥰'];
const CAT_ANGRY = ['😾','🙀'];

let _catPetCount = {};
let _catTimer = {};

window.catPet = function(wid) {
  const face = document.getElementById('cat-face-' + wid);
  const phrase = document.getElementById('cat-phrase-' + wid);
  const hearts = document.getElementById('cat-hearts-' + wid);
  if (!face) return;

  _catPetCount[wid] = (_catPetCount[wid] || 0) + 1;
  const count = _catPetCount[wid];

  // Анимация
  face.style.transform = 'scale(1.3) rotate(-10deg)';
  setTimeout(() => face.style.transform = 'scale(1)', 150);

  // Меняем морду
  face.textContent = CAT_FACES[Math.floor(Math.random() * CAT_FACES.length)];

  // Фраза
  const p = CAT_PHRASES[Math.floor(Math.random() * CAT_PHRASES.length)];
  if (phrase) {
    phrase.style.opacity = '0';
    setTimeout(() => {
      phrase.textContent = p;
      phrase.style.opacity = '1';
    }, 150);
  }

  // Сердечки — больше погладил, больше любви
  if (hearts) {
    const h = Math.min(count, 5);
    hearts.textContent = '♡'.repeat(h);
    hearts.style.color = '#f472b6';
  }

  // Если очень много — котик устал
  if (count > 0 && count % 10 === 0) {
    face.textContent = '😹';
    if (phrase) phrase.textContent = 'хватит! хватит! мяу!';
    setTimeout(() => {
      face.textContent = '😸';
      if (phrase) phrase.textContent = 'ладно... ещё немного';
      _catPetCount[wid] = 0;
      if (hearts) hearts.textContent = '';
    }, 2000);
  }

  // Сбрасываем счётчик если долго не гладили
  clearTimeout(_catTimer[wid]);
  _catTimer[wid] = setTimeout(() => {
    _catPetCount[wid] = 0;
    if (face) face.textContent = '🐱';
    if (phrase) phrase.textContent = 'погладь меня...';
    if (hearts) hearts.textContent = '';
  }, 10000);
};
