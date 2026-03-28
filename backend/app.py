from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3, os, urllib.request, urllib.parse, json

app = Flask(__name__)
CORS(app)

DB_PATH = os.environ.get('DB_PATH', '/data/dashboard.db')

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")  # WAL позволяет параллельные чтения
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS sections (
        id    INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        color TEXT NOT NULL DEFAULT 'accent'
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS links (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        section_id INTEGER NOT NULL,
        name       TEXT NOT NULL,
        url        TEXT NOT NULL,
        icon       TEXT,
        position   INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY (section_id) REFERENCES sections(id) ON DELETE CASCADE
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS notes (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        content    TEXT NOT NULL DEFAULT '',
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS todos (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        text       TEXT NOT NULL,
        done       INTEGER NOT NULL DEFAULT 0,
        position   INTEGER NOT NULL DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # Таблица виджетов — позиции и размеры в GridStack
    c.execute('''CREATE TABLE IF NOT EXISTS widgets (
        id      TEXT PRIMARY KEY,
        x       INTEGER NOT NULL DEFAULT 0,
        y       INTEGER NOT NULL DEFAULT 0,
        w       INTEGER NOT NULL DEFAULT 2,
        h       INTEGER NOT NULL DEFAULT 3,
        min_w   INTEGER NOT NULL DEFAULT 1,
        min_h   INTEGER NOT NULL DEFAULT 2,
        visible INTEGER NOT NULL DEFAULT 1,
        type    TEXT
    )''')
    # Add type column if missing (migration)
    try:
        c.execute('ALTER TABLE widgets ADD COLUMN type TEXT')
    except:
        pass
    try:
        c.execute('ALTER TABLE widgets ADD COLUMN config TEXT')
    except:
        pass

    # Настройки приложения
    c.execute('''CREATE TABLE IF NOT EXISTS settings (
        key   TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )''')

    # Дефолтный город
    c.execute("INSERT OR IGNORE INTO settings (key,value) VALUES ('weather_city','Краснодар')")
    c.execute("INSERT OR IGNORE INTO settings (key,value) VALUES ('weather_lat','45.0448')")
    c.execute("INSERT OR IGNORE INTO settings (key,value) VALUES ('weather_lon','38.9760')")

    # Seed sections если пусто — убрано для чистого старта
    # if c.execute('SELECT COUNT(*) FROM sections').fetchone()[0] == 0:
    #     _seed(c)

    # Seed notes
    if c.execute('SELECT COUNT(*) FROM notes').fetchone()[0] == 0:
        c.execute('INSERT INTO notes (content) VALUES (?)', ('',))

    # Системные виджеты НЕ создаются автоматически — пользователь добавляет сам

    conn.commit()
    conn.close()

def _seed(c):
    sections = [
        ('Работа',   'accent',  0, 2, 3, 1, 2),
        ('Обучение', 'accent2', 2, 3, 2, 1, 2),
        ('Сервисы',  'danger',  4, 3, 2, 1, 2),
        ('Роутеры',  'accent3', 0, 3, 4, 2, 3),
        ('NAS',      'accent4', 4, 5, 4, 2, 3),
    ]
    for title, color, x, y, w, min_w, min_h in sections:
        c.execute('INSERT INTO sections (title, color) VALUES (?,?)', (title, color))
        sid = c.lastrowid
        c.execute('''INSERT OR IGNORE INTO widgets (id,x,y,w,h,min_w,min_h)
                     VALUES (?,?,?,?,?,?,?)''', (f'section-{sid}', x, y, w, 4, min_w, min_h))

    rows = c.execute('SELECT id, title FROM sections').fetchall()
    sid = {r['title']: r['id'] for r in rows}

    links = {
        'Работа':   [('ASK','https://ask.kivit.ru/servicedesk/','AS'),
                     ('Мониторинг','https://moon2.itmgt.ru/','MN'),
                     ('Отчет','https://ask.kivit.ru/servicedesk/matrix/','RP')],
        'Обучение': [('SkillFactory','https://student-lk.skillfactory.ru/my-study','SF')],
        'Сервисы':  [('Beit24.ru','https://beit24.ru','BT'),
                     ('ipsecgen','https://ipsecgen.beit24.ru','IP'),
                     ('Nginx Proxy','http://192.168.0.50:8181/','NX')],
        'Роутеры':  [('Routerich','http://192.168.0.1','RT'),
                     ('Xiaomiwrt','http://192.168.0.2','XI'),
                     ('Travel WRT','http://192.168.10.1','TR'),
                     ('Keenetic M','http://192.168.1.1','KM'),
                     ('Keenetic B','http://192.168.2.1','KB'),
                     ('Mikrotik','http://192.168.0.100','MK')],
        'NAS':      [('NAS','http://192.168.0.50','NS'),
                     ('MNAS','http://192.168.1.40','MN'),
                     ('Drive','https://nas.beit24.ru/drive','DR'),
                     ('Контакты','https://nas.beit24.ru/contacts/','CN'),
                     ('Загрузки','https://nas.beit24.ru/download/','DL'),
                     ('Заметки','https://nas.beit24.ru/note','ZM'),
                     ('Photo','https://mnas.beit24.ru/photo','PH'),
                     ('Video','http://nas.beit24.ru/cam','VD')],
    }
    for section_title, items in links.items():
        for pos, (name, url, icon) in enumerate(items):
            c.execute('INSERT INTO links (section_id,name,url,icon,position) VALUES (?,?,?,?,?)',
                      (sid[section_title], name, url, icon, pos))

# ── Weather (серверный прокси) ────────────────────────

# Weather cache per lat/lon key
import time as _time
_weather_cache = {}

@app.route('/api/weather')
def get_weather():
    # Параметры из query string — каждый виджет передаёт свои
    lat = request.args.get('lat', '45.0448')
    lon = request.args.get('lon', '38.9760')
    city = request.args.get('city', 'Краснодар')
    cache_key = f'{lat},{lon}'
    now = _time.time()
    cached = _weather_cache.get(cache_key)
    if cached and now - cached['ts'] < 600:
        return jsonify(cached['data'])
    try:
        url = (f'https://api.open-meteo.com/v1/forecast'
               f'?latitude={lat}&longitude={lon}'
               f'&current=temperature_2m,apparent_temperature,weathercode,windspeed_10m,relativehumidity_2m'
               f'&wind_speed_unit=ms&timezone=auto')
        with urllib.request.urlopen(url, timeout=3) as r:
            data = json.loads(r.read())
        result = dict(data['current'])
        result['city'] = city
        _weather_cache[cache_key] = {'data': result, 'ts': now}
        return jsonify(result)
    except Exception as e:
        if cached:
            return jsonify(cached['data'])
        return jsonify({'error': str(e)}), 502

@app.route('/api/settings', methods=['GET'])
def get_settings():
    conn = get_db()
    rows = conn.execute('SELECT key,value FROM settings').fetchall()
    conn.close()
    return jsonify({r['key']: r['value'] for r in rows})

@app.route('/api/settings', methods=['PUT'])
def save_settings():
    conn = get_db()
    for key, value in request.json.items():
        conn.execute('INSERT OR REPLACE INTO settings (key,value) VALUES (?,?)', (key, value))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

# Геокодинг — поиск города по имени через Open-Meteo geocoding
@app.route('/api/geocode')
def geocode():
    name = request.args.get('name','')
    try:
        url = f'https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(name)}&count=5&language=ru'
        with urllib.request.urlopen(url, timeout=3) as r:
            data = json.loads(r.read())
        results = data.get('results', [])
        return jsonify([{'name': r['name'], 'country': r.get('country',''), 
                         'lat': r['latitude'], 'lon': r['longitude']} for r in results])
    except Exception as e:
        return jsonify({'error': str(e)}), 502

# ── Widgets (GridStack layout) ────────────────────────

@app.route('/api/widgets', methods=['GET'])
def get_widgets():
    conn = get_db()
    rows = conn.execute('SELECT * FROM widgets').fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/widgets', methods=['POST'])
def create_widget():
    data = request.json
    conn = get_db()
    conn.execute('''INSERT OR IGNORE INTO widgets (id,x,y,w,h,min_w,min_h,visible,type,config)
                    VALUES (?,?,?,?,?,?,?,1,?,?)''',
                 (data['id'], data.get('x',0), data.get('y',0),
                  data.get('w',3), data.get('h',4),
                  data.get('min_w',1), data.get('min_h',2),
                  data.get('type'),
                  json.dumps(data.get('config')) if data.get('config') else None))
    conn.commit()
    conn.close()
    return jsonify({'ok': True}), 201

@app.route('/api/widgets', methods=['PUT'])
def save_widgets():
    items = request.json  # [{id, x, y, w, h}, ...]
    conn = get_db()
    for item in items:
        wid = item.get('id')
        x = item.get('x', 0)
        y = item.get('y', 0)
        w = item.get('w', 2)
        h = item.get('h', 3)
        # INSERT OR REPLACE — создаёт если нет, обновляет если есть
        conn.execute('''INSERT INTO widgets (id,x,y,w,h,min_w,min_h,visible)
                        VALUES (?,?,?,?,?,
                          COALESCE((SELECT min_w FROM widgets WHERE id=?),1),
                          COALESCE((SELECT min_h FROM widgets WHERE id=?),2),
                          COALESCE((SELECT visible FROM widgets WHERE id=?),1))
                        ON CONFLICT(id) DO UPDATE SET x=?,y=?,w=?,h=?
                     ''', (wid,x,y,w,h, wid,wid,wid, x,y,w,h))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

@app.route('/api/widgets/<wid>/config', methods=['PUT'])
def save_widget_config(wid):
    conn = get_db()
    conn.execute('UPDATE widgets SET config=? WHERE id=?',
                 (json.dumps(request.json), wid))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

@app.route('/api/widgets/<wid>', methods=['DELETE'])
def delete_widget(wid):
    conn = get_db()
    conn.execute('DELETE FROM widgets WHERE id=?', (wid,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

# ── Sections ──────────────────────────────────────────

@app.route('/api/sections', methods=['GET'])
def get_sections():
    conn = get_db()
    sections = conn.execute('SELECT * FROM sections').fetchall()
    result = []
    for s in sections:
        links = conn.execute(
            'SELECT * FROM links WHERE section_id=? ORDER BY position', (s['id'],)
        ).fetchall()
        widget = conn.execute(
            'SELECT * FROM widgets WHERE id=?', (f"section-{s['id']}",)
        ).fetchone()
        result.append({
            **dict(s),
            'links': [dict(l) for l in links],
            'widget': dict(widget) if widget else None
        })
    conn.close()
    return jsonify(result)

@app.route('/api/sections', methods=['POST'])
def create_section():
    data = request.json
    conn = get_db()
    cur = conn.execute('INSERT INTO sections (title,color) VALUES (?,?)',
                       (data['title'], data.get('color','accent')))
    sid = cur.lastrowid
    # Дефолтная позиция — в конец
    max_y = conn.execute("SELECT COALESCE(MAX(y+h),0) FROM widgets").fetchone()[0]
    conn.execute('INSERT OR IGNORE INTO widgets (id,x,y,w,h,min_w,min_h) VALUES (?,?,?,?,?,?,?)',
                 (f'section-{sid}', 0, max_y, 3, 4, 1, 2))
    conn.commit()
    row = conn.execute('SELECT * FROM sections WHERE id=?', (sid,)).fetchone()
    widget = conn.execute('SELECT * FROM widgets WHERE id=?', (f'section-{sid}',)).fetchone()
    conn.close()
    return jsonify({**dict(row), 'links': [], 'widget': dict(widget)}), 201

@app.route('/api/sections/<int:sid>', methods=['PUT'])
def update_section(sid):
    data = request.json
    conn = get_db()
    conn.execute('UPDATE sections SET title=?, color=? WHERE id=?',
                 (data['title'], data.get('color','accent'), sid))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

@app.route('/api/sections/<int:sid>', methods=['DELETE'])
def delete_section(sid):
    conn = get_db()
    conn.execute('DELETE FROM links WHERE section_id=?', (sid,))
    conn.execute('DELETE FROM sections WHERE id=?', (sid,))
    conn.execute('DELETE FROM widgets WHERE id=?', (f'section-{sid}',))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

# ── Links ─────────────────────────────────────────────

@app.route('/api/sections/<int:sid>/links', methods=['POST'])
def create_link(sid):
    data = request.json
    conn = get_db()
    max_pos = conn.execute('SELECT COALESCE(MAX(position),0) FROM links WHERE section_id=?',
                           (sid,)).fetchone()[0]
    icon = data.get('icon') or data.get('name','??')[:2].upper()
    cur = conn.execute('INSERT INTO links (section_id,name,url,icon,position) VALUES (?,?,?,?,?)',
                       (sid, data['name'], data['url'], icon, max_pos+1))
    row = conn.execute('SELECT * FROM links WHERE id=?', (cur.lastrowid,)).fetchone()
    conn.commit()
    conn.close()
    return jsonify(dict(row)), 201

@app.route('/api/sections/<int:sid>/links/<int:lid>/move', methods=['POST'])
def move_link(sid, lid):
    direction = request.json.get('direction', 'up')
    conn = get_db()
    links = conn.execute(
        'SELECT id, position FROM links WHERE section_id=? ORDER BY position', (sid,)
    ).fetchall()
    ids = [r['id'] for r in links]
    if lid not in ids:
        conn.close()
        return jsonify({'ok': False}), 404
    idx = ids.index(lid)
    if direction == 'up' and idx > 0:
        ids[idx], ids[idx-1] = ids[idx-1], ids[idx]
    elif direction == 'down' and idx < len(ids)-1:
        ids[idx], ids[idx+1] = ids[idx+1], ids[idx]
    for pos, link_id in enumerate(ids):
        conn.execute('UPDATE links SET position=? WHERE id=?', (pos, link_id))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

@app.route('/api/sections/<int:sid>/links/reorder', methods=['POST'])
def reorder_links(sid):
    data = request.json
    drag_id = data.get('drag_id')
    target_id = data.get('target_id')
    conn = get_db()
    links = conn.execute(
        'SELECT id FROM links WHERE section_id=? ORDER BY position', (sid,)
    ).fetchall()
    ids = [r['id'] for r in links]
    if drag_id not in ids or target_id not in ids:
        conn.close()
        return jsonify({'ok': False}), 404
    ids.remove(drag_id)
    target_idx = ids.index(target_id)
    ids.insert(target_idx, drag_id)
    for pos, link_id in enumerate(ids):
        conn.execute('UPDATE links SET position=? WHERE id=?', (pos, link_id))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

@app.route('/api/links/<int:lid>', methods=['PUT'])
def update_link(lid):
    data = request.json
    conn = get_db()
    conn.execute('UPDATE links SET name=?,url=?,icon=? WHERE id=?',
                 (data['name'], data['url'], data.get('icon',''), lid))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

@app.route('/api/links/<int:lid>', methods=['DELETE'])
def delete_link(lid):
    conn = get_db()
    conn.execute('DELETE FROM links WHERE id=?', (lid,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

# ── Notes ─────────────────────────────────────────────

@app.route('/api/notes', methods=['GET'])
def get_notes():
    conn = get_db()
    row = conn.execute('SELECT content FROM notes LIMIT 1').fetchone()
    conn.close()
    return jsonify({'content': row['content'] if row else ''})

@app.route('/api/notes', methods=['PUT'])
def save_notes():
    conn = get_db()
    conn.execute('UPDATE notes SET content=?, updated_at=CURRENT_TIMESTAMP',
                 (request.json.get('content',''),))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

# ── Todos ─────────────────────────────────────────────

@app.route('/api/todos', methods=['GET'])
def get_todos():
    conn = get_db()
    rows = conn.execute('SELECT * FROM todos ORDER BY position,id').fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/todos', methods=['POST'])
def create_todo():
    conn = get_db()
    max_pos = conn.execute('SELECT COALESCE(MAX(position),0) FROM todos').fetchone()[0]
    cur = conn.execute('INSERT INTO todos (text,done,position) VALUES (?,0,?)',
                       (request.json['text'], max_pos+1))
    row = conn.execute('SELECT * FROM todos WHERE id=?', (cur.lastrowid,)).fetchone()
    conn.commit()
    conn.close()
    return jsonify(dict(row)), 201

@app.route('/api/todos/<int:tid>', methods=['PUT'])
def update_todo(tid):
    data = request.json
    conn = get_db()
    conn.execute('UPDATE todos SET text=?,done=? WHERE id=?',
                 (data['text'], int(data['done']), tid))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

@app.route('/api/todos/<int:tid>', methods=['DELETE'])
def delete_todo(tid):
    conn = get_db()
    conn.execute('DELETE FROM todos WHERE id=?', (tid,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

# ── Init — всё одним запросом ────────────────────────

@app.route('/api/init')
def init_data():
    conn = get_db()

    sections = conn.execute('SELECT * FROM sections').fetchall()
    result_sections = []
    for s in sections:
        links = conn.execute('SELECT * FROM links WHERE section_id=? ORDER BY position', (s['id'],)).fetchall()
        widget = conn.execute('SELECT * FROM widgets WHERE id=?', (f"section-{s['id']}",)).fetchone()
        result_sections.append({**dict(s), 'links': [dict(l) for l in links], 'widget': dict(widget) if widget else None})

    widgets = conn.execute('SELECT * FROM widgets').fetchall()
    notes = conn.execute('SELECT content FROM notes LIMIT 1').fetchone()
    todos = conn.execute('SELECT * FROM todos ORDER BY position,id').fetchall()

    conn.close()
    return jsonify({
        'sections': result_sections,
        'widgets': [dict(w) for w in widgets],
        'notes': notes['content'] if notes else '',
        'todos': [dict(t) for t in todos],
    })

# ── Favicons ─────────────────────────────────────────

FAVICON_DIR = os.path.join(os.path.dirname(DB_PATH), 'favicons')

def get_domain(url):
    try:
        from urllib.parse import urlparse
        return urlparse(url).netloc.replace('www.','') or url
    except:
        return url

@app.route('/api/favicon')
def get_favicon():
    domain = request.args.get('domain','')
    if not domain:
        return '', 404
    os.makedirs(FAVICON_DIR, exist_ok=True)
    safe = domain.replace(':','_').replace('/','_').replace('.','_')
    fpath = os.path.join(FAVICON_DIR, f'{safe}.ico')
    # Отдаём кэш
    if os.path.exists(fpath):
        with open(fpath, 'rb') as f:
            data = f.read()
        return data, 200, {'Content-Type':'image/x-icon','Cache-Control':'public,max-age=86400'}

    headers = {'User-Agent':'Mozilla/5.0'}
    base_url = request.args.get('url', '')  # полный URL включая порт
    is_local = any(domain.startswith(p) for p in ['192.168.','10.','172.','localhost'])
    proto = 'http' if is_local else 'https'

    def fetch_url(url, timeout=3):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read(), r.headers.get('Content-Type',''), r.url
        except:
            return None, None, None

    def fetch_url2(url, timeout=3):
        data, ct, final_url = fetch_url(url, timeout)
        return data, ct

    def save_and_return(data):
        with open(fpath, 'wb') as f:
            f.write(data)
        return data, 200, {'Content-Type':'image/x-icon','Cache-Control':'public,max-age=86400'}

    # 1. Парсим HTML страницы — ищем <link rel="icon">
    html_urls = [base_url] if base_url else []
    html_urls += [f'{proto}://{domain}', f'http://{domain}']
    import re
    for try_url in html_urls:
        html, _, final_url = fetch_url(try_url)
        if not html:
            continue
        # Используем финальный URL после редиректов как base
        base_url = final_url or try_url
        try:
            html_str = html.decode('utf-8', errors='ignore')
            # Ищем link rel icon/shortcut icon
            match = re.search(
                r'<link[^>]+rel=["\'](?:shortcut )?icon["\'][^>]+href=["\']([^"\'>]+)["\']',
                html_str, re.IGNORECASE
            )
            if not match:
                match = re.search(
                    r'<link[^>]+href=["\']([^"\'>]+)["\'][^>]+rel=["\'](?:shortcut )?icon["\']',
                    html_str, re.IGNORECASE
                )
            if match:
                icon_path = match.group(1)
                # Строим полный URL
                if icon_path.startswith('http'):
                    icon_url = icon_path
                elif icon_path.startswith('//'):
                    icon_url = proto + ':' + icon_path
                elif icon_path.startswith('/'):
                    # Используем хост из финального URL
                    from urllib.parse import urlparse
                    p = urlparse(base_url)
                    icon_url = f'{p.scheme}://{p.netloc}{icon_path}'
                else:
                    from urllib.parse import urlparse
                    p = urlparse(base_url)
                    icon_url = f'{p.scheme}://{p.netloc}/{icon_path}'
                data, _, __ = fetch_url(icon_url)
                if data and len(data) > 50:
                    return save_and_return(data)
        except:
            pass

    # 2. Стандартный /favicon.ico
    for url in [f'{proto}://{domain}/favicon.ico', f'http://{domain}/favicon.ico']:
        data, _, __ = fetch_url(url)
        if data and len(data) > 50:
            return save_and_return(data)

    # 3. Google Favicon для внешних
    if not is_local:
        data, _, __ = fetch_url(
            f'https://www.google.com/s2/favicons?domain={domain}&sz=32', timeout=4
        )
        if data:
            return save_and_return(data)

    return '', 404

# ── Icon pack (dashboard-icons) ─────────────────────

ICONS_CDN = 'https://cdn.jsdelivr.net/gh/walkxcode/dashboard-icons/png/'

# Полный список из dashboard-icons (1000 иконок)
ICONS_LIST = ["1337x", "13ft", "1panel", "1password", "1password-dark", "20i", "20i-dark", "2fauth", "2fauth-light", "3cx", "3cx-light", "4chan", "5etools", "5etools-dark", "7zip", "8311", "9anime", "a-mule", "a3", "aboard", "act", "action1", "activepieces", "actual-budget", "adblock", "adguard-home", "adguard-home-sync", "adminer", "adobe", "ads-b-exchange", "adsb", "advanzia", "adventure-log", "affine", "affine-light", "agile-freaks", "agregarr", "ai-on-the-edge-device", "air-trail", "airsonic", "airtable", "airtel", "airvpn", "akamai", "akaunting", "akkoma", "akkoma-light", "alarmpi", "albert-heijn", "alertmanager", "alertmanager-dark", "alexa", "alexandrie", "alexandrie-dark", "algo", "ali-mail", "aliasvault", "aliexpress", "alist", "aliyun", "alloy", "alltube", "alltube-light", "alma-linux", "alpine-linux", "amazon", "amazon-light", "amazon-prime", "amazon-web-services", "amazon-web-services-light", "amcrest", "amcrest-cloud", "amd", "amd-light", "ami", "ami-alt", "ami-alt-light", "amp", "ampache", "anchor", "android", "android-auto", "android-auto-dark", "android-robot", "anghami", "angular", "anime-kai", "anki", "anonaddy", "ansible", "ansible-light", "anubis", "any-listen", "anything-llm", "anything-llm-light", "anytype", "apache", "apache-airflow", "apache-answer", "apache-cassandra", "apache-cloudstack", "apache-druid", "apache-iceberg", "apache-openoffice", "apache-solr", "apache-subversion", "apache-tomcat", "apache-tomcat-light", "apc", "apiscp", "app-service", "app-store", "appdaemon", "appflowy", "apple", "apple-alt", "apple-light", "apple-maps", "apple-music", "apple-podcasts", "apple-tv-plus", "apple-tv-plus-light", "application-gateway-container", "application-gateways", "apprise", "appwrite", "ara-records-ansible", "arcane", "arch-linux", "archidekt", "archisteamfarm", "archivebox", "archivedotorg", "archiveteam-warrior", "archiveteam-warrior-light", "arduino", "arenalmsys", "argo-cd", "ariang", "arm", "arris", "arris-light", "artifacthub", "artifactory", "artix", "aruba", "asana", "asciinema", "asrock-rack", "asrock-rack-ipmi", "assetgrid", "asterisk", "astral", "astrbot", "astuto", "astuto-light", "asus", "asus-full", "asus-rog", "asus-router", "asustor", "at-t", "atlassian", "atlassian-bamboo", "atlassian-bitbucket", "atlassian-confluence", "atlassian-jira", "atlassian-opsgenie", "atlassian-trello", "atuin", "atuin-light", "audacity", "audiobookshelf", "audiomuse-ai", "audora", "aura", "auracast", "aurral", "authelia", "authentik", "authman", "auto-cad", "auto-mcs", "autobangumi", "autobangumi-dark", "autobrr", "automad", "automad-light", "av1", "av1-dark", "av1-light", "avg", "avigilon", "avm-fritzbox", "avm-fritzbox-light", "aws", "aws-ecs", "aws-light", "awtrix", "awwesome", "awx", "axis", "aya", "azuracast", "azure", "azure-application-insights", "azure-bicep", "azure-container-apps", "azure-container-instances", "azure-container-registry", "azure-container-service", "azure-cosmos-db", "azure-data-factory", "azure-devops", "azure-dns", "azure-expressroute-cirtcuits", "azure-firewall", "azure-front-door", "azure-keyvault", "azure-kubernetes-services", "azure-log-analytics-workspaces", "azure-monitor", "azure-postgres-server", "azure-sql-db", "azure-sql-server", "azure-storage-accounts", "azure-virtual-desktop", "azure-virtual-network-gateways", "azure-vm", "azure-vnet", "bab-technologie", "bab-technologie-dark", "babybuddy", "backblaze", "backrest", "backrest-light", "bacula", "badge", "baikal", "bale", "balena-cloud", "balena-etcher", "ballerina", "bandcamp", "bar-assistant", "barcodebuddy", "barrage", "baserow", "basilisk", "bastillion", "batocera-linux", "bazarr", "bazarr-dark", "bazecor", "be-quiet", "beaver-habit-tracker", "beaver-habit-tracker-light", "bechtle", "beef", "beef-light", "beets", "behance", "benotes", "bentopdf", "beszel", "beszel-light", "betanin", "bewcloud", "bible-gateway", "bibliogram", "biblioreads", "biblioreads-light", "biedronka", "bigcapital", "bilibili", "bing", "binner", "binner-dark", "birdnet", "bitbucket", "bitcoin", "bithumen", "bitly", "bitly-dark", "bitly-light", "bitly-wordmark-light", "bitmagnet", "bitwarden", "bitwig-studio", "bitwig-studio-dark", "black-forest-labs", "black-forest-labs-dark", "black-forest-labs-light", "black-forest-labs-wordmark-dark", "black-forest-labs-wordmark-light", "blender", "blocky", "blogger", "blu-ray", "blu-ray-3d", "blue-iris", "blue-letter-bible", "bluemap", "bluesky", "bluetooth", "bluewallet", "bobcat-miner", "boeing", "boinc", "boltnew", "book-lore", "booklogr", "booklogr-light", "booklore", "booklore-wordmark-light", "booksonic", "bookstack", "bootstrap", "borg", "borgmatic", "borgmatic-light", "bottom", "bottom-dark", "boundary", "box", "boxarr", "brave", "brave-dev", "brewpi", "brick-tracker", "bright-move", "brillcam", "broad-link", "broadcastchannel", "broadcastchannel-light", "broadcom", "broadcom-dark", "broadcom-wordmark-light", "brocade", "brother", "browserless", "browserless-light", "browsh", "btcpay-server", "buddy", "budget-board", "budget-zero", "budgetbee", "budgetbee-light", "budibase", "buffalo", "build-better", "build-better-dark", "buildium", "bunkerweb", "bunny", "burpsuite", "buxfer", "byparr", "bytestash", "c", "cabernet", "cabot", "cachyos-linux", "cacti", "caddy", "cadvisor", "cal-com", "cal-com-light", "calckey", "caldera", "calibre", "calibre-web", "calibre-web-automated-book-downloader", "camera-ui", "canonical", "canvas-lms", "cap-cut", "cap-cut-dark", "capacities", "capacities-dark", "capjs", "caprover", "cardigann", "cardigann-light", "carousell", "carrefour", "casaos", "castopod", "catppuccin", "cc", "cc-light", "cd", "cd-dark", "cd-light", "centos", "centreon", "ceph", "cert-manager", "cert-warden", "cert-warden-light", "cessna", "chainguard", "changedetection", "channels-dvr", "chaptarr", "chart-db", "chatbetter", "chatgpt", "chatpad-ai", "chatwoot", "check-cle", "check-point", "check-point-wordmark-light", "checkbits", "checkmate", "checkmk", "cherry", "chess", "chevereto", "chhoto-url", "chibisafe", "chiefonboarding", "chirpy", "chowdown", "chroma", "chrome", "chrome-beta", "chrome-canary", "chrome-dev", "chrome-devtools", "chrome-remote-desktop", "chromecast", "chromecast-light", "chromium", "chronograf", "chzzk", "cilium", "cilium-light", "cinny", "cinny-light", "ciphermail", "cisco", "citrix", "clam-av", "clash", "claude-ai", "claude-ai-light", "clawd", "cleanuparr", "cleanuperr", "clickhouse", "clickup", "cloud66", "cloud9", "cloud9-light", "cloudbeaver", "cloudcmd", "cloudflare", "cloudflare-pages", "cloudflare-zero-trust", "cloudpanel", "cloudreve", "cloudstream", "cobalt", "cobalt-dark", "cocalc", "cockpit", "cockpit-cms", "cockpit-cms-light", "cockpit-light", "code", "code-cademy", "code-cademy-dark", "code-server", "codeberg", "codellm", "coder", "coder-light", "codestats", "codestats-light", "codex", "codex-light", "codimd", "codimd-light", "collabora-online", "comfy-ui", "comfyui", "comfyui-dark", "comfyui-light", "comfyui-wordmark-dark", "comfyui-wordmark-light", "commafeed", "commafeed-light", "commento", "commento-light", "compreface", "concourse", "configarr", "confix", "confluence", "confluent", "confluent-dark", "confluent-light", "consul", "contabo", "control-d", "control-d-dark", "converse", "converse-light", "convertx", "convex", "cooler-control", "coolify", "copyparty", "copyq", "core-control", "coredns", "coreos", "cosign", "cosmic", "cosmos-cloud", "costco", "couchdb", "couchpotato", "counter-analytics", "counter-strike-2", "counter-strike-global-offensive", "coursera", "cozy", "cpanel", "cpp", "crafty-controller", "crater-invoice", "crazydomains", "cribl", "cribl-light", "cron-master", "cronicle", "cronmaster", "cronmaster-dark", "cronmaster-light", "cross-seed", "cross-seed-square", "crosswatch", "crowdin", "crowdin-dark", "crowdsec", "crowdsec-web-ui", "crowdstrike", "crowdstrike-dark", "crowdstrike-light", "crowdstrike-wordmark-dark", "crowdstrike-wordmark-light", "crunchyroll", "cryptomator", "cryptpad", "csharp", "css", "css-light", "ctfreak", "cup", "cups", "cups-light", "cura", "cyber-power-full", "cyberchef", "cypress", "czkawka", "d-link", "dagster-dark", "dagster-light", "dahua", "dalibo", "danmaku", "daps", "dart", "dashboard-icons", "dashboard-icons-dark", "dashdot", "dashlane", "dashwise", "dashy", "databasus", "databricks", "datadog", "davical", "davis", "dawarich", "dc-os", "dd-wrt", "dd-wrt-light", "ddclient", "ddev", "ddev-dark", "ddns-updater", "debian-linux", "deemix", "deepl", "deepl-dark", "deepseek", "deezer", "defguard", "dell", "dell-light", "deluge", "deno", "deno-light", "denodo", "denon", "denon-light", "dependency-track", "dependency-track-wordmark-dark", "dependency-track-wordmark-light", "deployarr", "deq", "develancacheui", "devtooly", "devtooly-light", "dia", "diagrams-net", "diamond-aircraft", "dietpi", "digi-kam", "digikey", "digital-ocean", "dilg", "dillinger", "dillinger-light", "dim", "dim-light", "diners-club", "directadmin", "directus", "discord", "discourse", "discourse-light", "diskover", "disney-plus", "dispatcharr", "distribution", "diun", "dixa", "diyhue", "dlna", "dns-private-resolver", "dns-zone", "dnsimple", "docassemble", "docassemble-light", "docker", "docker-amd", "docker-amvd", "docker-compose", "docker-engine", "docker-gc", "docker-mailserver", "docker-mailserver-light", "docker-moby", "docker-volume-backup", "dockge", "dockhand", "docking-station", "dockmon", "dockpeek", "dockpeek-dark", "dockstarter", "dockwatch", "docling", "docmost", "docsify", "docspell", "documenso", "docusaurus", "docuseal", "dogpile", "dokemon", "dokploy", "dokploy-dark", "dokuwiki", "dolibarr", "dolphin", "domainmod", "domoticz", "donetick", "doplarr", "doppler", "dopplertask", "double-commander", "double-take", "double-take-dark", "dovecot", "dozzle", "dragon-ruby", "draw-io", "draytek", "dream-host", "dream-host-dark", "drone", "drop", "dropbox", "dropout", "dropout-light", "droppy", "droppy-dark", "dub", "dub-light", "duckdns", "duckdns-light", "duckduckgo", "dumbassets", "dumbpad", "duo", "duolingo", "duplicacy", "duplicati", "dvd", "dvd-dark", "dvd-light", "dynmap", "easy-gate", "easy-gate-light", "ebay", "eblocker", "edge", "edge-dev", "edgeos", "edgeos-light", "eficify", "eitaa", "elabftw", "elastic", "elastic-beats", "elastic-kibana", "elastic-logstash", "elasticsearch", "electron", "electronic-arts", "electrum", "element", "eleven-labs", "eleven-labs-dark", "eleventy", "eleventy-light", "elgato-wave-link", "eliza-os", "elysian", "emacs", "embraer", "emby", "embystat", "emq", "emq-light", "emqx", "emsesp", "emulatorjs", "enbizcard", "enclosed", "enclosed-light", "endeavouros-linux", "endel", "endel-dark", "endless", "endless-light", "endurain", "enhance", "enshrouded", "ente-auth", "ente-photos", "entergy", "epic-games", "epic-games-light", "epson-iprint", "epson-scan", "ersatztv", "erste", "erste-george", "erugo", "esphome", "esphome-alt", "esphome-alt-light", "esphome-light", "espocrm", "espressif", "etcd", "etesync", "ethereum", "etherpad", "evcc", "evebox", "everhour", "evernote", "eweka", "excalidraw", "exercism", "exercism-dark", "expense-owl", "ezbookkeeping", "f-droid", "f1-dash", "f5-networks", "facebook", "facebook-messenger", "fail2ban", "falcon-christmas", "falcon-player", "falcon-player-dark", "fast-com", "fast-com-light", "fastapi", "fastapi-wordmark-light", "fasten-health", "fastmail", "fedora", "fedora-alt", "feedbase", "feedbase-light", "feedbin", "feedbin-light", "feedly", "feedlynx", "feedlynx-light", "feishin", "fenrus", "fenrus-light", "ferdi", "ferdium", "fermentrack", "ferretdb", "fibaro", "fidelity", "fider", "figma", "filaman", "filebot", "filebrowser", "filebrowser-quantum", "filecloud", "fileflows", "filegator", "filepizza", "filerise", "filerun", "files", "files-community", "filestash", "filezilla", "finamp", "findroid", "fios", "fios-light", "firebase", "firefly", "firefly-iii", "firefox", "firefox-beta", "firefox-developer-edition", "firefox-lite", "firefox-nightly", "firefox-reality", "firefox-send", "fireshare", "firewalla", "fittrackee", "fl-studio", "fladder", "flame", "flaresolverr", "flarum", "flat-notes", "flathub", "flathub-dark", "flatnotes", "flatpak", "fleetdm", "flexget", "flightaware", "flightradar24", "flightradar24-light", "floatplane", "flogo", "flood", "floorp", "floorplanner", "flowise", "flowtunes", "fluent-reader", "fluffychat", "fluffychat-dark", "fluidd", "flutter", "flutter-wordmark-dark", "flutter-wordmark-light", "flux-cd", "flux-operator", "flux-operator-light", "fly-io", "fmd", "fnos", "focalboard", "foldingathome", "fontawesome", "foreflight", "foreflight-dark", "forgejo", "formbricks", "forte", "forte-light", "fortinet", "fortran", "foscam", "fossil", "foundry-vtt", "framer", "franz", "free-dns", "free-sas", "freebox-delta", "freebox-pop", "freebox-revolution", "freedombox", "freeipa", "freenas", "freenom", "freepbx", "freescout", "freesound", "freshbooks", "freshping", "freshping-dark", "freshrss", "friendica", "frigate", "frigate-light", "fritzbox", "fritzbox-light", "fronius", "frp", "fulcio", "funkwhale", "funkwhale-light", "fusionauth", "fusionauth-light", "fusionpbx", "gamevault", "gameyfin", "gameyfin-light", "gaps", "garage", "garmin-connect", "garuda-linux", "gaseous", "gatsby", "gatus", "gboard", "geckoview", "genius", "gentoo-linux", "genua", "geo-guessr", "gerbera", "gerrit", "get-iplayer", "ghost", "ghost-light", "ghostfolio", "ghostty", "gigaset", "gimp", "git", "gitam-university", "gitbook", "gitea", "gitea-mirror", "gitee", "github", "github-copilot", "github-copilot-dark", "github-light", "gitlab", "gitsign", "gladys-assistant", "glance", "glances", "glances-light", "glinet", "glinet-dark", "glitchtip", "glpi", "gluetun", "gmail", "gnu-guix", "go", "go2rtc", "goaccess", "goaccess-light", "gocd", "gocoax", "godaddy", "godaddy-alt"]

@app.route('/api/icons/search')
def search_icons():
    q = request.args.get('q', '').lower().strip()
    if not q:
        # Без запроса — возвращаем первые 40 популярных
        popular = ['adguard-home','authentik','bitwarden','calibre-web',
            'cloudflare','dashy','docker','dozzle','emby','filebrowser',
            'freshrss','gitea','glances','grafana','homeassistant',
            'homarr','immich','jellyfin','keenetic','komga','mikrotik',
            'mosquitto','navidrome','nextcloud','nginx','nginx-proxy-manager',
            'node-red','ntfy','ollama','open-webui','overseerr',
            'paperless-ngx','photoprism','pihole','plex','portainer',
            'proxmox','qbittorrent','radarr','redis','sonarr',
            'syncthing','synology','tailscale','traefik','transmission',
            'unifi','uptime-kuma','vaultwarden','wireguard']
        return jsonify([p for p in popular if p in ICONS_LIST][:40])
    results = [n for n in ICONS_LIST if q in n]
    return jsonify(results[:40])

@app.route('/api/icons/debug')
def debug_icons():
    try:
        req = urllib.request.Request(
            'https://cdn.jsdelivr.net/gh/walkxcode/dashboard-icons/metadata/icon-metadata.json',
            headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as r:
            raw = r.read()
            data = json.loads(raw)
            return jsonify({
                'status': 'ok',
                'type': str(type(data)),
                'len': len(data),
                'keys': list(data.keys())[:10] if isinstance(data, dict) else 'list',
                'sample': str(raw[:300])
            })
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/icons/<path:name>')
def get_icon(name):
    # Sanitize
    name = name.replace('/', '').replace('..', '').replace(' ', '-').lower()
    if not name.endswith('.png'):
        name = name + '.png'
    os.makedirs(FAVICON_DIR, exist_ok=True)
    fpath = os.path.join(FAVICON_DIR, 'icon_' + name)
    if os.path.exists(fpath):
        with open(fpath, 'rb') as f:
            return f.read(), 200, {'Content-Type': 'image/png',
                                   'Cache-Control': 'public,max-age=604800'}
    try:
        url = ICONS_CDN + name
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as r:
            data = r.read()
        with open(fpath, 'wb') as f:
            f.write(data)
        return data, 200, {'Content-Type': 'image/png',
                           'Cache-Control': 'public,max-age=604800'}
    except:
        return '', 404

# ── Widget plugins ───────────────────────────────────

@app.route('/api/widget-plugins')
def list_widget_plugins():
    widgets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'widgets')
    if not os.path.exists(widgets_dir):
        return jsonify([])
    files = [f for f in os.listdir(widgets_dir)
             if f.endswith('.js') and not f.startswith('WIDGET_')]
    return jsonify(files)

# ── Health ────────────────────────────────────────────

@app.route('/api/health')
def health():
    return jsonify({'status': 'ok'})

# Вызываем при импорте модуля — gunicorn не заходит в __main__
init_db()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
