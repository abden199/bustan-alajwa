#!/usr/bin/env python3
"""بستان العجوة — Flask + Apps Script + Google Sheets"""

import os, json, base64, sqlite3, urllib.request, urllib.parse
from datetime import datetime
from flask import Flask, request, jsonify, render_template, g

app = Flask(__name__)
app.config['SECRET_KEY'] = 'bustan-alajwa-2026'

APPS_SCRIPT_URL = os.environ.get('APPS_SCRIPT_URL', '')
USE_SHEETS = bool(APPS_SCRIPT_URL)
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'bustan.db')

print("=" * 50)
if USE_SHEETS:
    print(" mode: Google Sheets (Apps Script)")
else:
    print(" mode: SQLite (local)")
    print(" db: " + DB_PATH)
print("=" * 50)

TABLES = {
    'users':        ['id','username','password','role','name','active'],
    'reps':         ['id','name','phone','dept','notes','active','pin'],
    'advances':     ['id','repId','amount','date','purpose','notes','status','settleDate'],
    'purchases':    ['id','advId','amount','taxableAmount','taxAmount','invoiceType','invoiceNo','costCenter','desc','date','notes','supplierName','supplierTaxNo','companyId'],
    'expenses':     ['id','repId','advId','amount','desc','date','costCenter','accountantNotes','managerNotes','status','actionDate'],
    'adv_requests': ['id','repId','amount','purpose','notes','status','requestDate','actionDate'],
    'suppliers':    ['id','name','taxNo','phone','email','active'],
    'companies':    ['id','name','taxNo','crNo','address','active']
}

def num(v):
    try:
        return float(v) if v not in (None, '', 'None') else 0
    except:
        return 0


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
        db.execute("INSERT INTO users VALUES (1,'admin','admin123','admin','مدير النظام','true')")
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
def api_data():
    try:
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
    except Exception as e:
        return jsonify({'ok': False, 'err': str(e)})

@app.route('/api/report-data')
def api_report():
    try:
        return jsonify({'ok': True, 'd': {
            'r': db_read('reps'),
            'a': db_read('advances'),
            'p': db_read('purchases'),
            'x': db_read('expenses'),
            'sup': db_read('suppliers'),
            'comp': db_read('companies')
        }})
    except Exception as e:
        return jsonify({'ok': False, 'err': str(e)})

@app.route('/api/rep-data/<int:rid>')
def api_rep(rid):
    try:
        advs = db_filtered('advances', 'repId', rid)
        ids = [int(a['id']) for a in advs]
        purs = [p for p in db_read('purchases') if int(p.get('advId', 0)) in ids]
        return jsonify({'ok': True, 'd': {'a': advs, 'p': purs}})
    except Exception as e:
        return jsonify({'ok': False, 'err': str(e)})


# ================================================================
# API: المصادقة
# ================================================================
@app.route('/api/auth', methods=['POST'])
def api_auth():
    try:
        d = request.json
        if d is None:
            return jsonify({'ok': False, 'err': 'لا توجد بيانات'})
        if isinstance(d, list):
            username = str(d[0]) if len(d) > 0 else ''
            password = str(d[1]) if len(d) > 1 else ''
        else:
            username = str(d.get('username', ''))
            password = str(d.get('password', ''))
        for u in db_read('users'):
            if str(u.get('username', '')) == username and str(u.get('password', '')) == password:
                if str(u.get('active', 'true')) == 'true':
                    return jsonify({'ok': True, 'user': {
                        'id': int(u['id']),
                        'username': u['username'],
                        'role': u.get('role', 'add'),
                        'name': u.get('name', username)
                    }})
        return jsonify({'ok': False, 'err': 'بيانات الدخول غير صحيحة'})
    except Exception as e:
        return jsonify({'ok': False, 'err': str(e)})


# ================================================================
# API: حفظ الكل
# ================================================================
@app.route('/api/save-all', methods=['POST'])
def api_save_all():
    try:
        d = request.json or {}
        if isinstance(d, list):
            return jsonify({'success': False, 'err': 'صيغة غير صحيحة'})
        for key, tab in [('reps', 'reps'), ('advances', 'advances'),
                         ('purchases', 'purchases'), ('expenses', 'expenses'),
                         ('suppliers', 'suppliers'), ('companies', 'companies')]:
            if key in d:
                db_write(tab, d[key])
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'err': str(e)})


# ================================================================
# API: الفواتير
# ================================================================
@app.route('/api/purchases', methods=['POST'])
def api_add_purchase():
    try:
        d = request.json or {}
        if isinstance(d, list):
            d = d[0] if d else {}
        nid = db_insert('purchases', {
            'advId': d.get('advId'),
            'amount': num(d.get('amount')),
            'taxableAmount': num(d.get('taxableAmount')),
            'taxAmount': num(d.get('taxAmount')),
            'invoiceType': d.get('invoiceType', ''),
            'invoiceNo': d.get('invoiceNo', ''),
            'costCenter': d.get('costCenter', ''),
            'desc': d.get('desc', ''),
            'date': d.get('date', ''),
            'notes': d.get('notes', ''),
            'supplierName': d.get('supplierName', ''),
            'supplierTaxNo': d.get('supplierTaxNo', ''),
            'companyId': d.get('companyId', '')
        })
        return jsonify({'success': True, 'id': nid})
    except Exception as e:
        return jsonify({'success': False, 'err': str(e)})

@app.route('/api/purchases/<int:pid>', methods=['PUT'])
def api_upd_purchase(pid):
    try:
        d = request.json or {}
        if isinstance(d, list):
            d = d[0] if d else {}
        db_update('purchases', pid, d)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'err': str(e)})

@app.route('/api/purchases/<int:pid>', methods=['DELETE'])
def api_del_purchase(pid):
    try:
        db_delete('purchases', pid)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'err': str(e)})


# ================================================================
# API: العهد
# ================================================================
@app.route('/api/advances', methods=['POST'])
def api_add_advance():
    try:
        d = request.json or {}
        if isinstance(d, list):
            d = d[0] if d else {}
        nid = db_insert('advances', {
            'repId': d.get('repId'),
            'amount': num(d.get('amount')),
            'date': d.get('date', ''),
            'purpose': d.get('purpose', ''),
            'notes': d.get('notes', ''),
            'status': d.get('status', 'open'),
            'settleDate': d.get('settleDate', '')
        })
        return jsonify({'success': True, 'id': nid})
    except Exception as e:
        return jsonify({'success': False, 'err': str(e)})

@app.route('/api/advances/<int:aid>', methods=['PUT'])
def api_upd_advance(aid):
    try:
        d = request.json or {}
        if isinstance(d, list):
            d = d[0] if d else {}
        db_update('advances', aid, d)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'err': str(e)})

@app.route('/api/advances/<int:aid>', methods=['DELETE'])
def api_del_advance(aid):
    try:
        db_delete('advances', aid)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'err': str(e)})


# ================================================================
# API: طلبات العهد
# ================================================================
@app.route('/api/adv-requests', methods=['POST'])
def api_add_request():
    try:
        d = request.json or {}
        if isinstance(d, list):
            d = d[0] if d else {}
        nid = db_insert('adv_requests', {
            'repId': d.get('repId'),
            'amount': num(d.get('amount')),
            'purpose': d.get('purpose', ''),
            'notes': d.get('notes', ''),
            'status': d.get('status', 'pending'),
            'requestDate': d.get('requestDate', ''),
            'actionDate': d.get('actionDate', '')
        })
        return jsonify({'success': True, 'id': nid})
    except Exception as e:
        return jsonify({'success': False, 'err': str(e)})

@app.route('/api/adv-requests/<int:rid>', methods=['PUT'])
def api_upd_request(rid):
    try:
        d = request.json or {}
        if isinstance(d, list):
            d = d[0] if d else {}
        db_update('adv_requests', rid, d)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'err': str(e)})


# ================================================================
# API: المصروفات
# ================================================================
@app.route('/api/expenses', methods=['POST'])
def api_add_expenses():
    try:
        items = request.json or []
        if isinstance(items, dict):
            items = [items]
        for item in items:
            if isinstance(item, list):
                continue
            db_insert('expenses', {
                'repId': item.get('repId'),
                'advId': item.get('advId'),
                'amount': num(item.get('amount')),
                'desc': item.get('desc', ''),
                'date': item.get('date', ''),
                'costCenter': item.get('costCenter', ''),
                'accountantNotes': item.get('accountantNotes', ''),
                'managerNotes': item.get('managerNotes', ''),
                'status': item.get('status', 'pending'),
                'actionDate': item.get('actionDate', '')
            })
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'err': str(e)})

@app.route('/api/expenses/<int:eid>', methods=['PUT'])
def api_upd_expense(eid):
    try:
        d = request.json or {}
        if isinstance(d, list):
            d = d[0] if d else {}
        db_update('expenses', eid, d)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'err': str(e)})


# ================================================================
# API: المستخدمين والموردين والشركات
# ================================================================
@app.route('/api/users', methods=['POST'])
def api_users():
    try:
        data = request.json or []
        if isinstance(data, dict):
            data = [data]
        db_write('users', data)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'err': str(e)})

@app.route('/api/suppliers', methods=['POST'])
def api_suppliers():
    try:
        data = request.json or []
        if isinstance(data, dict):
            data = [data]
        db_write('suppliers', data)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'err': str(e)})

@app.route('/api/companies', methods=['POST'])
def api_companies():
    try:
        data = request.json or []
        if isinstance(data, dict):
            data = [data]
        db_write('companies', data)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'err': str(e)})


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
def api_import():
    try:
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
    except Exception as e:
        return jsonify({'ok': False, 'err': str(e)})

@app.route('/api/export/download')
def api_export():
    try:
        data = {}
        for tab in TABLES:
            data[tab] = db_read(tab)
        return jsonify({'ok': True, 'data': data})
    except Exception as e:
        return jsonify({'ok': False, 'err': str(e)})

@app.route('/api/debug-users')
def debug_users():
    try:
        users = db_read('users')
        result = []
        for u in users:
            result.append({
                'id': u.get('id'),
                'username': repr(u.get('username')),
                'password': repr(u.get('password')),
                'password_type': type(u.get('password')).__name__,
                'active': repr(u.get('active')),
                'active_type': type(u.get('active')).__name__
            })
        return jsonify({'ok': True, 'count': len(users), 'users': result})
    except Exception as e:
        return jsonify({'ok': False, 'err': str(e)})
# ================================================================
# التشغيل
# ================================================================
if USE_SHEETS:
    with app.app_context():
        print("Apps Script connected: " + APPS_SCRIPT_URL[:50] + "...")
else:
    with app.app_context():
        sqlite_init()
        print("SQLite ready")

if __name__ == '__main__':
    print(" http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
