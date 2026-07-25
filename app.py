#!/usr/bin/env python3
"""بستان العجوة — Flask + Apps Script + Google Sheets"""
import os, json, base64, sqlite3, urllib.request, urllib.parse, secrets, logging
from functools import wraps
from datetime import datetime
from flask import Flask, request, jsonify, render_template, g, session

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("bustan")

from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# --- الأمان: SECRET_KEY من متغير بيئة، مع مفتاح عشوائي كحل احتياطي ---
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))

APPS_SCRIPT_URL = os.environ.get('APPS_SCRIPT_URL', '')
USE_SHEETS = bool(APPS_SCRIPT_URL)
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'bustan.db')

# --- الأمان: وضع التصحيح (debug) يُفعّل فقط عبر متغير بيئة صريح ---
DEBUG_MODE = os.environ.get('FLASK_DEBUG', '0') == '1'

log.info("=" * 50)
if USE_SHEETS:
    log.info(" mode: Google Sheets (Apps Script)")
else:
    log.info(" mode: SQLite (local)")
    log.info(" db: " + DB_PATH)
log.info("=" * 50)

TABLES = {
    'users': ['id','username','password','role','name','active'],
    'reps': ['id','name','phone','dept','notes','active','pin'],
    'advances': ['id','repId','amount','date','purpose','notes','status','settleDate'],
    'purchases': ['id','advId','amount','taxableAmount','taxAmount','invoiceType','invoiceNo','costCenter','desc','date','notes','supplierName','supplierTaxNo','companyId'],
    'expenses': ['id','repId','advId','amount','desc','date','costCenter','accountantNotes','managerNotes','status','actionDate'],
    'adv_requests': ['id','repId','amount','purpose','notes','status','requestDate','actionDate'],
    'suppliers': ['id','name','taxNo','phone','email','active'],
    'companies': ['id','name','taxNo','crNo','address','active']
}

def num(v):
    try:
        return float(v) if v not in (None, '', 'None') else 0
    except:
        return 0

# ================================================================
# جودة الكود: مواصفات كل جدول قابل للإدخال عبر API — تُستخدم لبناء
# عنصر الإدخال بدل تكرار نفس القائمة يدوياً في كل مسار على حدة.
# 'numeric' تحدد أي الحقول تُمرَّر عبر num() قبل الحفظ.
# 'defaults' تحدد القيم الافتراضية للحقول غير الرقمية (مثل status).
# ================================================================
FIELD_SPECS = {
    'purchases': {
        'fields': ['advId','amount','taxableAmount','taxAmount','invoiceType','invoiceNo',
                   'costCenter','desc','date','notes','supplierName','supplierTaxNo','companyId'],
        'numeric': {'amount','taxableAmount','taxAmount'},
        'defaults': {},
    },
    'advances': {
        'fields': ['repId','amount','date','purpose','notes','status','settleDate'],
        'numeric': {'amount'},
        'defaults': {'status': 'open'},
    },
    'adv_requests': {
        'fields': ['repId','amount','purpose','notes','status','requestDate','actionDate'],
        'numeric': {'amount'},
        'defaults': {'status': 'pending'},
    },
    'expenses': {
        'fields': ['repId','advId','amount','desc','date','costCenter','accountantNotes',
                   'managerNotes','status','actionDate'],
        'numeric': {'amount'},
        'defaults': {'status': 'pending'},
    },
}

def build_item(tab, d):
    """يبني عنصر جاهز للحفظ حسب مواصفة الجدول — بدل تكرار قائمة الحقول يدوياً في كل مسار."""
    spec = FIELD_SPECS[tab]
    item = {}
    for field in spec['fields']:
        default = spec['defaults'].get(field, 0 if field in spec['numeric'] else '')
        value = d.get(field, default)
        item[field] = num(value) if field in spec['numeric'] else value
    return item

def parse_body(as_list_default=None):
    """يوحّد استخراج جسم الطلب: يدعم قائمة (تُختصر لأول عنصر) أو كائن، مع قيمة افتراضية آمنة."""
    d = request.json
    if d is None:
        d = as_list_default if as_list_default is not None else {}
    if isinstance(d, list):
        d = d[0] if d else {}
    return d

def api_route(f):
    """يزيل تكرار try/except عبر كل مسارات الـ API، ويسجّل الأخطاء الحقيقية بدل ابتلاعها بصمت."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            log.exception(f.__name__ + " failed")
            return jsonify({'ok': False, 'success': False, 'err': str(e)})
    return wrapper

# ================================================================
# الأمان: حراسة الجلسة لمسارات الكتابة والقراءة الحساسة
# ================================================================
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('user_id'):
            return jsonify({'ok': False, 'success': False, 'err': 'يجب تسجيل الدخول'}), 401
        return f(*args, **kwargs)
    return wrapper

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not session.get('user_id'):
                return jsonify({'ok': False, 'success': False, 'err': 'يجب تسجيل الدخول'}), 401
            if session.get('role') not in roles:
                return jsonify({'ok': False, 'success': False, 'err': 'صلاحيات غير كافية'}), 403
            return f(*args, **kwargs)
        return wrapper
    return decorator

# ================================================================
# Apps Script Proxy
# ================================================================
def sheets_api_get(params):
    url = APPS_SCRIPT_URL + '?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, method='GET')
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode('utf-8'))

def sheets_api_post(body):
    data = json.dumps(body).encode('utf-8')
    req = urllib.request.Request(APPS_SCRIPT_URL, data=data, method='POST')
    req.add_header('Content-Type', 'application/json')
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode('utf-8'))

def sheets_read(tab):
    result = sheets_api_get({'action': 'read', 'table': tab})
    if result.get('ok'):
        return result.get('data', [])
    return []

def sheets_write(tab, data):
    return sheets_api_post({'action': 'write', 'table': tab, 'data': data})

def sheets_insert(tab, item):
    result = sheets_api_post({'action': 'insert', 'table': tab, 'item': item})
    return result.get('id', 0) if result.get('ok') else 0

def sheets_update(tab, id_val, updates):
    return sheets_api_post({'action': 'update', 'table': tab, 'id': id_val, 'item': updates})

def sheets_delete(tab, id_val):
    return sheets_api_post({'action': 'delete', 'table': tab, 'id': id_val})

def sheets_filtered(tab, col, val):
    result = sheets_api_get({'action': 'readFiltered', 'table': tab, 'col': col, 'val': val})
    if result.get('ok'):
        return result.get('data', [])
    return []

# ================================================================
# SQLite
# ================================================================
def get_db():
    if 'db' not in g:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
    return g.db

@app.teardown_appcontext
def close_db(exc):
    db = g.pop('db', None)
    if db:
        db.close()

def dict_all(rows):
    return [dict(r) for r in rows]

def sqlite_init():
    db = get_db()
    db.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT, password TEXT, role TEXT DEFAULT 'add', name TEXT, active TEXT DEFAULT 'true')")
    db.execute("CREATE TABLE IF NOT EXISTS reps (id INTEGER PRIMARY KEY, name TEXT, phone TEXT, dept TEXT, notes TEXT, active TEXT DEFAULT 'true', pin TEXT)")
    db.execute("CREATE TABLE IF NOT EXISTS advances (id INTEGER PRIMARY KEY, repId INTEGER, amount REAL DEFAULT 0, date TEXT, purpose TEXT, notes TEXT, status TEXT DEFAULT 'open', settleDate TEXT)")
    db.execute('CREATE TABLE IF NOT EXISTS purchases (id INTEGER PRIMARY KEY, advId INTEGER, amount REAL DEFAULT 0, taxableAmount REAL DEFAULT 0, taxAmount REAL DEFAULT 0, invoiceType TEXT, invoiceNo TEXT, costCenter TEXT, "desc" TEXT, date TEXT, notes TEXT, supplierName TEXT, supplierTaxNo TEXT, companyId TEXT)')
    db.execute('CREATE TABLE IF NOT EXISTS expenses (id INTEGER PRIMARY KEY, repId INTEGER, advId INTEGER, amount REAL DEFAULT 0, "desc" TEXT, date TEXT, costCenter TEXT, accountantNotes TEXT, managerNotes TEXT, status TEXT DEFAULT "pending", actionDate TEXT)')
    db.execute("CREATE TABLE IF NOT EXISTS adv_requests (id INTEGER PRIMARY KEY, repId INTEGER, amount REAL DEFAULT 0, purpose TEXT, notes TEXT, status TEXT DEFAULT 'pending', requestDate TEXT, actionDate TEXT)")
    db.execute("CREATE TABLE IF NOT EXISTS suppliers (id INTEGER PRIMARY KEY, name TEXT, taxNo TEXT, phone TEXT, email TEXT, active TEXT DEFAULT 'true')")
    db.execute("CREATE TABLE IF NOT EXISTS companies (id INTEGER PRIMARY KEY, name TEXT, taxNo TEXT, crNo TEXT, address TEXT, active TEXT DEFAULT 'true')")
    if db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        db.execute(
            "INSERT INTO users (id, username, password, role, name, active) VALUES (1,?,?,?,?,?)",
            ('admin', generate_password_hash('admin123'), 'admin', 'مدير النظام', 'true')
        )
    db.commit()

def sqlite_read(tab):
    return dict_all(get_db().execute("SELECT * FROM " + tab).fetchall())

def sqlite_write(tab, data, headers):
    db = get_db()
    db.execute("DELETE FROM " + tab)
    for item in data:
        vals = [item.get(h, '') if item.get(h) is not None else '' for h in headers]
        ph = ','.join(['?'] * len(headers))
        cols = ','.join(['"' + c + '"' if c == 'desc' else c for c in headers])
        db.execute("INSERT INTO " + tab + " (" + cols + ") VALUES (" + ph + ")", vals)
    db.commit()

def sqlite_next_id(tab):
    row = get_db().execute("SELECT MAX(id) FROM " + tab).fetchone()
    return (row[0] or 0) + 1

def sqlite_insert(tab, item):
    db = get_db()
    nid = sqlite_next_id(tab)
    item['id'] = nid
    headers = TABLES[tab]
    vals = [item.get(h, '') if item.get(h) is not None else '' for h in headers]
    ph = ','.join(['?'] * len(headers))
    cols = ','.join(['"' + c + '"' if c == 'desc' else c for c in headers])
    db.execute("INSERT INTO " + tab + " (" + cols + ") VALUES (" + ph + ")", vals)
    db.commit()
    return nid

def sqlite_update(tab, id_val, updates):
    db = get_db()
    sets = []
    vals = []
    for k, v in updates.items():
        col = '"' + k + '"' if k == 'desc' else k
        sets.append(col + "=?")
        vals.append(v)
    vals.append(id_val)
    db.execute("UPDATE " + tab + " SET " + ','.join(sets) + " WHERE id=?", vals)
    db.commit()

def sqlite_delete(tab, id_val):
    db = get_db()
    db.execute("DELETE FROM " + tab + " WHERE id=?", [id_val])
    db.commit()

def sqlite_filtered(tab, col, val):
    return dict_all(get_db().execute("SELECT * FROM " + tab + " WHERE " + col + "=?", [val]).fetchall())

# ================================================================
# واجهة موحدة
# ================================================================
def db_read(tab):
    return sheets_read(tab) if USE_SHEETS else sqlite_read(tab)

def db_write(tab, data):
    if USE_SHEETS:
        sheets_write(tab, data)
    else:
        sqlite_write(tab, data, TABLES[tab])

def db_insert(tab, item):
    return sheets_insert(tab, item) if USE_SHEETS else sqlite_insert(tab, item)

def db_update(tab, id_val, updates):
    if USE_SHEETS:
        sheets_update(tab, id_val, updates)
    else:
        sqlite_update(tab, id_val, updates)

def db_delete(tab, id_val):
    if USE_SHEETS:
        sheets_delete(tab, id_val)
    else:
        sqlite_delete(tab, id_val)

def db_filtered(tab, col, val):
    return sheets_filtered(tab, col, val) if USE_SHEETS else sqlite_filtered(tab, col, val)

# ================================================================
# صفحات HTML
# ================================================================
@app.route('/')
def page_router():
    page = request.args.get('page', '')
    pages = {
        'admin': 'app.html',
        'rep': 'rep.html',
        'report': 'report.html',
        'report2': 'report2.html'
    }
    return render_template(pages.get(page, 'index.html'))

# ================================================================
# API: البيانات
# ================================================================
@app.route('/api/data')
@login_required
@api_route
def api_data():
    return jsonify({'ok': True, 'd': {
        'r': db_read('reps'),
        'a': db_read('advances'),
        'p': db_read('purchases'),
        'x': db_read('expenses'),
        'u': db_read('users'),
        'q': db_read('adv_requests'),
        'sup': db_read('suppliers'),
        'comp': db_read('companies')
    }})

@app.route('/api/report-data')
@login_required
@api_route
def api_report():
    return jsonify({'ok': True, 'd': {
        'r': db_read('reps'),
        'a': db_read('advances'),
        'p': db_read('purchases'),
        'x': db_read('expenses'),
        'sup': db_read('suppliers'),
        'comp': db_read('companies')
    }})

@app.route('/api/rep-data/<int:rid>')
@login_required
@api_route
def api_rep(rid):
    advs = db_filtered('advances', 'repId', rid)
    ids = [int(a['id']) for a in advs]
    purs = [p for p in db_read('purchases') if int(p.get('advId', 0)) in ids]
    return jsonify({'ok': True, 'd': {'a': advs, 'p': purs}})

# ================================================================
# API: المصادقة
# ================================================================
@app.route('/api/auth', methods=['POST'])
@api_route
def api_auth():
    d = request.json
    if d is None:
        return jsonify({'ok': False, 'err': 'لا توجد بيانات'})
    if isinstance(d, list):
        username = str(d[0]).strip().strip("'").strip('"')
        password = str(d[1]).strip().strip("'").strip('"')
    else:
        username = str(d.get('username', '')).strip().strip("'").strip('"')
        password = str(d.get('password', '')).strip().strip("'").strip('"')

    users = db_read('users')
    for u in users:
        u_user = str(u.get('username', '')).strip().strip("'").strip('"')
        u_pass = str(u.get('password', '')).strip().strip("'").strip('"')
        u_active = str(u.get('active', 'true')).strip().lower()

        if u_user != username:
            continue

        password_ok = False
        if u_pass.startswith('pbkdf2:') or u_pass.startswith('scrypt:'):
            password_ok = check_password_hash(u_pass, password)
        else:
            password_ok = (u_pass == password)
            if password_ok:
                try:
                    db_update('users', u.get('id'), {'password': generate_password_hash(password)})
                except Exception:
                    log.exception("password auto-upgrade failed")

        if password_ok:
            if u_active in ('true', '1', 'yes'):
                session['user_id'] = int(u.get('id', 0))
                session['role'] = u.get('role', 'add')
                session.permanent = True
                return jsonify({'ok': True, 'user': {
                    'id': int(u.get('id', 0)),
                    'username': u.get('username', ''),
                    'role': u.get('role', 'add'),
                    'name': u.get('name', username)
                }})
            return jsonify({'ok': False, 'err': 'الحساب غير مفعّل'})

    return jsonify({'ok': False, 'err': 'بيانات الدخول غير صحيحة'})

@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({'ok': True})

# ================================================================
# API: حفظ الكل
# ================================================================
@app.route('/api/save-all', methods=['POST'])
@login_required
@api_route
def api_save_all():
    d = request.json or {}
    if isinstance(d, list):
        return jsonify({'success': False, 'err': 'صيغة غير صحيحة'})
    for key, tab in [('reps', 'reps'), ('advances', 'advances'),
                      ('purchases', 'purchases'), ('expenses', 'expenses'),
                      ('suppliers', 'suppliers'), ('companies', 'companies')]:
        if key in d:
            db_write(tab, d[key])
    return jsonify({'success': True})

# ================================================================
# جودة الكود: مسارات إدخال/تعديل/حذف عامة تبني الجدول من FIELD_SPECS
# بدل تكرار نفس بنية الكود ثلاث مرات لكل جدول (فواتير، عهد، طلبات عهد)
# ================================================================
def register_crud(tab, url_prefix):
    @app.route(url_prefix, methods=['POST'], endpoint='add_' + tab)
    @login_required
    @api_route
    def _add():
        d = parse_body()
        nid = db_insert(tab, build_item(tab, d))
        return jsonify({'success': True, 'id': nid})

    @app.route(url_prefix + '/<int:item_id>', methods=['PUT'], endpoint='upd_' + tab)
    @login_required
    @api_route
    def _upd(item_id):
        d = parse_body()
        db_update(tab, item_id, d)
        return jsonify({'success': True})

    @app.route(url_prefix + '/<int:item_id>', methods=['DELETE'], endpoint='del_' + tab)
    @login_required
    @api_route
    def _del(item_id):
        db_delete(tab, item_id)
        return jsonify({'success': True})

register_crud('purchases', '/api/purchases')
register_crud('advances', '/api/advances')

# adv_requests له نمط مختلف قليلاً (بدون DELETE في الأصل) فبقي مسار منفصل صغير
@app.route('/api/adv-requests', methods=['POST'])
@login_required
@api_route
def api_add_request():
    d = parse_body()
    nid = db_insert('adv_requests', build_item('adv_requests', d))
    return jsonify({'success': True, 'id': nid})

@app.route('/api/adv-requests/<int:rid>', methods=['PUT'])
@login_required
@api_route
def api_upd_request(rid):
    d = parse_body()
    db_update('adv_requests', rid, d)
    return jsonify({'success': True})

# ================================================================
# API: المصروفات (تُضاف كدفعة/قائمة، لذلك بقيت بمسار مخصص)
# ================================================================
@app.route('/api/expenses', methods=['POST'])
@login_required
@api_route
def api_add_expenses():
    items = request.json or []
    if isinstance(items, dict):
        items = [items]
    for item in items:
        if isinstance(item, list):
            continue
        db_insert('expenses', build_item('expenses', item))
    return jsonify({'success': True})

@app.route('/api/expenses/<int:eid>', methods=['PUT'])
@login_required
@api_route
def api_upd_expense(eid):
    d = parse_body()
    db_update('expenses', eid, d)
    return jsonify({'success': True})

# ================================================================
# API: المستخدمين والموردين والشركات
# ================================================================
@app.route('/api/users', methods=['POST'])
@role_required('admin')
@api_route
def api_users():
    data = request.json or []
    if isinstance(data, dict):
        data = [data]
    for u in data:
        pw = str(u.get('password', ''))
        if pw and not (pw.startswith('pbkdf2:') or pw.startswith('scrypt:')):
            u['password'] = generate_password_hash(pw)
    db_write('users', data)
    return jsonify({'success': True})

@app.route('/api/suppliers', methods=['POST'])
@login_required
@api_route
def api_suppliers():
    data = request.json or []
    if isinstance(data, dict):
        data = [data]
    db_write('suppliers', data)
    return jsonify({'success': True})

@app.route('/api/companies', methods=['POST'])
@login_required
@api_route
def api_companies():
    data = request.json or []
    if isinstance(data, dict):
        data = [data]
    db_write('companies', data)
    return jsonify({'success': True})

# ================================================================
# API: الاستيراد والتصدير
# ================================================================
KEY_MAP = {
    'reps': 'reps', 'advances': 'advances', 'purchases': 'purchases',
    'expenses': 'expenses', 'users': 'users', 'advRequests': 'adv_requests',
    'suppliers': 'suppliers', 'companies': 'companies',
    'المناديب': 'reps', 'العهد': 'advances', 'المشتريات': 'purchases',
    'مصروفات_بدون_فواتير': 'expenses', 'المستخدمين': 'users',
    'طلبات_العهد': 'adv_requests', 'الموردين': 'suppliers', 'الشركات': 'companies'
}

@app.route('/api/import/upload', methods=['POST'])
@role_required('admin')
@api_route
def api_import():
    d = request.json or {}
    if isinstance(d, list):
        return jsonify({'ok': False, 'err': 'صيغة غير صحيحة'})
    file_data = d.get('data', '')
    if isinstance(file_data, str):
        try:
            decoded = base64.b64decode(file_data).decode('utf-8')
        except:
            decoded = file_data
    else:
        decoded = json.dumps(file_data)
    data = json.loads(decoded)
    imported = 0
    skipped = []
    for fk, items in data.items():
        table = KEY_MAP.get(fk)
        if not table:
            skipped.append(fk)
            continue
        if not isinstance(items, list) or not items:
            skipped.append(fk)
            continue
        db_write(table, items)
        imported += 1
    msg = "تم استيراد " + str(imported) + " جداول"
    if skipped:
        msg += " — تخطي: " + ", ".join(skipped)
    return jsonify({'ok': True, 'msg': msg, 'count': imported})

@app.route('/api/export/download')
@role_required('admin')
@api_route
def api_export():
    data = {}
    for tab in TABLES:
        data[tab] = db_read(tab)
    return jsonify({'ok': True, 'data': data})

@app.route('/api/export-file')
@role_required('admin')
@api_route
def api_export_file():
    data = {}
    for tab in TABLES:
        data[tab] = db_read(tab)
    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    from flask import Response
    return Response(
        json_str,
        mimetype='application/json',
        headers={'Content-Disposition': 'attachment; filename=bustan_backup.json'}
    )

# ملاحظة أمان: مسار /api/debug-users الأصلي تم حذفه بالكامل — كان يكشف كلمات المرور.

# ================================================================
# التشغيل
# ================================================================
if USE_SHEETS:
    with app.app_context():
        log.info("Apps Script connected: " + APPS_SCRIPT_URL[:50] + "...")
else:
    with app.app_context():
        sqlite_init()
        log.info("SQLite ready")

if __name__ == '__main__':
    log.info(" http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=DEBUG_MODE)
