"""
Hospital Management System - Complete Web Interface
Matches new database schema (hospitalmanagementsystem_final.db)
Roles: admin, doctor, nurse, receptionist
Run: pip install flask && python hospital_web_final.py
"""

from flask import Flask, render_template_string, request, session, jsonify, redirect
import sqlite3, os
from datetime import datetime, date
from functools import wraps

app = Flask(__name__)
app.secret_key = 'hms-final-ultra-secure-2026-xK9#mPqL'
DB_NAME = "hospitalmanagementsystem_final.db"

# ── DB HELPERS ──────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn

def query_db(sql, params=()):
    conn = get_db()
    try:
        rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
        conn.close(); return rows
    except Exception as e:
        conn.close(); raise e

def mutate_db(sql, params=()):
    conn = get_db()
    try:
        cur = conn.execute(sql, params); conn.commit()
        r = {'rowcount': cur.rowcount, 'lastrowid': cur.lastrowid}
        conn.close(); return r
    except Exception as e:
        conn.close(); raise e

def exec_tx(stmts):
    conn = get_db()
    try:
        for sql, params in stmts: conn.execute(sql, params)
        conn.commit(); conn.close(); return True
    except Exception as e:
        conn.rollback(); conn.close(); raise e

def login_required(f):
    @wraps(f)
    def d(*a, **kw):
        if 'user_id' not in session: return redirect('/')
        return f(*a, **kw)
    return d

def admin_required(f):
    @wraps(f)
    def d(*a, **kw):
        if 'user_id' not in session: return redirect('/')
        if session.get('role') != 'admin':
            return jsonify({'error': 'Admin access only'}), 403
        return f(*a, **kw)
    return d

# ── STAFF ACCOUNTS (username → credentials) ──────────────────
# Doctors/nurses get real person_ids from DB at login time.
# Patients log in with person_id as username, date_of_birth as password.
STAFF_USERS = {
    'admin':      {'password':'admin123',  'role':'admin',        'name':'System Administrator'},
    'drsmith':    {'password':'doctor123', 'role':'doctor',       'db_index':0},
    'drjones':    {'password':'doctor123', 'role':'doctor',       'db_index':1},
    'drmwangi':   {'password':'doctor123', 'role':'doctor',       'db_index':2},
    'nurse1':     {'password':'nurse123',  'role':'nurse',        'db_index':0},
    'nurse2':     {'password':'nurse123',  'role':'nurse',        'db_index':1},
    'nurse3':     {'password':'nurse123',  'role':'nurse',        'db_index':2},
    'reception':  {'password':'recept123', 'role':'receptionist', 'name':'Front Desk'},
}

def resolve_staff(username):
    """Resolve a staff username to (person_id, display_name, role)."""
    u = STAFF_USERS.get(username)
    if not u: return None, None, None
    role = u['role']
    if role == 'admin':
        return None, u['name'], role
    if role == 'receptionist':
        return None, u.get('name','Front Desk'), role
    idx = u.get('db_index', 0)
    if role == 'doctor':
        rows = query_db("SELECT doc.person_id, p.first_name||' '||p.last_name AS fn FROM doctor doc JOIN person p ON doc.person_id=p.person_id ORDER BY doc.person_id")
        if rows:
            r = rows[min(idx, len(rows)-1)]
            return r['person_id'], 'Dr. '+r['fn'], role
    elif role == 'nurse':
        rows = query_db("SELECT n.person_id, p.first_name||' '||p.last_name AS fn FROM nurse n JOIN person p ON n.person_id=p.person_id ORDER BY n.person_id")
        if rows:
            r = rows[min(idx, len(rows)-1)]
            return r['person_id'], 'Nurse '+r['fn'], role
    return None, username, role

def resolve_patient(username, password):
    """Patients log in with person_id as username, DOB as password."""
    try:
        pid = int(username)
    except ValueError:
        return None, None
    rows = query_db("SELECT p.person_id, p.first_name||' '||p.last_name AS fn, p.date_of_birth FROM patient pt JOIN person p ON pt.person_id=p.person_id WHERE pt.person_id=?", (pid,))
    if not rows: return None, None
    r = rows[0]
    # Accept DOB in YYYY-MM-DD or DD/MM/YYYY or DD-MM-YYYY
    dob = r['date_of_birth'] or ''
    passwords_ok = [dob, dob.replace('-','/'), dob.replace('-','')]
    if password in passwords_ok:
        return r['person_id'], r['fn']
    return None, None

# ── HTML TEMPLATE ────────────────────────────────────────────
HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>MediCare HMS</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
:root {
  --primary:#2196F3;--primary2:#1565C0;--primary3:#64B5F6;--primary-light:#E3F2FD;
  --gold:#F59E0B;--gold2:#D97706;--gold3:#FCD34D;--gold-light:#FFFBEB;
  --teal:#0d9488;--teal-light:#ccfbf1;
  --emerald:#059669;--emerald-light:#d1fae5;
  --rose:#e11d48;--rose-light:#ffe4e6;
  --amber:#d97706;--amber-light:#fef3c7;
  --purple:#7c3aed;--purple-light:#ede9fe;
  --bg:#EFF6FF;--bg2:#DBEAFE;--surface:#ffffff;--surface2:#F0F7FF;
  --border:#BFDBFE;--border2:#93C5FD;
  --text:#0f172a;--text2:#1e3a5f;--text3:#475569;--text4:#94a3b8;
  --shadow:rgba(33,150,243,.14);--shadow2:rgba(33,150,243,.08);
  --gold-shadow:rgba(245,158,11,.25);
}
*{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{font-family:'Plus Jakarta Sans',sans-serif;color:var(--text);min-height:100vh;overflow-x:hidden;
  background:#EFF6FF;
  background-image:
    radial-gradient(ellipse 70% 50% at 0% 0%,rgba(147,197,253,.45) 0%,transparent 55%),
    radial-gradient(ellipse 50% 40% at 100% 0%,rgba(253,230,138,.3) 0%,transparent 50%),
    radial-gradient(ellipse 50% 40% at 50% 100%,rgba(191,219,254,.6) 0%,transparent 55%);
}
::-webkit-scrollbar{width:5px}::-webkit-scrollbar-track{background:#DBEAFE}::-webkit-scrollbar-thumb{background:linear-gradient(180deg,var(--primary),var(--gold));border-radius:10px}

/* ── LOGIN ── */
.login-scene{min-height:100vh;display:flex;position:relative;overflow:hidden;background:#EFF6FF}

/* Animated background particles */
.login-particles{position:absolute;inset:0;pointer-events:none;overflow:hidden;z-index:0}
.particle{position:absolute;border-radius:50%;animation:particleDrift linear infinite}
@keyframes particleDrift{
  0%{transform:translateY(100vh) translateX(0) scale(0);opacity:0}
  10%{opacity:1;transform:translateY(90vh) translateX(10px) scale(1)}
  90%{opacity:.6}
  100%{transform:translateY(-10vh) translateX(-20px) scale(.5);opacity:0}
}

/* Decorative geometric shapes */
.login-deco{position:absolute;inset:0;pointer-events:none;z-index:0;overflow:hidden}
.deco-ring{position:absolute;border-radius:50%;border:2px solid rgba(33,150,243,.15);animation:rotateDeco linear infinite}
@keyframes rotateDeco{from{transform:rotate(0deg) scale(1)}50%{transform:rotate(180deg) scale(1.05)}to{transform:rotate(360deg) scale(1)}}
.deco-hex{position:absolute;opacity:.07;animation:hexPulse 4s ease-in-out infinite alternate}
@keyframes hexPulse{from{opacity:.05;transform:scale(1)}to{opacity:.12;transform:scale(1.08)}}

.login-left{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:60px 40px;
  background:linear-gradient(145deg,#1565C0 0%,#1976D2 40%,#0D47A1 75%,#0a3570 100%);
  position:relative;overflow:hidden}

/* Glowing orbs on left panel */
.login-left .orb{position:absolute;border-radius:50%;filter:blur(60px);pointer-events:none;animation:orbFloat ease-in-out infinite alternate}
@keyframes orbFloat{from{transform:translateY(0) scale(1)}to{transform:translateY(-30px) scale(1.1)}}

/* Gold accent line */
.login-left::after{content:'';position:absolute;right:0;top:0;bottom:0;width:3px;
  background:linear-gradient(180deg,transparent 0%,var(--gold3) 30%,var(--gold) 50%,var(--gold3) 70%,transparent 100%)}

.brand-mark{display:flex;align-items:center;gap:18px;margin-bottom:40px;position:relative;z-index:2}
.brand-icon{position:relative;width:68px;height:68px;border-radius:20px;display:grid;place-items:center;font-size:30px;color:#fff;
  background:linear-gradient(135deg,rgba(245,158,11,.9),rgba(217,119,6,.95));
  box-shadow:0 8px 32px rgba(245,158,11,.5),0 0 0 2px rgba(255,255,255,.2);
  animation:iconPulse 3s ease-in-out infinite}
@keyframes iconPulse{0%,100%{box-shadow:0 8px 32px rgba(245,158,11,.5),0 0 0 2px rgba(255,255,255,.2)}50%{box-shadow:0 8px 48px rgba(245,158,11,.8),0 0 0 4px rgba(255,255,255,.15),0 0 60px rgba(245,158,11,.3)}}
.brand-name{font-family:'DM Serif Display',serif;font-size:38px;line-height:1;color:#fff}
.brand-name span{color:var(--gold3)}
.brand-tagline{font-size:10px;color:rgba(255,255,255,.6);letter-spacing:.2em;text-transform:uppercase;margin-top:5px}

/* Animated heartbeat line */
.heartbeat-line{position:relative;z-index:2;width:100%;max-width:300px;margin:0 auto 32px;height:50px}
.heartbeat-line svg{width:100%;height:100%;overflow:visible}
.heartbeat-path{fill:none;stroke:rgba(245,158,11,.8);stroke-width:2.5;stroke-dasharray:600;stroke-dashoffset:600;animation:drawLine 2.5s ease forwards,pulseStroke 2s 2.5s ease-in-out infinite}
@keyframes drawLine{to{stroke-dashoffset:0}}
@keyframes pulseStroke{0%,100%{stroke:rgba(245,158,11,.8)}50%{stroke:rgba(252,211,77,1)}}

.login-feat{position:relative;z-index:2;display:flex;flex-direction:column;gap:10px;width:100%;max-width:340px}
.login-feat-item{display:flex;align-items:center;gap:14px;background:rgba(255,255,255,.09);backdrop-filter:blur(12px);
  border-radius:14px;padding:13px 18px;border:1px solid rgba(255,255,255,.14);
  transition:all .3s;cursor:default;animation:featSlide .5s ease backwards}
@keyframes featSlide{from{opacity:0;transform:translateX(-20px)}to{opacity:1;transform:translateX(0)}}
.login-feat-item:hover{background:rgba(255,255,255,.16);border-color:rgba(245,158,11,.4);transform:translateX(4px)}
.feat-icon{width:36px;height:36px;border-radius:10px;background:linear-gradient(135deg,rgba(245,158,11,.3),rgba(217,119,6,.4));
  display:grid;place-items:center;font-size:16px;color:var(--gold3);flex-shrink:0;border:1px solid rgba(245,158,11,.3)}
.login-feat-item span{font-size:13px;color:rgba(255,255,255,.88);font-weight:500}

/* Welcome text */
.login-welcome{position:relative;z-index:2;text-align:center;margin-bottom:28px}
.login-welcome h2{font-family:'DM Serif Display',serif;font-size:28px;color:#fff;margin-bottom:6px}
.login-welcome p{font-size:12px;color:rgba(255,255,255,.6);letter-spacing:.05em}

/* Right panel */
.login-right{width:500px;display:flex;align-items:center;justify-content:center;padding:0;
  background:linear-gradient(160deg,#ffffff 0%,#F0F7FF 100%)}
.login-card{width:100%;max-width:400px;padding:50px 44px}

/* Decorative gold top bar on right */
.login-card-topbar{height:4px;width:60px;background:linear-gradient(90deg,var(--gold),var(--gold3));border-radius:4px;margin-bottom:36px}

.login-heading{font-family:'DM Serif Display',serif;font-size:32px;line-height:1.2;margin-bottom:6px;color:var(--text)}
.login-heading em{color:var(--primary2);font-style:italic}
.login-sub{color:var(--text3);font-size:13.5px;margin-bottom:30px;line-height:1.6}
.field{margin-bottom:16px}
.field label{display:block;font-size:10.5px;font-weight:800;text-transform:uppercase;letter-spacing:.12em;color:var(--text3);margin-bottom:7px}
.input-wrap{position:relative}
.input-wrap i{position:absolute;left:14px;top:50%;transform:translateY(-50%);color:var(--text4);font-size:14px;pointer-events:none;transition:color .2s}
.input-wrap input,.input-wrap select{width:100%;background:#F8FBFF;border:1.5px solid var(--border);border-radius:12px;color:var(--text);padding:13px 16px 13px 42px;font-family:'Plus Jakarta Sans',sans-serif;font-size:14px;outline:none;transition:all .25s}
.input-wrap input:focus,.input-wrap select:focus{border-color:var(--primary);background:#fff;box-shadow:0 0 0 3px rgba(33,150,243,.1)}
.input-wrap:focus-within i{color:var(--primary)}

/* Role selector pills */
.role-pills{display:grid;grid-template-columns:repeat(5,1fr);gap:6px;margin-bottom:16px}
.role-pill{display:flex;flex-direction:column;align-items:center;gap:4px;padding:10px 4px;border-radius:12px;border:1.5px solid var(--border);background:#F8FBFF;cursor:pointer;transition:all .25s;font-size:10px;font-weight:700;color:var(--text3);text-transform:uppercase;letter-spacing:.05em}
.role-pill i{font-size:18px;transition:color .2s}
.role-pill:hover{border-color:var(--primary);background:var(--primary-light);color:var(--primary2)}
.role-pill:hover i{color:var(--primary)}
.role-pill.active{border-color:var(--gold);background:var(--gold-light);color:var(--gold2);box-shadow:0 0 0 3px rgba(245,158,11,.12)}
.role-pill.active i{color:var(--gold)}

.btn-login{width:100%;padding:15px;border:none;border-radius:12px;
  background:linear-gradient(135deg,var(--primary) 0%,var(--primary2) 100%);
  color:#fff;font-family:'Plus Jakarta Sans',sans-serif;font-size:15px;font-weight:700;cursor:pointer;letter-spacing:.03em;
  display:flex;align-items:center;justify-content:center;gap:10px;transition:all .3s;
  box-shadow:0 6px 24px rgba(33,150,243,.4),0 0 0 0 rgba(245,158,11,0);margin-top:8px;position:relative;overflow:hidden}
.btn-login::before{content:'';position:absolute;inset:0;background:linear-gradient(135deg,rgba(245,158,11,.0),rgba(245,158,11,.0));transition:all .4s}
.btn-login:hover{transform:translateY(-2px);box-shadow:0 12px 36px rgba(33,150,243,.5)}
.btn-login:hover::before{background:linear-gradient(135deg,rgba(245,158,11,.15),rgba(245,158,11,.0))}
.btn-login:active{transform:translateY(0)}

/* Ripple on login button */
.btn-login .ripple{position:absolute;border-radius:50%;background:rgba(255,255,255,.3);transform:scale(0);animation:rippleAnim .6s linear;pointer-events:none}
@keyframes rippleAnim{to{transform:scale(4);opacity:0}}

.error-box{background:#fff1f2;border:1.5px solid #fecdd3;border-radius:10px;padding:12px 16px;color:#be123c;font-size:13px;margin-bottom:20px;display:flex;align-items:center;gap:10px;animation:shakeError .4s ease}
@keyframes shakeError{0%,100%{transform:translateX(0)}25%{transform:translateX(-6px)}75%{transform:translateX(6px)}}

.login-divider{display:flex;align-items:center;gap:12px;margin:20px 0;color:var(--text4);font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.1em}
.login-divider::before,.login-divider::after{content:'';flex:1;height:1px;background:var(--border)}

/* Role hidden select (for form submission compatibility) */
#loginRole{display:none}

/* ── APP SHELL ── */
.app{display:flex;min-height:100vh}
.sidebar{width:260px;min-width:260px;background:#fff;border-right:1.5px solid var(--border);display:flex;flex-direction:column;position:sticky;top:0;height:100vh;overflow-y:auto;box-shadow:2px 0 20px var(--shadow2)}
.sb-brand{padding:22px 20px 18px;border-bottom:1.5px solid var(--border);display:flex;align-items:center;gap:12px}
.sb-brand-icon{width:42px;height:42px;background:linear-gradient(135deg,var(--gold),var(--gold2));border-radius:12px;display:grid;place-items:center;font-size:20px;color:#fff;flex-shrink:0;box-shadow:0 4px 14px var(--gold-shadow)}
.sb-brand-text{font-family:'DM Serif Display',serif;font-size:20px;color:var(--text)}
.sb-brand-text span{color:var(--gold2)}
.sb-user{margin:14px 14px 0;background:linear-gradient(135deg,#f0f9ff,#e0f2fe);border:1.5px solid var(--border2);border-radius:14px;padding:14px;display:flex;align-items:center;gap:12px}
.sb-avatar{width:40px;height:40px;border-radius:50%;background:linear-gradient(135deg,var(--primary),var(--teal));display:grid;place-items:center;font-size:18px;color:#fff;flex-shrink:0}
.sb-user-name{font-weight:700;font-size:13px;line-height:1.2;color:var(--text)}
.sb-user-role{font-size:10px;text-transform:uppercase;letter-spacing:.1em;color:var(--gold2);font-weight:700;margin-top:2px}
.sb-nav{padding:16px 12px;flex:1}
.sb-section-label{font-size:10px;text-transform:uppercase;letter-spacing:.14em;color:var(--text4);padding:0 10px;margin:16px 0 5px;font-weight:700}
.sb-section-label:first-child{margin-top:0}
.nav-btn{display:flex;align-items:center;gap:12px;width:100%;padding:10px 12px;border-radius:10px;border:none;background:none;color:var(--text3);font-family:'Plus Jakarta Sans',sans-serif;font-size:13px;font-weight:600;cursor:pointer;transition:all .18s;text-align:left}
.nav-btn i{width:18px;text-align:center;font-size:14px;flex-shrink:0}
.nav-btn:hover{background:var(--primary-light);color:var(--primary2)}
.nav-btn.active{background:linear-gradient(135deg,#EFF6FF,#DBEAFE);color:var(--primary2);box-shadow:inset 3px 0 0 var(--gold);font-weight:700}
.sb-footer{padding:16px 12px;border-top:1.5px solid var(--border)}
.btn-signout{display:flex;align-items:center;justify-content:center;gap:10px;width:100%;padding:10px;border-radius:10px;border:1.5px solid #fecdd3;background:#fff1f2;color:#be123c;font-family:'Plus Jakarta Sans',sans-serif;font-size:13px;font-weight:700;cursor:pointer;transition:all .2s;text-decoration:none}
.btn-signout:hover{background:#ffe4e6;border-color:#fda4af}
.main{flex:1;display:flex;flex-direction:column;overflow:hidden;background:var(--bg)}
.topbar{background:#fff;border-bottom:1.5px solid var(--border);padding:14px 32px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100;box-shadow:0 2px 12px var(--shadow2)}
.topbar-title{font-family:'DM Serif Display',serif;font-size:22px;color:var(--text)}
.topbar-sub{font-size:12px;color:var(--text3);margin-top:1px}
.topbar-right{display:flex;align-items:center;gap:14px}
.topbar-time{font-family:'JetBrains Mono',monospace;font-size:12px;color:var(--gold2);background:var(--gold-light);border:1.5px solid var(--gold3);padding:6px 14px;border-radius:8px}
.pulse-dot{width:8px;height:8px;border-radius:50%;background:var(--emerald);box-shadow:0 0 0 0 rgba(5,150,105,.4);animation:pulse 2s infinite}
@keyframes pulse{0%,100%{box-shadow:0 0 0 0 rgba(5,150,105,.4)}50%{box-shadow:0 0 0 8px rgba(5,150,105,0)}}
.content{flex:1;padding:28px 32px;overflow-y:auto}
.page{animation:fadeUp .3s ease both}
@keyframes fadeUp{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:translateY(0)}}

/* ── STATS ── */
.stats-row{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:14px;margin-bottom:24px}
.chart-grid-2{display:grid;grid-template-columns:1fr 1fr;gap:20px}
.chart-grid-3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:20px}
.chart-card .tcard-header{padding-bottom:12px;border-bottom:1px solid var(--border)}
.chart-wrap{padding:16px 8px 8px;position:relative;height:260px}
.chart-wrap canvas{max-height:100%}
@media(max-width:1100px){.chart-grid-3{grid-template-columns:1fr 1fr}}
@media(max-width:800px){.chart-grid-2,.chart-grid-3{grid-template-columns:1fr}}
.stat-tile{background:#fff;border:1.5px solid var(--border);border-radius:18px;padding:22px 22px;position:relative;overflow:hidden;transition:transform .2s,box-shadow .2s,border-color .2s;cursor:pointer}
.stat-tile:hover{transform:translateY(-3px);box-shadow:0 12px 32px var(--shadow);border-color:var(--border2)}
.stat-tile::after{content:'';position:absolute;top:-20px;right:-20px;width:90px;height:90px;border-radius:50%;background:var(--tile-bg,#e0f2fe);opacity:.6}
.stat-tile-icon{width:46px;height:46px;border-radius:14px;background:var(--tile-bg,#e0f2fe);border:1.5px solid var(--tile-border,#bae6fd);display:grid;place-items:center;font-size:20px;margin-bottom:14px;color:var(--tile-color,var(--primary))}
.stat-tile-val{font-family:'DM Serif Display',serif;font-size:36px;line-height:1;color:var(--text)}
.stat-tile-lbl{font-size:11px;color:var(--text3);margin-top:4px;font-weight:700;text-transform:uppercase;letter-spacing:.06em}

/* ── TABLES ── */
.tcard{background:#fff;border:1.5px solid var(--border);border-radius:18px;overflow:hidden;margin-bottom:20px;box-shadow:0 2px 12px var(--shadow2)}
.tcard-header{padding:16px 22px;border-bottom:1.5px solid var(--border);display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;background:#fafcff}
.tcard-title{font-weight:800;font-size:15px;display:flex;align-items:center;gap:10px;color:var(--text)}
.tcard-title i{color:var(--primary);font-size:16px}
table{width:100%;border-collapse:collapse}
thead th{background:#f0f9ff;padding:11px 18px;text-align:left;font-size:10.5px;text-transform:uppercase;letter-spacing:.1em;color:var(--text3);font-weight:800;border-bottom:1.5px solid var(--border)}
tbody td{padding:12px 18px;border-bottom:1px solid #f1f5f9;font-size:13px;vertical-align:middle;color:var(--text2)}
tbody tr:last-child td{border-bottom:none}
tbody tr{transition:background .12s}
tbody tr:hover td{background:#f8fbff}

/* ── BADGES ── */
.badge{display:inline-flex;align-items:center;gap:5px;padding:4px 10px;border-radius:20px;font-size:11px;font-weight:700}
.b-green{background:var(--emerald-light);color:#065f46;border:1px solid #a7f3d0}
.b-red{background:var(--rose-light);color:#9f1239;border:1px solid #fda4af}
.b-amber{background:var(--amber-light);color:#92400e;border:1px solid #fcd34d}
.b-blue{background:var(--primary-light);color:var(--primary2);border:1px solid #bae6fd}
.b-teal{background:var(--teal-light);color:#134e4a;border:1px solid #99f6e4}
.b-purple{background:var(--purple-light);color:#4c1d95;border:1px solid #c4b5fd}

/* ── BUTTONS ── */
.btn{display:inline-flex;align-items:center;gap:7px;padding:9px 18px;border-radius:10px;border:none;font-family:'Plus Jakarta Sans',sans-serif;font-size:13px;font-weight:700;cursor:pointer;transition:all .2s;text-decoration:none}
.btn-teal{background:linear-gradient(135deg,var(--primary),var(--primary2));color:#fff;box-shadow:0 4px 14px rgba(14,165,233,.3)}
.btn-teal:hover{transform:translateY(-1px);box-shadow:0 6px 22px rgba(14,165,233,.45)}
.btn-ghost{background:var(--primary-light);color:var(--primary2);border:1.5px solid var(--border2)}
.btn-ghost:hover{background:#bae6fd;border-color:var(--primary3)}
.btn-danger{background:var(--rose-light);color:#be123c;border:1.5px solid #fda4af}
.btn-danger:hover{background:#fecdd3}
.btn-success{background:var(--emerald-light);color:#065f46;border:1.5px solid #a7f3d0}
.btn-success:hover{background:#a7f3d0}
.btn-sm{padding:6px 12px;font-size:12px;border-radius:8px}

/* ── FORMS ── */
.field-g{margin-bottom:16px}
.field-g label{display:block;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.1em;color:var(--text3);margin-bottom:7px}
.form-ctrl{width:100%;background:#f8fbff;border:1.5px solid var(--border2);border-radius:10px;color:var(--text);padding:11px 14px;font-family:'Plus Jakarta Sans',sans-serif;font-size:13px;outline:none;transition:all .2s}
.form-ctrl:focus{border-color:var(--primary);background:#fff;box-shadow:0 0 0 3px rgba(14,165,233,.1)}
textarea.form-ctrl{resize:vertical;min-height:80px}
.form-row{display:grid;grid-template-columns:1fr 1fr;gap:14px}

/* ── MODALS ── */
.overlay{display:none;position:fixed;inset:0;z-index:1000;background:rgba(15,23,42,.35);backdrop-filter:blur(6px);align-items:center;justify-content:center}
.overlay.open{display:flex;animation:fadeIn .2s ease}
@keyframes fadeIn{from{opacity:0}to{opacity:1}}
.modal{background:#fff;border:1.5px solid var(--border);border-radius:22px;padding:32px;width:560px;max-width:95vw;max-height:88vh;overflow-y:auto;box-shadow:0 24px 60px rgba(14,165,233,.15),0 4px 20px rgba(0,0,0,.08);animation:scaleIn .25s ease}
@keyframes scaleIn{from{transform:scale(.93);opacity:0}to{transform:scale(1);opacity:1}}
.modal-title{font-family:'DM Serif Display',serif;font-size:22px;margin-bottom:22px;display:flex;align-items:center;gap:12px;color:var(--text)}
.modal-title i{color:var(--primary);font-size:20px}
.modal-footer{display:flex;gap:10px;justify-content:flex-end;margin-top:22px;padding-top:18px;border-top:1.5px solid var(--border)}

/* ── SQL EDITOR ── */
.sql-editor{font-family:'JetBrains Mono',monospace;background:#f0f9ff;border:1.5px solid var(--border2);border-radius:12px;color:var(--primary2);padding:18px;font-size:13px;line-height:1.7;width:100%;min-height:130px;resize:vertical;outline:none}
.sql-editor:focus{border-color:var(--primary);box-shadow:0 0 0 3px rgba(14,165,233,.1)}
.sql-result{background:#f0f9ff;border:1.5px solid var(--border2);border-radius:12px;padding:18px;font-family:'JetBrains Mono',monospace;font-size:12px;max-height:380px;overflow:auto;white-space:pre;margin-top:14px;display:none;color:var(--text2);line-height:1.6}

/* ── PROFILE ── */
.profile-hero{background:linear-gradient(135deg,#e0f2fe,#ccfbf1);border:1.5px solid var(--border2);border-radius:20px;padding:32px;margin-bottom:20px;display:flex;align-items:center;gap:24px}
.profile-avatar{width:80px;height:80px;border-radius:50%;background:linear-gradient(135deg,var(--primary),var(--teal));display:grid;place-items:center;font-size:36px;color:#fff;flex-shrink:0;box-shadow:0 8px 24px rgba(14,165,233,.35)}
.profile-name{font-family:'DM Serif Display',serif;font-size:28px;color:var(--text);margin-bottom:4px}
.profile-sub{color:var(--primary2);font-size:13px;font-weight:700}
.info-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px}
.info-card{background:#fff;border:1.5px solid var(--border);border-radius:14px;padding:16px 20px}
.info-label{font-size:10px;text-transform:uppercase;letter-spacing:.12em;color:var(--text4);margin-bottom:5px;font-weight:700}
.info-val{font-size:14px;color:var(--text);font-weight:600}

/* ── SEARCH ── */
.search-bar{display:flex;gap:10px;align-items:center;flex-wrap:wrap}
.search-input{background:#f8fbff;border:1.5px solid var(--border2);border-radius:10px;color:var(--text);padding:9px 16px 9px 36px;font-family:'Plus Jakarta Sans',sans-serif;font-size:13px;outline:none;width:220px;transition:all .2s}
.search-input:focus{border-color:var(--primary);background:#fff;box-shadow:0 0 0 3px rgba(14,165,233,.1)}
.search-wrap{position:relative}
.search-wrap i{position:absolute;left:11px;top:50%;transform:translateY(-50%);color:var(--text4);font-size:13px;pointer-events:none}

/* ── ALERTS ── */
.alert{padding:12px 16px;border-radius:10px;font-size:13px;margin-bottom:14px;display:flex;align-items:center;gap:10px;font-weight:500}
.alert-success{background:var(--emerald-light);border:1.5px solid #a7f3d0;color:#065f46}
.alert-error{background:var(--rose-light);border:1.5px solid #fda4af;color:#9f1239}
.alert-info{background:var(--primary-light);border:1.5px solid #bae6fd;color:var(--primary2)}

/* ── LOADING ── */
.loading{text-align:center;padding:48px;color:var(--text3)}
.spinner{width:36px;height:36px;border:3px solid var(--primary-light);border-top-color:var(--primary);border-radius:50%;animation:spin .7s linear infinite;margin:0 auto 12px}
@keyframes spin{to{transform:rotate(360deg)}}

/* ── MISC ── */
.summary-2col{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:20px}

/* ── HEALTH CARDS (patient dashboard) ── */
.health-card{background:#fff;border:1.5px solid var(--border);border-radius:16px;padding:20px;display:flex;align-items:center;gap:16px;box-shadow:0 2px 10px var(--shadow2);transition:transform .2s,box-shadow .2s}
.health-card:hover{transform:translateY(-2px);box-shadow:0 8px 24px var(--shadow)}
.health-card-icon{width:52px;height:52px;border-radius:14px;display:grid;place-items:center;font-size:22px;flex-shrink:0}
.health-card-val{font-family:'DM Serif Display',serif;font-size:26px;color:var(--text);line-height:1}
.health-card-lbl{font-size:12px;color:var(--text3);font-weight:600;margin-top:3px}

/* ── BOOKING WIZARD ── */
.book-steps{display:flex;gap:0;margin-bottom:28px;background:#f8fbff;border:1.5px solid var(--border);border-radius:14px;overflow:hidden}
.book-step{flex:1;padding:14px 10px;text-align:center;font-size:12px;font-weight:700;color:var(--text4);border-right:1.5px solid var(--border);cursor:pointer;transition:all .2s;display:flex;flex-direction:column;align-items:center;gap:6px}
.book-step:last-child{border-right:none}
.book-step i{font-size:18px}
.book-step.active{background:linear-gradient(135deg,#e0f2fe,#bae6fd);color:var(--primary2)}
.book-step.done{background:var(--emerald-light);color:#065f46}
.doctor-card{background:#fff;border:1.5px solid var(--border);border-radius:14px;padding:18px;cursor:pointer;transition:all .2s;display:flex;align-items:center;gap:14px;margin-bottom:12px}
.doctor-card:hover{border-color:var(--primary);box-shadow:0 4px 16px var(--shadow)}
.doctor-card.selected{border-color:var(--primary);background:var(--primary-light);box-shadow:0 4px 16px var(--shadow)}
.doctor-card-avatar{width:50px;height:50px;border-radius:50%;background:linear-gradient(135deg,var(--primary),var(--teal));display:grid;place-items:center;font-size:22px;color:#fff;flex-shrink:0}
.doctor-card-name{font-weight:800;font-size:14px;color:var(--text)}
.doctor-card-spec{font-size:12px;color:var(--primary2);font-weight:600;margin-top:2px}
.doctor-card-fee{font-size:12px;color:var(--text3);margin-top:2px}
.time-slot{display:inline-flex;align-items:center;justify-content:center;padding:10px 16px;border-radius:10px;border:1.5px solid var(--border2);background:#f8fbff;font-size:13px;font-weight:700;cursor:pointer;transition:all .2s;margin:4px;color:var(--text2)}
.time-slot:hover{border-color:var(--primary);background:var(--primary-light);color:var(--primary2)}
.time-slot.selected{background:linear-gradient(135deg,var(--primary),var(--primary2));color:#fff;border-color:var(--primary);box-shadow:0 4px 12px rgba(14,165,233,.3)}

@media(max-width:900px){.summary-2col{grid-template-columns:1fr}.form-row{grid-template-columns:1fr}.login-scene{flex-direction:column}.login-left{min-height:220px;padding:32px 24px}.login-right{width:100%;padding:32px 20px}}

</style>
</head>
<body>

<!-- ══════════════ LOGIN PAGE ══════════════ -->
<div id="loginPage" class="login-scene" style="display:none">

  <!-- Left Panel -->
  <div class="login-left">
    <!-- Animated glowing orbs -->
    <div class="orb" style="width:400px;height:400px;background:rgba(245,158,11,.12);top:-150px;right:-100px;animation-duration:6s"></div>
    <div class="orb" style="width:300px;height:300px;background:rgba(33,150,243,.15);bottom:-100px;left:-80px;animation-duration:8s;animation-delay:-3s"></div>
    <div class="orb" style="width:200px;height:200px;background:rgba(245,158,11,.08);top:50%;left:20%;animation-duration:5s;animation-delay:-1s"></div>

    <!-- Deco rings -->
    <div class="login-deco">
      <div class="deco-ring" style="width:500px;height:500px;top:-200px;left:-200px;animation-duration:30s"></div>
      <div class="deco-ring" style="width:300px;height:300px;bottom:-100px;right:50px;animation-duration:20s;animation-direction:reverse;border-color:rgba(245,158,11,.12)"></div>
    </div>

    <div class="brand-mark">
      <div class="brand-icon"><i class="fas fa-heartbeat"></i></div>
      <div>
        <div class="brand-name">Medi<span>Care</span></div>
        <div class="brand-tagline">Hospital Management System</div>
      </div>
    </div>

    <div class="login-welcome">
      <h2>Advanced Healthcare<br>Management</h2>
      <p>Empowering medical teams with precision tools</p>
    </div>

    <!-- Animated ECG heartbeat SVG -->
    <div class="heartbeat-line">
      <svg viewBox="0 0 300 50" preserveAspectRatio="none">
        <path class="heartbeat-path" d="M0,25 L40,25 L55,10 L65,40 L75,5 L88,45 L100,25 L140,25 L160,25 L175,12 L185,38 L195,8 L208,42 L220,25 L260,25 L300,25"/>
      </svg>
    </div>

    <div class="login-feat">
      <div class="login-feat-item" style="animation-delay:.1s">
        <div class="feat-icon"><i class="fas fa-calendar-check"></i></div>
        <span>Smart appointment scheduling</span>
      </div>
      <div class="login-feat-item" style="animation-delay:.2s">
        <div class="feat-icon"><i class="fas fa-notes-medical"></i></div>
        <span>Complete electronic health records</span>
      </div>
      <div class="login-feat-item" style="animation-delay:.3s">
        <div class="feat-icon"><i class="fas fa-shield-alt"></i></div>
        <span>Role-based secure access control</span>
      </div>
      <div class="login-feat-item" style="animation-delay:.4s">
        <div class="feat-icon"><i class="fas fa-chart-line"></i></div>
        <span>Real-time analytics &amp; reporting</span>
      </div>
    </div>
  </div>

  <!-- Right Panel -->
  <div class="login-right">
    <div class="login-card">
      <div class="login-card-topbar"></div>

      <div style="display:flex;align-items:center;gap:10px;margin-bottom:28px">
        <div style="width:38px;height:38px;background:linear-gradient(135deg,var(--gold),var(--gold2));border-radius:10px;display:grid;place-items:center;font-size:17px;color:#fff;box-shadow:0 4px 14px var(--gold-shadow)"><i class="fas fa-heartbeat"></i></div>
        <span style="font-family:'DM Serif Display',serif;font-size:20px;color:var(--text)">Medi<span style="color:var(--gold2)">Care</span> <span style="color:var(--text3);font-size:14px;font-family:'Plus Jakarta Sans',sans-serif;font-weight:500">HMS</span></span>
      </div>

      <div class="login-heading">Welcome <em>back</em></div>
      <div class="login-sub">Select your role and sign in to continue</div>

      <div id="loginError" class="error-box" style="display:none"><i class="fas fa-exclamation-circle"></i><span></span></div>

      <!-- Role pills -->
      <div style="margin-bottom:16px">
        <div style="font-size:10.5px;font-weight:800;text-transform:uppercase;letter-spacing:.12em;color:var(--text3);margin-bottom:8px">Select Role</div>
        <div class="role-pills" id="rolePills">
          <div class="role-pill active" data-role="admin" onclick="selectRole('admin',this)">
            <i class="fas fa-shield-alt"></i>Admin
          </div>
          <div class="role-pill" data-role="doctor" onclick="selectRole('doctor',this)">
            <i class="fas fa-user-md"></i>Doctor
          </div>
          <div class="role-pill" data-role="nurse" onclick="selectRole('nurse',this)">
            <i class="fas fa-user-nurse"></i>Nurse
          </div>
          <div class="role-pill" data-role="receptionist" onclick="selectRole('receptionist',this)">
            <i class="fas fa-concierge-bell"></i>Front
          </div>
          <div class="role-pill" data-role="patient" onclick="selectRole('patient',this)">
            <i class="fas fa-procedures"></i>Patient
          </div>
        </div>
        <!-- Hidden select for form compat -->
        <select id="loginRole" onchange="updateLoginHint(this.value)">
          <option value="admin">Administrator</option>
          <option value="doctor">Doctor</option>
          <option value="nurse">Nurse</option>
          <option value="receptionist">Receptionist</option>
          <option value="patient">Patient</option>
        </select>
      </div>

      <div class="field">
        <label id="userLabel">Username</label>
        <div class="input-wrap"><i class="fas fa-user"></i><input id="loginUser" type="text" placeholder="Enter username" autocomplete="username"></div>
      </div>
      <div class="field">
        <label id="passLabel">Password</label>
        <div class="input-wrap"><i class="fas fa-lock"></i><input id="loginPass" type="password" placeholder="Enter password" autocomplete="current-password"></div>
      </div>

      <button class="btn-login" id="loginBtn" onclick="doLoginWithRipple(event)">
        <i class="fas fa-sign-in-alt"></i> Sign In
      </button>
    </div>
  </div>
</div>

<!-- ══════════════ APP SHELL ══════════════ -->
<div id="appShell" class="app" style="display:none">
  <!-- SIDEBAR -->
  <nav class="sidebar">
    <div class="sb-brand">
      <div class="sb-brand-icon"><i class="fas fa-heartbeat"></i></div>
      <div class="sb-brand-text">Medi<span>Care</span></div>
    </div>
    <div class="sb-user">
      <div class="sb-avatar"><i class="fas fa-user-circle"></i></div>
      <div><div class="sb-user-name" id="sbUserName">—</div><div class="sb-user-role" id="sbUserRole">—</div></div>
    </div>
    <div class="sb-nav" id="sidebarNav"></div>
    <div class="sb-footer">
      <a href="#" class="btn-signout" onclick="doLogout()"><i class="fas fa-sign-out-alt"></i> Sign Out</a>
    </div>
  </nav>
  <!-- MAIN -->
  <div class="main">
    <div class="topbar">
      <div><div class="topbar-title" id="topbarTitle">Dashboard</div><div class="topbar-sub" id="topbarSub">Hospital Management System</div></div>
      <div class="topbar-right">
        <div class="pulse-dot"></div>
        <div class="topbar-time" id="topbarClock">--:--:--</div>
      </div>
    </div>
    <div class="content" id="mainContent">
      <div class="loading"><div class="spinner"></div>Loading...</div>
    </div>
  </div>
</div>

<!-- ══════════════ MODALS ══════════════ -->

<!-- Add Patient Modal -->
<div class="overlay" id="modalAddPatient">
<div class="modal">
  <div class="modal-title"><i class="fas fa-user-plus"></i> Add New Patient</div>
  <div class="form-row">
    <div class="field-g"><label>First Name</label><input class="form-ctrl" id="pFirst" placeholder="First name"></div>
    <div class="field-g"><label>Last Name</label><input class="form-ctrl" id="pLast" placeholder="Last name"></div>
  </div>
  <div class="form-row">
    <div class="field-g"><label>ID Number</label><input class="form-ctrl" id="pIdNum" placeholder="e.g. 63-123456-A1"></div>
    <div class="field-g"><label>Date of Birth</label><input class="form-ctrl" id="pDob" type="date"></div>
  </div>
  <div class="form-row">
    <div class="field-g"><label>Gender</label><select class="form-ctrl" id="pGender"><option>Male</option><option>Female</option><option>Other</option></select></div>
    <div class="field-g"><label>Blood Type</label><select class="form-ctrl" id="pBlood"><option value="">Unknown</option><option>A+</option><option>A-</option><option>B+</option><option>B-</option><option>AB+</option><option>AB-</option><option>O+</option><option>O-</option></select></div>
  </div>
  <div class="form-row">
    <div class="field-g"><label>Phone</label><input class="form-ctrl" id="pPhone" placeholder="0771234567"></div>
    <div class="field-g"><label>Email</label><input class="form-ctrl" id="pEmail" placeholder="email@example.com"></div>
  </div>
  <div class="form-row">
    <div class="field-g"><label>Insurance Provider</label><input class="form-ctrl" id="pInsurer" placeholder="e.g. PSMAS"></div>
    <div class="field-g"><label>Insurance Number</label><input class="form-ctrl" id="pInsNum" placeholder="INS-XXXX"></div>
  </div>
  <div class="field-g"><label>Physical Address</label><textarea class="form-ctrl" id="pAddr" rows="2" placeholder="Street address..."></textarea></div>
  <div id="addPatientMsg"></div>
  <div class="modal-footer">
    <button class="btn btn-ghost" onclick="closeModal('modalAddPatient')">Cancel</button>
    <button class="btn btn-teal" onclick="submitAddPatient()"><i class="fas fa-save"></i> Save Patient</button>
  </div>
</div></div>

<!-- Add Appointment Modal -->
<div class="overlay" id="modalAddAppt">
<div class="modal">
  <div class="modal-title"><i class="fas fa-calendar-plus"></i> Schedule Appointment</div>
  <div class="form-row">
    <div class="field-g"><label>Patient</label><select class="form-ctrl" id="apptPatient" style="max-height:200px"></select></div>
    <div class="field-g"><label>Doctor</label><select class="form-ctrl" id="apptDoctor"></select></div>
  </div>
  <div class="form-row">
    <div class="field-g"><label>Date</label><input class="form-ctrl" id="apptDate" type="date"></div>
    <div class="field-g"><label>Time</label><input class="form-ctrl" id="apptTime" type="time" value="09:00"></div>
  </div>
  <div class="form-row">
    <div class="field-g"><label>Type</label><select class="form-ctrl" id="apptType"><option>Consultation</option><option>Follow-up</option><option>Emergency</option><option>Procedure</option><option>Check-up</option></select></div>
    <div class="field-g"><label>Duration (min)</label><input class="form-ctrl" id="apptDur" type="number" value="30" min="15" max="180"></div>
  </div>
  <div class="field-g"><label>Reason / Notes</label><textarea class="form-ctrl" id="apptNotes" rows="2" placeholder="Reason for appointment..."></textarea></div>
  <div id="addApptMsg"></div>
  <div class="modal-footer">
    <button class="btn btn-ghost" onclick="closeModal('modalAddAppt')">Cancel</button>
    <button class="btn btn-teal" onclick="submitAddAppt()"><i class="fas fa-calendar-check"></i> Schedule</button>
  </div>
</div></div>

<!-- Add Medical Record Modal -->
<div class="overlay" id="modalAddRecord">
<div class="modal">
  <div class="modal-title"><i class="fas fa-notes-medical"></i> Add Medical Record</div>
  <div class="field-g"><label>Patient</label><select class="form-ctrl" id="recPatient"></select></div>
  <div class="form-row">
    <div class="field-g"><label>Visit Date</label><input class="form-ctrl" id="recDate" type="date"></div>
    <div class="field-g"><label>Blood Pressure (Sys/Dia)</label><input class="form-ctrl" id="recBP" placeholder="e.g. 120/80"></div>
  </div>
  <div class="form-row">
    <div class="field-g"><label>Heart Rate (bpm)</label><input class="form-ctrl" id="recHR" type="number" placeholder="72"></div>
    <div class="field-g"><label>Temperature (°C)</label><input class="form-ctrl" id="recTemp" type="number" step="0.1" placeholder="36.5"></div>
  </div>
  <div class="form-row">
    <div class="field-g"><label>Weight (kg)</label><input class="form-ctrl" id="recWeight" type="number" step="0.1" placeholder="70"></div>
    <div class="field-g"><label>Height (cm)</label><input class="form-ctrl" id="recHeight" type="number" placeholder="170"></div>
  </div>
  <div class="field-g"><label>Symptoms</label><textarea class="form-ctrl" id="recSymptoms" rows="2" placeholder="Presenting symptoms..."></textarea></div>
  <div class="field-g"><label>Diagnosis</label><textarea class="form-ctrl" id="recDiag" rows="2" placeholder="Diagnosis..."></textarea></div>
  <div class="field-g"><label>Treatment</label><textarea class="form-ctrl" id="recTreatment" rows="2" placeholder="Treatment plan..."></textarea></div>
  <div class="field-g"><label>Follow-up Date</label><input class="form-ctrl" id="recFollowup" type="date"></div>
  <div id="addRecordMsg"></div>
  <div class="modal-footer">
    <button class="btn btn-ghost" onclick="closeModal('modalAddRecord')">Cancel</button>
    <button class="btn btn-teal" onclick="submitAddRecord()"><i class="fas fa-save"></i> Save Record</button>
  </div>
</div></div>

<!-- Add Doctor Modal -->
<div class="overlay" id="modalAddDoctor">
<div class="modal">
  <div class="modal-title"><i class="fas fa-user-md"></i> Add New Doctor</div>
  <div class="form-row">
    <div class="field-g"><label>First Name</label><input class="form-ctrl" id="drFirst" placeholder="First name"></div>
    <div class="field-g"><label>Last Name</label><input class="form-ctrl" id="drLast" placeholder="Last name"></div>
  </div>
  <div class="form-row">
    <div class="field-g"><label>Date of Birth</label><input class="form-ctrl" id="drDob" type="date"></div>
    <div class="field-g"><label>Gender</label><select class="form-ctrl" id="drGender"><option>Male</option><option>Female</option><option>Other</option></select></div>
  </div>
  <div class="form-row">
    <div class="field-g"><label>Phone</label><input class="form-ctrl" id="drPhone" placeholder="0771234567"></div>
    <div class="field-g"><label>Email</label><input class="form-ctrl" id="drEmail" placeholder="dr@hospital.com"></div>
  </div>
  <div class="form-row">
    <div class="field-g"><label>License Number</label><input class="form-ctrl" id="drLicense" placeholder="LIC-XXXX"></div>
    <div class="field-g"><label>Specialization</label><input class="form-ctrl" id="drSpec" placeholder="e.g. Cardiology"></div>
  </div>
  <div class="form-row">
    <div class="field-g"><label>Department</label><select class="form-ctrl" id="drDept"></select></div>
    <div class="field-g"><label>Years Experience</label><input class="form-ctrl" id="drExp" type="number" value="0" min="0"></div>
  </div>
  <div class="form-row">
    <div class="field-g"><label>Consultation Fee ($)</label><input class="form-ctrl" id="drFee" type="number" step="0.01" value="50"></div>
    <div class="field-g"><label>Max Appts/Day</label><input class="form-ctrl" id="drMaxAppts" type="number" value="20"></div>
  </div>
  <div class="field-g"><label>Qualifications</label><textarea class="form-ctrl" id="drQual" rows="2" placeholder="e.g. MBChB, FRCS..."></textarea></div>
  <div id="addDoctorMsg"></div>
  <div class="modal-footer">
    <button class="btn btn-ghost" onclick="closeModal('modalAddDoctor')">Cancel</button>
    <button class="btn btn-teal" onclick="submitAddDoctor()"><i class="fas fa-save"></i> Save Doctor</button>
  </div>
</div></div>

<!-- Add Nurse Modal -->
<div class="overlay" id="modalAddNurse">
<div class="modal">
  <div class="modal-title"><i class="fas fa-user-nurse"></i> Add New Nurse</div>
  <div class="form-row">
    <div class="field-g"><label>First Name</label><input class="form-ctrl" id="nrFirst" placeholder="First name"></div>
    <div class="field-g"><label>Last Name</label><input class="form-ctrl" id="nrLast" placeholder="Last name"></div>
  </div>
  <div class="form-row">
    <div class="field-g"><label>Date of Birth</label><input class="form-ctrl" id="nrDob" type="date"></div>
    <div class="field-g"><label>Gender</label><select class="form-ctrl" id="nrGender"><option>Male</option><option>Female</option><option>Other</option></select></div>
  </div>
  <div class="form-row">
    <div class="field-g"><label>Phone</label><input class="form-ctrl" id="nrPhone" placeholder="0771234567"></div>
    <div class="field-g"><label>Email</label><input class="form-ctrl" id="nrEmail" placeholder="nurse@hospital.com"></div>
  </div>
  <div class="form-row">
    <div class="field-g"><label>License Number</label><input class="form-ctrl" id="nrLicense" placeholder="NLN-XXXX"></div>
    <div class="field-g"><label>Ward</label><select class="form-ctrl" id="nrWard"></select></div>
  </div>
  <div class="form-row">
    <div class="field-g"><label>Qualification</label><input class="form-ctrl" id="nrQual" placeholder="e.g. RGN, BScN"></div>
    <div class="field-g"><label>Shift</label><select class="form-ctrl" id="nrShift"><option>Day</option><option>Night</option><option>Rotating</option></select></div>
  </div>
  <div id="addNurseMsg"></div>
  <div class="modal-footer">
    <button class="btn btn-ghost" onclick="closeModal('modalAddNurse')">Cancel</button>
    <button class="btn btn-teal" onclick="submitAddNurse()"><i class="fas fa-save"></i> Save Nurse</button>
  </div>
</div></div>

<!-- Prescription Modal -->
<div class="overlay" id="modalPrescription">
<div class="modal">
  <div class="modal-title"><i class="fas fa-prescription"></i> Issue Prescription</div>
  <input type="hidden" id="presRecordId">
  <div class="field-g"><label>Medicine</label><select class="form-ctrl" id="presMed"></select></div>
  <div class="form-row">
    <div class="field-g"><label>Dosage</label><input class="form-ctrl" id="presDosage" placeholder="e.g. 500mg"></div>
    <div class="field-g"><label>Frequency</label><input class="form-ctrl" id="presFreq" placeholder="e.g. Twice daily"></div>
  </div>
  <div class="form-row">
    <div class="field-g"><label>Duration (days)</label><input class="form-ctrl" id="presDur" type="number" value="7"></div>
    <div class="field-g"><label>Quantity</label><input class="form-ctrl" id="presQty" type="number" value="14"></div>
  </div>
  <div class="field-g"><label>Instructions</label><textarea class="form-ctrl" id="presInstr" rows="2" placeholder="Special instructions..."></textarea></div>
  <div id="prescriptionMsg"></div>
  <div class="modal-footer">
    <button class="btn btn-ghost" onclick="closeModal('modalPrescription')">Cancel</button>
    <button class="btn btn-teal" onclick="submitPrescription()"><i class="fas fa-save"></i> Issue Prescription</button>
  </div>
</div></div>

<!-- Lab Order Modal -->
<div class="overlay" id="modalLabOrder">
<div class="modal">
  <div class="modal-title"><i class="fas fa-flask"></i> Order Lab Test</div>
  <div class="field-g"><label>Patient</label><select class="form-ctrl" id="labPatient"></select></div>
  <div class="field-g"><label>Lab Test</label><select class="form-ctrl" id="labTest"></select></div>
  <div class="field-g"><label>Scheduled Date</label><input class="form-ctrl" id="labDate" type="date"></div>
  <div class="field-g"><label>Notes</label><textarea class="form-ctrl" id="labNotes" rows="2" placeholder="Special instructions..."></textarea></div>
  <div id="labOrderMsg"></div>
  <div class="modal-footer">
    <button class="btn btn-ghost" onclick="closeModal('modalLabOrder')">Cancel</button>
    <button class="btn btn-teal" onclick="submitLabOrder()"><i class="fas fa-save"></i> Order Test</button>
  </div>
</div></div>

<script>
// ══════════════════════════════════════════════
//  STATE
// ══════════════════════════════════════════════
let currentUser = null;
let currentPage = 'dashboard';

// ══════════════════════════════════════════════
//  BOOT
// ══════════════════════════════════════════════
window.addEventListener('DOMContentLoaded', async () => {
  startClock();
  const r = await fetch('/api/whoami');
  const d = await r.json();
  if (d.logged_in) {
    currentUser = d;
    showApp();
  } else {
    showLogin();
  }
});

function startClock() {
  const tick = () => {
    const now = new Date();
    document.getElementById('topbarClock').textContent =
      now.toLocaleTimeString('en-GB',{hour12:false});
  };
  tick();
  setInterval(tick, 1000);
}

// ══════════════════════════════════════════════
//  LOGIN / LOGOUT
// ══════════════════════════════════════════════
function showLogin() {
  document.getElementById('loginPage').style.display = 'flex';
  document.getElementById('appShell').style.display = 'none';
  document.getElementById('loginUser').addEventListener('keydown', e => { if(e.key==='Enter') doLogin(); });
  document.getElementById('loginPass').addEventListener('keydown', e => { if(e.key==='Enter') doLogin(); });
}

async function doLogin() {
  const u = document.getElementById('loginUser').value.trim();
  const p = document.getElementById('loginPass').value.trim();
  const r = document.getElementById('loginRole').value;
  const errEl = document.getElementById('loginError');
  errEl.style.display = 'none';
  if (!u || !p) { showLoginError('Please enter username and password.'); return; }
  try {
    const res = await fetch('/api/login', { method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({username:u, password:p, role:r}) });
    const d = await res.json();
    if (d.success) {
      currentUser = d;
      showApp();
    } else {
      showLoginError(d.error || 'Invalid credentials');
    }
  } catch(e) { showLoginError('Network error. Is the server running?'); }
}

function showLoginError(msg) {
  const el = document.getElementById('loginError');
  el.querySelector('span').textContent = msg;
  el.style.display = 'flex';
}

async function doLogout() {
  await fetch('/api/logout', {method:'POST'});
  currentUser = null;
  document.getElementById('loginPage').style.display = 'flex';
  document.getElementById('appShell').style.display = 'none';
  document.getElementById('loginUser').value = '';
  document.getElementById('loginPass').value = '';
  document.getElementById('loginError').style.display = 'none';
}

// ══════════════════════════════════════════════
//  APP SHELL
// ══════════════════════════════════════════════
function showApp() {
  document.getElementById('loginPage').style.display = 'none';
  document.getElementById('appShell').style.display = 'flex';
  document.getElementById('sbUserName').textContent = currentUser.name;
  document.getElementById('sbUserRole').textContent = currentUser.role.charAt(0).toUpperCase() + currentUser.role.slice(1);
  buildSidebar();
  navigate('dashboard');
}

function buildSidebar() {
  const role = currentUser.role;
  const nav = document.getElementById('sidebarNav');
  const pages = getPages(role);
  nav.innerHTML = pages.map(section => `
    <div class="sb-section-label">${section.label}</div>
    ${section.items.map(item => `
      <button class="nav-btn" id="nav_${item.id}" onclick="navigate('${item.id}')">
        <i class="fas fa-${item.icon}"></i>${item.label}
      </button>`).join('')}
  `).join('');
}

function getPages(role) {
  const common = [
    { label:'Overview', items:[{id:'dashboard',label:'Dashboard',icon:'home'}] },
    { label:'Appointments', items:[{id:'appointments',label:'Appointments',icon:'calendar-alt'}] },
  ];
  if (role === 'admin') return [
    ...common,
    { label:'People', items:[
      {id:'patients',label:'Patients',icon:'users'},
      {id:'doctors',label:'Doctors',icon:'user-md'},
      {id:'nurses',label:'Nurses',icon:'user-nurse'},
    ]},
    { label:'Medical', items:[
      {id:'records',label:'Medical Records',icon:'notes-medical'},
      {id:'prescriptions',label:'Prescriptions',icon:'prescription-bottle-alt'},
      {id:'labtests',label:'Lab Tests',icon:'flask'},
    ]},
    { label:'Facilities', items:[
      {id:'admissions',label:'Admissions',icon:'procedures'},
      {id:'wards',label:'Wards & Rooms',icon:'hospital'},
      {id:'departments',label:'Departments',icon:'building'},
    ]},
    { label:'Finance', items:[
      {id:'invoices',label:'Invoices',icon:'file-invoice-dollar'},
      {id:'medicines',label:'Medicines',icon:'pills'},
    ]},
    { label:'Admin', items:[
      {id:'statistics',label:'Statistics & Analytics',icon:'chart-bar'},
      {id:'sql',label:'SQL Runner',icon:'database'},
    ]},
  ];
  if (role === 'doctor') return [
    ...common,
    { label:'My Patients', items:[
      {id:'patients',label:'My Patients',icon:'users'},
      {id:'records',label:'Medical Records',icon:'notes-medical'},
      {id:'prescriptions',label:'Prescriptions',icon:'prescription-bottle-alt'},
      {id:'labtests',label:'Lab Tests',icon:'flask'},
    ]},
    { label:'Info', items:[
      {id:'medicines',label:'Medicines',icon:'pills'},
      {id:'departments',label:'Departments',icon:'building'},
    ]},
    { label:'Account', items:[
      {id:'my_profile',label:'My Profile',icon:'id-card'},
    ]},
  ];
  if (role === 'nurse') return [
    ...common,
    { label:'Ward', items:[
      {id:'patients',label:'Patients',icon:'users'},
      {id:'admissions',label:'Admissions',icon:'procedures'},
      {id:'records',label:'Medical Records',icon:'notes-medical'},
    ]},
    { label:'Info', items:[
      {id:'wards',label:'Wards & Rooms',icon:'hospital'},
      {id:'medicines',label:'Medicines',icon:'pills'},
    ]},
    { label:'Account', items:[
      {id:'my_profile',label:'My Profile',icon:'id-card'},
    ]},
  ];
  if (role === 'patient') return [
    { label:'My Health', items:[
      {id:'dashboard',label:'My Dashboard',icon:'home'},
      {id:'book_appointment',label:'Book Appointment',icon:'calendar-plus'},
      {id:'my_appointments',label:'My Appointments',icon:'calendar-alt'},
      {id:'my_records',label:'My Medical Records',icon:'notes-medical'},
      {id:'my_prescriptions',label:'My Prescriptions',icon:'prescription-bottle-alt'},
      {id:'my_labtests',label:'My Lab Tests',icon:'flask'},
      {id:'my_invoices',label:'My Bills',icon:'file-invoice-dollar'},
      {id:'my_profile',label:'My Profile',icon:'id-card'},
    ]},
  ];
  // receptionist
  return [
    ...common,
    { label:'Registration', items:[
      {id:'patients',label:'Patients',icon:'users'},
    ]},
    { label:'Facilities', items:[
      {id:'admissions',label:'Admissions',icon:'procedures'},
      {id:'departments',label:'Departments',icon:'building'},
    ]},
    { label:'Finance', items:[
      {id:'invoices',label:'Invoices',icon:'file-invoice-dollar'},
    ]},
  ];
}

function navigate(page) {
  currentPage = page;
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  const btn = document.getElementById('nav_'+page);
  if (btn) btn.classList.add('active');
  loadPage(page);
}

// ══════════════════════════════════════════════
//  PAGE LOADER
// ══════════════════════════════════════════════
async function loadPage(page) {
  destroyCharts();
  const content = document.getElementById('mainContent');
  content.innerHTML = '<div class="loading"><div class="spinner"></div>Loading...</div>';
  const titles = {
    dashboard:'Dashboard', patients:'Patients', doctors:'Doctors', nurses:'Nurses',
    appointments:'Appointments', records:'Medical Records', prescriptions:'Prescriptions',
    labtests:'Lab Tests', admissions:'Admissions', wards:'Wards & Rooms',
    departments:'Departments', invoices:'Invoices', medicines:'Medicines', sql:'SQL Runner',
    book_appointment:'Book an Appointment', statistics:'Statistics & Analytics',
    my_profile:'My Profile'
  };
  document.getElementById('topbarTitle').textContent = titles[page] || page;
  document.getElementById('topbarSub').textContent = 'Hospital Management System';

  try {
    if (page === 'dashboard') await renderDashboard();
    else if (page === 'patients') await renderPatients();
    else if (page === 'doctors') await renderDoctors();
    else if (page === 'nurses') await renderNurses();
    else if (page === 'appointments') await renderAppointments();
    else if (page === 'records') await renderRecords();
    else if (page === 'prescriptions') await renderPrescriptions();
    else if (page === 'labtests') await renderLabTests();
    else if (page === 'admissions') await renderAdmissions();
    else if (page === 'wards') await renderWards();
    else if (page === 'departments') await renderDepartments();
    else if (page === 'invoices') await renderInvoices();
    else if (page === 'medicines') await renderMedicines();
    else if (page === 'sql') renderSQL();
    else if (page === 'my_appointments') await renderMyAppointments();
    else if (page === 'book_appointment') await renderBookAppointment();
    else if (page === 'my_records') await renderMyRecords();
    else if (page === 'my_prescriptions') await renderMyPrescriptions();
    else if (page === 'my_labtests') await renderMyLabTests();
    else if (page === 'my_invoices') await renderMyInvoices();
    else if (page === 'my_profile') await renderMyProfile();
    else if (page === 'statistics') await renderStatistics();
  } catch(e) {
    content.innerHTML = `<div class="alert alert-error"><i class="fas fa-exclamation-triangle"></i>Error loading page: ${e.message}</div>`;
  }
}

// ══════════════════════════════════════════════
//  DASHBOARD
// ══════════════════════════════════════════════
async function renderDashboard() {
  const d = await fetch('/api/dashboard').then(r=>r.json());
  const role = currentUser.role;

  if (role === 'patient') { await renderPatientDashboard(d); return; }
  if (role === 'admin') { await renderAdminDashboard(d); return; }

  const tileThemes = [
    {bg:'#EFF6FF',border:'#93C5FD',color:'#1565C0'},
    {bg:'#FFFBEB',border:'#FCD34D',color:'#D97706'},
    {bg:'#d1fae5',border:'#a7f3d0',color:'#059669'},
    {bg:'#ede9fe',border:'#c4b5fd',color:'#7c3aed'},
    {bg:'#ffe4e6',border:'#fda4af',color:'#e11d48'},
    {bg:'#ccfbf1',border:'#99f6e4',color:'#0d9488'},
  ];
  const iconMap = {Patients:'users',Doctors:'user-md',Nurses:'user-nurse',Appointments:'calendar-alt',
    'Today Appointments':'calendar-check',Departments:'building','Available Rooms':'bed',
    Wards:'hospital','Lab Tests':'flask',Invoices:'file-invoice-dollar',Medicines:'pills',
    Admissions:'procedures','My Appointments':'calendar-alt','Patients Seen':'users',
    'Medical Records':'notes-medical','Prescriptions':'prescription-bottle-alt',
    'Total Appointments':'calendar-alt','Total Patients':'users',
    'Today\'s Patients':'users','Active Admissions':'procedures',
    'Ward Patients':'users','Pending Orders':'flask'};
  let i=0;
  let statsHtml = '';
  for(const [k,v] of Object.entries(d.stats)) {
    const th = tileThemes[i%tileThemes.length]; const ic = iconMap[k]||'circle';
    statsHtml += `<div class="stat-tile" style="--tile-bg:${th.bg};--tile-border:${th.border};--tile-color:${th.color}">
      <div class="stat-tile-icon"><i class="fas fa-${ic}"></i></div>
      <div class="stat-tile-val">${v}</div><div class="stat-tile-lbl">${k}</div></div>`; i++;
  }

  let apptHtml = '';
  if (d.today_appts && d.today_appts.length) {
    apptHtml = `<div class="tcard"><div class="tcard-header"><div class="tcard-title"><i class="fas fa-clock"></i> Today's Appointments</div></div>
    <table><thead><tr><th>Time</th><th>Patient</th><th>Doctor</th><th>Status</th></tr></thead><tbody>
    ${d.today_appts.map(a=>`<tr>
      <td><span style="font-family:'JetBrains Mono',monospace;color:var(--primary2);font-weight:600">${(a.appt_datetime||'').substring(11,16)}</span></td>
      <td><strong>${a.patient_name||'—'}</strong></td><td>${a.doctor_name||'—'}</td>
      <td>${statusBadge(a.status)}</td></tr>`).join('')}
    </tbody></table></div>`;
  } else {
    apptHtml = `<div class="alert alert-info"><i class="fas fa-calendar-check"></i>No appointments scheduled for today.</div>`;
  }

  document.getElementById('mainContent').innerHTML = `<div class="page">
    <div class="stats-row">${statsHtml}</div>${apptHtml}</div>`;
}

// ══════════════════════════════════════════════
//  ADMIN DASHBOARD WITH CHARTS
// ══════════════════════════════════════════════
let _adminCharts = {};

function destroyCharts() {
  Object.values(_adminCharts).forEach(c => { try { c.destroy(); } catch(e){} });
  _adminCharts = {};
}

async function renderAdminDashboard(d) {
  destroyCharts();

  // Stat tiles
  const tileThemes = [
    {bg:'#EFF6FF',border:'#93C5FD',color:'#1565C0',icon:'users'},
    {bg:'#FFFBEB',border:'#FCD34D',color:'#D97706',icon:'user-md'},
    {bg:'#d1fae5',border:'#a7f3d0',color:'#059669',icon:'user-nurse'},
    {bg:'#ede9fe',border:'#c4b5fd',color:'#7c3aed',icon:'calendar-alt'},
    {bg:'#ffe4e6',border:'#fda4af',color:'#e11d48',icon:'building'},
    {bg:'#EFF6FF',border:'#93C5FD',color:'#1565C0',icon:'bed'},
    {bg:'#FFFBEB',border:'#FCD34D',color:'#D97706',icon:'pills'},
    {bg:'#d1fae5',border:'#a7f3d0',color:'#059669',icon:'procedures'},
  ];
  const statKeys = Object.keys(d.stats);
  let statsHtml = statKeys.map((k,i) => {
    const th = tileThemes[i % tileThemes.length];
    return `<div class="stat-tile" style="--tile-bg:${th.bg};--tile-border:${th.border};--tile-color:${th.color}">
      <div class="stat-tile-icon"><i class="fas fa-${th.icon}"></i></div>
      <div class="stat-tile-val">${d.stats[k]}</div><div class="stat-tile-lbl">${k}</div></div>`;
  }).join('');

  // Today appts table
  let apptHtml = d.today_appts && d.today_appts.length ?
    `<table><thead><tr><th>Time</th><th>Patient</th><th>Doctor</th><th>Status</th></tr></thead><tbody>
    ${d.today_appts.map(a=>`<tr>
      <td><span style="font-family:'JetBrains Mono',monospace;color:var(--primary2);font-weight:600">${(a.appt_datetime||'').substring(11,16)}</span></td>
      <td><strong>${a.patient_name||'—'}</strong></td><td>${a.doctor_name||'—'}</td>
      <td>${statusBadge(a.status)}</td></tr>`).join('')}
    </tbody></table>` :
    `<div style="text-align:center;padding:30px;color:var(--text4)"><i class="fas fa-calendar-check" style="font-size:28px;display:block;margin-bottom:10px"></i>No appointments today</div>`;

  document.getElementById('mainContent').innerHTML = `<div class="page">

    <!-- KPI Tiles -->
    <div class="stats-row">${statsHtml}</div>

    <!-- Charts Row 1 -->
    <div class="chart-grid-2" style="margin-top:24px">
      <div class="tcard chart-card">
        <div class="tcard-header">
          <div class="tcard-title"><i class="fas fa-chart-line" style="color:var(--primary)"></i> Appointments — Last 6 Months</div>
        </div>
        <div class="chart-wrap"><canvas id="chartMonthly"></canvas></div>
      </div>
      <div class="tcard chart-card">
        <div class="tcard-header">
          <div class="tcard-title"><i class="fas fa-chart-pie" style="color:var(--gold2)"></i> Appointment Status</div>
        </div>
        <div class="chart-wrap" style="max-height:240px;display:flex;align-items:center;justify-content:center"><canvas id="chartApptStatus"></canvas></div>
      </div>
    </div>

    <!-- Charts Row 2 -->
    <div class="chart-grid-3" style="margin-top:20px">
      <div class="tcard chart-card">
        <div class="tcard-header">
          <div class="tcard-title"><i class="fas fa-venus-mars" style="color:var(--teal)"></i> Patient Gender</div>
        </div>
        <div class="chart-wrap" style="max-height:220px;display:flex;align-items:center;justify-content:center"><canvas id="chartGender"></canvas></div>
      </div>
      <div class="tcard chart-card">
        <div class="tcard-header">
          <div class="tcard-title"><i class="fas fa-file-invoice-dollar" style="color:var(--emerald)"></i> Invoice Status</div>
        </div>
        <div class="chart-wrap" style="max-height:220px;display:flex;align-items:center;justify-content:center"><canvas id="chartInvoice"></canvas></div>
      </div>
      <div class="tcard chart-card">
        <div class="tcard-header">
          <div class="tcard-title"><i class="fas fa-flask" style="color:var(--purple)"></i> Lab Test Results</div>
        </div>
        <div class="chart-wrap" style="max-height:220px;display:flex;align-items:center;justify-content:center"><canvas id="chartLab"></canvas></div>
      </div>
    </div>

    <!-- Charts Row 3 -->
    <div class="chart-grid-2" style="margin-top:20px">
      <div class="tcard chart-card">
        <div class="tcard-header">
          <div class="tcard-title"><i class="fas fa-building" style="color:var(--primary2)"></i> Doctors per Department</div>
        </div>
        <div class="chart-wrap"><canvas id="chartDepts"></canvas></div>
      </div>
      <div class="tcard chart-card">
        <div class="tcard-header">
          <div class="tcard-title"><i class="fas fa-hospital" style="color:var(--teal)"></i> Ward Bed Occupancy</div>
        </div>
        <div class="chart-wrap"><canvas id="chartWards"></canvas></div>
      </div>
    </div>

    <!-- Low Stock + Today Appointments -->
    <div class="chart-grid-2" style="margin-top:20px">
      <div class="tcard chart-card">
        <div class="tcard-header">
          <div class="tcard-title"><i class="fas fa-exclamation-triangle" style="color:var(--rose)"></i> Low Stock Medicines</div>
        </div>
        <div class="chart-wrap"><canvas id="chartLowStock"></canvas></div>
      </div>
      <div class="tcard">
        <div class="tcard-header">
          <div class="tcard-title"><i class="fas fa-clock" style="color:var(--gold2)"></i> Today's Schedule</div>
        </div>
        ${apptHtml}
      </div>
    </div>

  </div>`;

  // Fetch chart data and render
  try {
    const s = await fetch('/api/admin_stats').then(r=>r.json());
    _buildAdminCharts(s);
  } catch(e) {
    console.error('Chart data error:', e);
  }
}

function _buildAdminCharts(s) {
  const BLUE = '#2196F3', GOLD = '#F59E0B', TEAL = '#0d9488',
        GREEN = '#059669', PURPLE = '#7c3aed', ROSE = '#e11d48',
        AMBER = '#D97706', NAVY = '#1565C0';

  const chartDefaults = {
    responsive:true, maintainAspectRatio:true,
    plugins:{ legend:{ labels:{ font:{family:"'Plus Jakarta Sans',sans-serif",size:12}, color:'#334155' } } },
  };

  // 1. Monthly appointments line chart
  const months = s.appt_monthly.map(r=>r.month);
  const monthCounts = s.appt_monthly.map(r=>r.c);
  _adminCharts.monthly = new Chart(document.getElementById('chartMonthly'), {
    type:'line',
    data:{
      labels: months,
      datasets:[{
        label:'Appointments',
        data: monthCounts,
        borderColor: BLUE,
        backgroundColor: 'rgba(33,150,243,.1)',
        borderWidth: 3,
        fill: true,
        tension: 0.45,
        pointBackgroundColor: GOLD,
        pointBorderColor: GOLD,
        pointRadius: 5,
        pointHoverRadius: 7,
      }]
    },
    options:{...chartDefaults, scales:{
      y:{ beginAtZero:true, ticks:{color:'#64748b'}, grid:{color:'rgba(0,0,0,.05)'} },
      x:{ ticks:{color:'#64748b'}, grid:{display:false} }
    }}
  });

  // 2. Appointment status doughnut
  const apptColors = {'Scheduled':BLUE,'Completed':GREEN,'Cancelled':ROSE,'No-Show':AMBER,'Checked In':TEAL};
  _adminCharts.apptStatus = new Chart(document.getElementById('chartApptStatus'), {
    type:'doughnut',
    data:{
      labels: s.appt_status.map(r=>r.status),
      datasets:[{
        data: s.appt_status.map(r=>r.c),
        backgroundColor: s.appt_status.map(r=>apptColors[r.status]||NAVY),
        borderWidth: 3, borderColor: '#fff', hoverOffset: 8,
      }]
    },
    options:{...chartDefaults, cutout:'65%', plugins:{...chartDefaults.plugins, legend:{position:'right',labels:{...chartDefaults.plugins.legend.labels}}}}
  });

  // 3. Gender pie
  const genderColors = {'Male':BLUE,'Female':ROSE,'Other':TEAL,'Unknown':AMBER};
  _adminCharts.gender = new Chart(document.getElementById('chartGender'), {
    type:'pie',
    data:{
      labels: s.gender.map(r=>r.gender||'Unknown'),
      datasets:[{
        data: s.gender.map(r=>r.c),
        backgroundColor: s.gender.map(r=>genderColors[r.gender]||PURPLE),
        borderWidth: 3, borderColor:'#fff', hoverOffset:6,
      }]
    },
    options:{...chartDefaults, plugins:{...chartDefaults.plugins, legend:{position:'bottom',labels:{...chartDefaults.plugins.legend.labels}}}}
  });

  // 4. Invoice status doughnut
  const invColors = {'Paid':GREEN,'Pending':GOLD,'Overdue':ROSE,'Partially Paid':TEAL};
  _adminCharts.invoice = new Chart(document.getElementById('chartInvoice'), {
    type:'doughnut',
    data:{
      labels: s.inv_status.map(r=>r.payment_status),
      datasets:[{
        data: s.inv_status.map(r=>r.c),
        backgroundColor: s.inv_status.map(r=>invColors[r.payment_status]||NAVY),
        borderWidth:3, borderColor:'#fff', hoverOffset:6,
      }]
    },
    options:{...chartDefaults, cutout:'60%', plugins:{...chartDefaults.plugins, legend:{position:'bottom',labels:{...chartDefaults.plugins.legend.labels}}}}
  });

  // 5. Lab results doughnut
  const lab = s.lab_results || {};
  _adminCharts.lab = new Chart(document.getElementById('chartLab'), {
    type:'doughnut',
    data:{
      labels:['Normal','Abnormal','Pending'],
      datasets:[{
        data:[lab.normal||0, lab.abnormal||0, lab.pending||0],
        backgroundColor:[GREEN, ROSE, AMBER],
        borderWidth:3, borderColor:'#fff', hoverOffset:6,
      }]
    },
    options:{...chartDefaults, cutout:'60%', plugins:{...chartDefaults.plugins, legend:{position:'bottom',labels:{...chartDefaults.plugins.legend.labels}}}}
  });

  // 6. Doctors per department horizontal bar
  _adminCharts.depts = new Chart(document.getElementById('chartDepts'), {
    type:'bar',
    data:{
      labels: s.departments.map(r=>r.dept_name),
      datasets:[{
        label:'Doctors',
        data: s.departments.map(r=>r.c),
        backgroundColor: s.departments.map((_,i)=>[BLUE,GOLD,TEAL,GREEN,PURPLE,ROSE][i%6]),
        borderRadius: 8, borderSkipped: false,
      }]
    },
    options:{...chartDefaults, indexAxis:'y',
      scales:{
        x:{beginAtZero:true, ticks:{stepSize:1,color:'#64748b'}, grid:{color:'rgba(0,0,0,.05)'}},
        y:{ticks:{color:'#334155'}, grid:{display:false}},
      }
    }
  });

  // 7. Ward occupancy grouped bar
  _adminCharts.wards = new Chart(document.getElementById('chartWards'), {
    type:'bar',
    data:{
      labels: s.wards.map(r=>r.ward_name),
      datasets:[
        {label:'Total Beds', data:s.wards.map(r=>r.total_beds), backgroundColor:'rgba(33,150,243,.25)', borderColor:BLUE, borderWidth:2, borderRadius:6},
        {label:'Occupied',   data:s.wards.map(r=>r.occupied),   backgroundColor:'rgba(245,158,11,.7)', borderColor:GOLD, borderWidth:2, borderRadius:6},
      ]
    },
    options:{...chartDefaults,
      scales:{
        y:{beginAtZero:true, ticks:{color:'#64748b'}, grid:{color:'rgba(0,0,0,.05)'}},
        x:{ticks:{color:'#334155',maxRotation:30}, grid:{display:false}},
      }
    }
  });

  // 8. Low stock horizontal bar
  _adminCharts.lowStock = new Chart(document.getElementById('chartLowStock'), {
    type:'bar',
    data:{
      labels: s.low_stock.map(r=>r.medicine_name),
      datasets:[
        {label:'In Stock',      data:s.low_stock.map(r=>r.quantity_in_stock), backgroundColor:'rgba(229,57,53,.7)',  borderColor:ROSE, borderWidth:2, borderRadius:6},
        {label:'Reorder Level', data:s.low_stock.map(r=>r.reorder_level),     backgroundColor:'rgba(245,158,11,.35)', borderColor:GOLD, borderWidth:2, borderRadius:6},
      ]
    },
    options:{...chartDefaults, indexAxis:'y',
      scales:{
        x:{beginAtZero:true, ticks:{color:'#64748b'}, grid:{color:'rgba(0,0,0,.05)'}},
        y:{ticks:{color:'#334155',font:{size:11}}, grid:{display:false}},
      }
    }
  });
}

async function renderPatientDashboard(d) {
  const uid = currentUser.user_id;
  const [appts, records] = await Promise.all([
    fetch('/api/my/appointments').then(r=>r.json()),
    fetch('/api/my/records').then(r=>r.json()),
  ]);
  const upcoming = appts.filter(a=>a.status==='Scheduled'||a.status==='Checked In').slice(0,3);
  const nextAppt = upcoming[0];

  document.getElementById('mainContent').innerHTML = `<div class="page">
    <div style="background:linear-gradient(135deg,#0ea5e9,#0369a1,#0d9488);border-radius:20px;padding:28px 32px;margin-bottom:24px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:16px">
      <div>
        <div style="font-size:13px;color:rgba(255,255,255,.75);font-weight:600;text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px"><i class="fas fa-hand-sparkles"></i> Welcome Back</div>
        <div style="font-family:'DM Serif Display',serif;font-size:28px;color:#fff;margin-bottom:6px">${currentUser.name}</div>
        <div style="font-size:13px;color:rgba(255,255,255,.8)">Patient ID: <strong>${uid}</strong> &nbsp;·&nbsp; ${new Date().toLocaleDateString('en-GB',{weekday:'long',year:'numeric',month:'long',day:'numeric'})}</div>
      </div>
      <button class="btn" style="background:rgba(255,255,255,.18);color:#fff;border:1.5px solid rgba(255,255,255,.3);backdrop-filter:blur(8px);font-size:14px;padding:12px 22px;border-radius:14px" onclick="navigate('book_appointment')">
        <i class="fas fa-calendar-plus"></i> Book Appointment
      </button>
    </div>

    <div class="stats-row" style="grid-template-columns:repeat(auto-fill,minmax(160px,1fr))">
      <div class="stat-tile" style="--tile-bg:#e0f2fe;--tile-border:#bae6fd;--tile-color:#0284c7">
        <div class="stat-tile-icon"><i class="fas fa-calendar-check"></i></div>
        <div class="stat-tile-val">${appts.length}</div><div class="stat-tile-lbl">Appointments</div>
      </div>
      <div class="stat-tile" style="--tile-bg:#d1fae5;--tile-border:#a7f3d0;--tile-color:#059669">
        <div class="stat-tile-icon"><i class="fas fa-notes-medical"></i></div>
        <div class="stat-tile-val">${records.length}</div><div class="stat-tile-lbl">Medical Records</div>
      </div>
      <div class="stat-tile" style="--tile-bg:#fef3c7;--tile-border:#fcd34d;--tile-color:#d97706" onclick="navigate('my_prescriptions')" style="cursor:pointer">
        <div class="stat-tile-icon"><i class="fas fa-prescription-bottle-alt"></i></div>
        <div class="stat-tile-val">${d.stats['Prescriptions']||0}</div><div class="stat-tile-lbl">Prescriptions</div>
      </div>
      <div class="stat-tile" style="--tile-bg:#ffe4e6;--tile-border:#fda4af;--tile-color:#e11d48" onclick="navigate('my_invoices')">
        <div class="stat-tile-icon"><i class="fas fa-file-invoice-dollar"></i></div>
        <div class="stat-tile-val">${d.stats['Pending Bills']||0}</div><div class="stat-tile-lbl">Pending Bills</div>
      </div>
    </div>

    ${nextAppt ? `
    <div class="tcard" style="margin-bottom:20px">
      <div class="tcard-header" style="background:linear-gradient(135deg,#f0f9ff,#e0f2fe)">
        <div class="tcard-title"><i class="fas fa-clock" style="color:var(--primary)"></i> Next Appointment</div>
        <span class="badge b-blue"><i class="fas fa-calendar"></i> Upcoming</span>
      </div>
      <div style="padding:20px 22px;display:flex;align-items:center;gap:20px;flex-wrap:wrap">
        <div style="width:56px;height:56px;border-radius:50%;background:linear-gradient(135deg,var(--primary),var(--teal));display:grid;place-items:center;font-size:24px;color:#fff;flex-shrink:0"><i class="fas fa-user-md"></i></div>
        <div style="flex:1">
          <div style="font-weight:800;font-size:16px;color:var(--text)">Dr. ${nextAppt.doctor_name}</div>
          <div style="font-size:13px;color:var(--text3);margin-top:2px">${nextAppt.specialization||''}</div>
          <div style="font-size:13px;color:var(--primary2);font-weight:600;margin-top:6px"><i class="fas fa-calendar-alt"></i> ${(nextAppt.appt_datetime||'').replace('T',' ').substring(0,16)} &nbsp;·&nbsp; ${nextAppt.appt_type}</div>
        </div>
        ${statusBadge(nextAppt.status)}
      </div>
    </div>` : `
    <div class="alert alert-info" style="cursor:pointer" onclick="navigate('book_appointment')">
      <i class="fas fa-calendar-plus"></i> You have no upcoming appointments. <strong>Click here to book one!</strong>
    </div>`}

    ${records.length > 0 ? `
    <div class="tcard">
      <div class="tcard-header"><div class="tcard-title"><i class="fas fa-notes-medical"></i> Recent Medical Records</div>
        <button class="btn btn-ghost btn-sm" onclick="navigate('my_records')"><i class="fas fa-arrow-right"></i> View All</button>
      </div>
      <table><thead><tr><th>Date</th><th>Diagnosis</th><th>Doctor</th><th>Follow-up</th></tr></thead><tbody>
      ${records.slice(0,3).map(r=>`<tr>
        <td><span style="font-family:'JetBrains Mono',monospace;color:var(--primary2)">${r.visit_date||'—'}</span></td>
        <td><strong>${r.diagnosis||'Visit'}</strong></td>
        <td>Dr. ${r.doctor_name||'—'}</td>
        <td>${r.follow_up_date?`<span class="badge b-amber"><i class="fas fa-calendar"></i> ${r.follow_up_date}</span>`:'<span class="badge b-green">None</span>'}</td>
      </tr>`).join('')}
      </tbody></table>
    </div>` : ''}
  </div>`;
}


//  PATIENTS
// ══════════════════════════════════════════════
async function renderPatients() {
  const rows = await fetch('/api/patients').then(r=>r.json());
  const canAdd = ['admin','receptionist'].includes(currentUser.role);
  const canDelete = currentUser.role === 'admin';
  document.getElementById('mainContent').innerHTML = `<div class="page">
    <div class="tcard">
      <div class="tcard-header">
        <div class="tcard-title"><i class="fas fa-users"></i> All Patients (${rows.length})</div>
        <div class="search-bar">
          <div class="search-wrap"><i class="fas fa-search"></i><input class="search-input" placeholder="Search..." oninput="filterTable('patientsTable',this.value)"></div>
          ${canAdd?`<button class="btn btn-teal btn-sm" onclick="openAddPatient()"><i class="fas fa-plus"></i> Add Patient</button>`:''}
        </div>
      </div>
      <table id="patientsTable">
        <thead><tr><th>#</th><th>Name</th><th>Phone</th><th>Gender</th><th>Blood</th><th>DOB</th><th>Insurance</th>${canDelete?'<th>Actions</th>':''}</tr></thead>
        <tbody>
        ${rows.map(r=>`<tr>
          <td><span style="font-family:'JetBrains Mono',monospace;color:var(--primary2)">${r.person_id}</span></td>
          <td><strong style="color:var(--text)">${r.first_name} ${r.last_name}</strong></td>
          <td>${r.phone_number||'—'}</td>
          <td>${r.gender||'—'}</td>
          <td><span class="badge b-red">${r.blood_type||'?'}</span></td>
          <td>${r.date_of_birth||'—'}</td>
          <td>${r.insurance_provider||'—'}</td>
          ${canDelete?`<td><button class="btn btn-danger btn-sm" onclick="deletePatient(${r.person_id})"><i class="fas fa-trash"></i></button></td>`:''}
        </tr>`).join('')}
        </tbody>
      </table>
    </div></div>`;
}

async function openAddPatient() {
  document.getElementById('addPatientMsg').innerHTML = '';
  openModal('modalAddPatient');
}

async function submitAddPatient() {
  const data = {
    first_name: document.getElementById('pFirst').value.trim(),
    last_name: document.getElementById('pLast').value.trim(),
    id_number: document.getElementById('pIdNum').value.trim(),
    date_of_birth: document.getElementById('pDob').value,
    gender: document.getElementById('pGender').value,
    blood_type: document.getElementById('pBlood').value,
    phone_number: document.getElementById('pPhone').value.trim(),
    email: document.getElementById('pEmail').value.trim(),
    physical_address: document.getElementById('pAddr').value.trim(),
    insurance_provider: document.getElementById('pInsurer').value.trim(),
    insurance_number: document.getElementById('pInsNum').value.trim(),
  };
  if (!data.first_name || !data.last_name || !data.phone_number || !data.date_of_birth) {
    showMsg('addPatientMsg','error','Please fill in required fields (name, DOB, phone).'); return;
  }
  const r = await fetch('/api/admin/add_patient',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  const d = await r.json();
  if (d.success) { closeModal('modalAddPatient'); renderPatients(); }
  else showMsg('addPatientMsg','error', d.error||'Failed to add patient');
}

async function deletePatient(id) {
  if (!confirm('Delete this patient and all their records? This cannot be undone.')) return;
  const r = await fetch('/api/admin/delete_patient',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id})});
  const d = await r.json();
  if (d.success) renderPatients();
  else alert('Error: ' + (d.error||'Unknown error'));
}

// ══════════════════════════════════════════════
//  DOCTORS
// ══════════════════════════════════════════════
async function renderDoctors() {
  const rows = await fetch('/api/doctors').then(r=>r.json());
  const canAdd = currentUser.role === 'admin';
  document.getElementById('mainContent').innerHTML = `<div class="page">
    <div class="tcard">
      <div class="tcard-header">
        <div class="tcard-title"><i class="fas fa-user-md"></i> Doctors (${rows.length})</div>
        <div class="search-bar">
          <div class="search-wrap"><i class="fas fa-search"></i><input class="search-input" placeholder="Search..." oninput="filterTable('doctorsTable',this.value)"></div>
          ${canAdd?`<button class="btn btn-teal btn-sm" onclick="openAddDoctor()"><i class="fas fa-plus"></i> Add Doctor</button>`:''}
        </div>
      </div>
      <table id="doctorsTable">
        <thead><tr><th>#</th><th>Name</th><th>Specialization</th><th>Department</th><th>Phone</th><th>Fee ($)</th><th>Exp</th>${canAdd?'<th>Actions</th>':''}</tr></thead>
        <tbody>
        ${rows.map(r=>`<tr>
          <td><span style="font-family:'JetBrains Mono',monospace;color:var(--primary2)">${r.person_id}</span></td>
          <td><strong style="color:var(--text)">Dr. ${r.first_name} ${r.last_name}</strong></td>
          <td><span class="badge b-blue">${r.specialization||'—'}</span></td>
          <td>${r.dept_name||'—'}</td>
          <td>${r.phone_number||'—'}</td>
          <td>$${(r.consultation_fee||0).toFixed(2)}</td>
          <td>${r.years_experience||0} yrs</td>
          ${canAdd?`<td><button class="btn btn-danger btn-sm" onclick="deleteDoctor(${r.person_id})"><i class="fas fa-trash"></i></button></td>`:''}
        </tr>`).join('')}
        </tbody>
      </table>
    </div></div>`;
}

async function openAddDoctor() {
  const depts = await fetch('/api/departments_list').then(r=>r.json());
  document.getElementById('drDept').innerHTML = depts.map(d=>`<option value="${d.dept_id}">${d.dept_name}</option>`).join('');
  document.getElementById('addDoctorMsg').innerHTML = '';
  openModal('modalAddDoctor');
}

async function submitAddDoctor() {
  const data = {
    first_name: document.getElementById('drFirst').value.trim(),
    last_name: document.getElementById('drLast').value.trim(),
    date_of_birth: document.getElementById('drDob').value,
    gender: document.getElementById('drGender').value,
    phone_number: document.getElementById('drPhone').value.trim(),
    email: document.getElementById('drEmail').value.trim(),
    license_number: document.getElementById('drLicense').value.trim(),
    specialization: document.getElementById('drSpec').value.trim(),
    dept_id: document.getElementById('drDept').value,
    years_experience: document.getElementById('drExp').value,
    consultation_fee: document.getElementById('drFee').value,
    max_appointments_per_day: document.getElementById('drMaxAppts').value,
    qualification: document.getElementById('drQual').value.trim(),
  };
  if (!data.first_name || !data.last_name || !data.phone_number || !data.license_number) {
    showMsg('addDoctorMsg','error','Please fill required fields.'); return;
  }
  const r = await fetch('/api/admin/add_doctor',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  const d = await r.json();
  if (d.success) { closeModal('modalAddDoctor'); renderDoctors(); }
  else showMsg('addDoctorMsg','error', d.error||'Failed to add doctor');
}

async function deleteDoctor(id) {
  if (!confirm('Delete this doctor? All their appointments and records will also be deleted.')) return;
  const r = await fetch('/api/admin/delete_doctor',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id})});
  const d = await r.json();
  if (d.success) renderDoctors();
  else alert('Error: ' + (d.error||'Unknown error'));
}

// ══════════════════════════════════════════════
//  NURSES
// ══════════════════════════════════════════════
async function renderNurses() {
  const rows = await fetch('/api/nurses').then(r=>r.json());
  const canAdd = currentUser.role === 'admin';
  document.getElementById('mainContent').innerHTML = `<div class="page">
    <div class="tcard">
      <div class="tcard-header">
        <div class="tcard-title"><i class="fas fa-user-nurse"></i> Nurses (${rows.length})</div>
        <div class="search-bar">
          <div class="search-wrap"><i class="fas fa-search"></i><input class="search-input" placeholder="Search..." oninput="filterTable('nursesTable',this.value)"></div>
          ${canAdd?`<button class="btn btn-teal btn-sm" onclick="openAddNurse()"><i class="fas fa-plus"></i> Add Nurse</button>`:''}
        </div>
      </div>
      <table id="nursesTable">
        <thead><tr><th>#</th><th>Name</th><th>License</th><th>Qualification</th><th>Ward</th><th>Shift</th><th>Phone</th>${canAdd?'<th>Actions</th>':''}</tr></thead>
        <tbody>
        ${rows.map(r=>`<tr>
          <td><span style="font-family:'JetBrains Mono',monospace;color:var(--primary2)">${r.person_id}</span></td>
          <td><strong style="color:var(--text)">${r.first_name} ${r.last_name}</strong></td>
          <td><span style="font-family:'JetBrains Mono',monospace">${r.license_number||'—'}</span></td>
          <td>${r.qualification||'—'}</td>
          <td><span class="badge b-teal">${r.ward_name||'—'}</span></td>
          <td>${r.shift||'—'}</td>
          <td>${r.phone_number||'—'}</td>
          ${canAdd?`<td><button class="btn btn-danger btn-sm" onclick="deleteNurse(${r.person_id})"><i class="fas fa-trash"></i></button></td>`:''}
        </tr>`).join('')}
        </tbody>
      </table>
    </div></div>`;
}

async function openAddNurse() {
  const wards = await fetch('/api/wards_list').then(r=>r.json());
  document.getElementById('nrWard').innerHTML = wards.map(w=>`<option value="${w.ward_id}">${w.ward_name}</option>`).join('');
  document.getElementById('addNurseMsg').innerHTML = '';
  openModal('modalAddNurse');
}

async function submitAddNurse() {
  const data = {
    first_name: document.getElementById('nrFirst').value.trim(),
    last_name: document.getElementById('nrLast').value.trim(),
    date_of_birth: document.getElementById('nrDob').value,
    gender: document.getElementById('nrGender').value,
    phone_number: document.getElementById('nrPhone').value.trim(),
    email: document.getElementById('nrEmail').value.trim(),
    license_number: document.getElementById('nrLicense').value.trim(),
    ward_id: document.getElementById('nrWard').value,
    qualification: document.getElementById('nrQual').value.trim(),
    shift: document.getElementById('nrShift').value,
  };
  if (!data.first_name || !data.last_name || !data.phone_number || !data.license_number) {
    showMsg('addNurseMsg','error','Please fill required fields.'); return;
  }
  const r = await fetch('/api/admin/add_nurse',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  const d = await r.json();
  if (d.success) { closeModal('modalAddNurse'); renderNurses(); }
  else showMsg('addNurseMsg','error', d.error||'Failed to add nurse');
}

async function deleteNurse(id) {
  if (!confirm('Delete this nurse?')) return;
  const r = await fetch('/api/admin/delete_nurse',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id})});
  const d = await r.json();
  if (d.success) renderNurses();
  else alert('Error: ' + (d.error||'Unknown error'));
}

// ══════════════════════════════════════════════
//  APPOINTMENTS
// ══════════════════════════════════════════════
async function renderAppointments() {
  const rows = await fetch('/api/appointments').then(r=>r.json());
  const canAdd = ['admin','receptionist','doctor'].includes(currentUser.role);
  document.getElementById('mainContent').innerHTML = `<div class="page">
    <div class="tcard">
      <div class="tcard-header">
        <div class="tcard-title"><i class="fas fa-calendar-alt"></i> Appointments (${rows.length})</div>
        <div class="search-bar">
          <div class="search-wrap"><i class="fas fa-search"></i><input class="search-input" placeholder="Search..." oninput="filterTable('apptsTable',this.value)"></div>
          ${canAdd?`<button class="btn btn-teal btn-sm" onclick="openAddAppt()"><i class="fas fa-plus"></i> Schedule</button>`:''}
        </div>
      </div>
      <table id="apptsTable">
        <thead><tr><th>#</th><th>Patient</th><th>Doctor</th><th>Date & Time</th><th>Type</th><th>Status</th><th>Actions</th></tr></thead>
        <tbody>
        ${rows.map(r=>`<tr>
          <td><span style="font-family:'JetBrains Mono',monospace;color:var(--primary2)">${r.appt_id}</span></td>
          <td>${r.patient_name||'—'}</td>
          <td>${r.doctor_name||'—'}</td>
          <td><span style="font-family:'JetBrains Mono',monospace">${(r.appt_datetime||'').replace('T',' ').substring(0,16)}</span></td>
          <td>${r.appt_type||'—'}</td>
          <td>${statusBadge(r.status)}</td>
          <td>
            <select class="form-ctrl" style="padding:4px 8px;font-size:11px;border-radius:6px;width:120px" onchange="updateApptStatus(${r.appt_id},this.value)">
              ${['Scheduled','Checked In','Completed','Cancelled','No Show'].map(s=>`<option ${s===r.status?'selected':''}>${s}</option>`).join('')}
            </select>
            ${currentUser.role==='admin'?`<button class="btn btn-danger btn-sm" style="margin-left:4px" onclick="deleteAppt(${r.appt_id})"><i class="fas fa-trash"></i></button>`:''}
          </td>
        </tr>`).join('')}
        </tbody>
      </table>
    </div></div>`;
}

async function openAddAppt() {
  const [patients, doctors] = await Promise.all([
    fetch('/api/patients_list').then(r=>r.json()),
    fetch('/api/doctors_list').then(r=>r.json()),
  ]);
  document.getElementById('apptPatient').innerHTML = patients.map(p=>`<option value="${p.person_id}">${p.first_name} ${p.last_name}</option>`).join('');
  document.getElementById('apptDoctor').innerHTML = doctors.map(d=>`<option value="${d.person_id}">Dr. ${d.first_name} ${d.last_name} (${d.specialization||''})</option>`).join('');
  document.getElementById('apptDate').value = new Date().toISOString().substring(0,10);
  document.getElementById('addApptMsg').innerHTML = '';
  openModal('modalAddAppt');
}

async function submitAddAppt() {
  const data = {
    patient_id: document.getElementById('apptPatient').value,
    doctor_id: document.getElementById('apptDoctor').value,
    appt_date: document.getElementById('apptDate').value,
    appt_time: document.getElementById('apptTime').value,
    appt_type: document.getElementById('apptType').value,
    duration_minutes: document.getElementById('apptDur').value,
    reason: document.getElementById('apptNotes').value,
  };
  if (!data.appt_date || !data.appt_time) { showMsg('addApptMsg','error','Please select date and time.'); return; }
  const r = await fetch('/api/add_appointment',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  const d = await r.json();
  if (d.success) { closeModal('modalAddAppt'); renderAppointments(); }
  else showMsg('addApptMsg','error', d.error||'Failed to schedule appointment');
}

async function updateApptStatus(id, status) {
  await fetch('/api/update_appointment',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id,status})});
}

async function deleteAppt(id) {
  if (!confirm('Delete this appointment?')) return;
  await fetch('/api/delete_appointment',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id})});
  renderAppointments();
}

// ══════════════════════════════════════════════
//  MEDICAL RECORDS
// ══════════════════════════════════════════════
async function renderRecords() {
  const rows = await fetch('/api/records').then(r=>r.json());
  const canAdd = ['admin','doctor'].includes(currentUser.role);
  document.getElementById('mainContent').innerHTML = `<div class="page">
    <div class="tcard">
      <div class="tcard-header">
        <div class="tcard-title"><i class="fas fa-notes-medical"></i> Medical Records (${rows.length})</div>
        <div class="search-bar">
          <div class="search-wrap"><i class="fas fa-search"></i><input class="search-input" placeholder="Search..." oninput="filterTable('recordsTable',this.value)"></div>
          ${canAdd?`<button class="btn btn-teal btn-sm" onclick="openAddRecord()"><i class="fas fa-plus"></i> Add Record</button>`:''}
        </div>
      </div>
      <table id="recordsTable">
        <thead><tr><th>#</th><th>Patient</th><th>Doctor</th><th>Date</th><th>Diagnosis</th><th>Vitals</th>${canAdd?'<th>Actions</th>':''}</tr></thead>
        <tbody>
        ${rows.map(r=>`<tr>
          <td><span style="font-family:'JetBrains Mono',monospace;color:var(--primary2)">${r.record_id}</span></td>
          <td>${r.patient_name||'—'}</td>
          <td>${r.doctor_name||'—'}</td>
          <td>${r.visit_date||'—'}</td>
          <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${r.diagnosis||'—'}</td>
          <td style="font-size:11px;font-family:'JetBrains Mono',monospace">${r.blood_pressure_systolic?`BP:${r.blood_pressure_systolic}/${r.blood_pressure_diastolic} `:''} ${r.heart_rate?`HR:${r.heart_rate} `:''} ${r.temperature?`T:${r.temperature}°C`:''}</td>
          ${canAdd?`<td>
            <button class="btn btn-success btn-sm" onclick="openPrescription(${r.record_id})" title="Prescribe"><i class="fas fa-prescription"></i></button>
            <button class="btn btn-danger btn-sm" onclick="deleteRecord(${r.record_id})"><i class="fas fa-trash"></i></button>
          </td>`:''}
        </tr>`).join('')}
        </tbody>
      </table>
    </div></div>`;
}

async function openAddRecord() {
  const patients = await fetch('/api/patients_list').then(r=>r.json());
  document.getElementById('recPatient').innerHTML = patients.map(p=>`<option value="${p.person_id}">${p.first_name} ${p.last_name}</option>`).join('');
  document.getElementById('recDate').value = new Date().toISOString().substring(0,10);
  document.getElementById('addRecordMsg').innerHTML = '';
  openModal('modalAddRecord');
}

async function submitAddRecord() {
  const bp = document.getElementById('recBP').value.split('/');
  const data = {
    patient_id: document.getElementById('recPatient').value,
    visit_date: document.getElementById('recDate').value,
    blood_pressure_systolic: bp[0]||null, blood_pressure_diastolic: bp[1]||null,
    heart_rate: document.getElementById('recHR').value||null,
    temperature: document.getElementById('recTemp').value||null,
    weight_kg: document.getElementById('recWeight').value||null,
    height_cm: document.getElementById('recHeight').value||null,
    symptoms: document.getElementById('recSymptoms').value,
    diagnosis: document.getElementById('recDiag').value,
    treatment: document.getElementById('recTreatment').value,
    follow_up_date: document.getElementById('recFollowup').value||null,
  };
  if (!data.diagnosis) { showMsg('addRecordMsg','error','Diagnosis is required.'); return; }
  const r = await fetch('/api/add_record',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  const d = await r.json();
  if (d.success) { closeModal('modalAddRecord'); renderRecords(); }
  else showMsg('addRecordMsg','error', d.error||'Failed to save record');
}

async function deleteRecord(id) {
  if (!confirm('Delete this medical record?')) return;
  await fetch('/api/delete_record',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id})});
  renderRecords();
}

async function openPrescription(recordId) {
  const meds = await fetch('/api/medicines_list').then(r=>r.json());
  document.getElementById('presRecordId').value = recordId;
  document.getElementById('presMed').innerHTML = meds.map(m=>`<option value="${m.medicine_id}">${m.medicine_name} (${m.strength||m.dosage_form||''})</option>`).join('');
  document.getElementById('prescriptionMsg').innerHTML = '';
  openModal('modalPrescription');
}

async function submitPrescription() {
  const data = {
    record_id: document.getElementById('presRecordId').value,
    medicine_id: document.getElementById('presMed').value,
    dosage: document.getElementById('presDosage').value,
    frequency: document.getElementById('presFreq').value,
    duration_days: document.getElementById('presDur').value,
    quantity_prescribed: document.getElementById('presQty').value,
    instructions: document.getElementById('presInstr').value,
  };
  const r = await fetch('/api/add_prescription',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  const d = await r.json();
  if (d.success) { closeModal('modalPrescription'); showToast('Prescription issued successfully'); }
  else showMsg('prescriptionMsg','error', d.error||'Failed to issue prescription');
}

// ══════════════════════════════════════════════
//  PRESCRIPTIONS
// ══════════════════════════════════════════════
async function renderPrescriptions() {
  const rows = await fetch('/api/prescriptions').then(r=>r.json());
  document.getElementById('mainContent').innerHTML = `<div class="page">
    <div class="tcard">
      <div class="tcard-header">
        <div class="tcard-title"><i class="fas fa-prescription-bottle-alt"></i> Prescriptions (${rows.length})</div>
        <div class="search-bar"><div class="search-wrap"><i class="fas fa-search"></i><input class="search-input" placeholder="Search..." oninput="filterTable('presTable',this.value)"></div></div>
      </div>
      <table id="presTable">
        <thead><tr><th>#</th><th>Patient</th><th>Medicine</th><th>Dosage</th><th>Frequency</th><th>Duration</th><th>Date</th><th>Dispensed</th></tr></thead>
        <tbody>
        ${rows.map(r=>`<tr>
          <td><span style="font-family:'JetBrains Mono',monospace;color:var(--primary2)">${r.prescription_id}</span></td>
          <td>${r.patient_name||'—'}</td>
          <td><strong style="color:var(--text)">${r.medicine_name||'—'}</strong></td>
          <td>${r.dosage||'—'}</td>
          <td>${r.frequency||'—'}</td>
          <td>${r.duration_days||'—'} days</td>
          <td>${r.prescribed_date||'—'}</td>
          <td>${r.is_dispensed?'<span class="badge b-green"><i class="fas fa-check"></i> Yes</span>':'<span class="badge b-amber">Pending</span>'}</td>
        </tr>`).join('')}
        </tbody>
      </table>
    </div></div>`;
}

// ══════════════════════════════════════════════
//  LAB TESTS
// ══════════════════════════════════════════════
async function renderLabTests() {
  const rows = await fetch('/api/lab_tests').then(r=>r.json());
  const canAdd = ['admin','doctor'].includes(currentUser.role);
  document.getElementById('mainContent').innerHTML = `<div class="page">
    <div class="tcard">
      <div class="tcard-header">
        <div class="tcard-title"><i class="fas fa-flask"></i> Lab Tests (${rows.length})</div>
        <div class="search-bar">
          <div class="search-wrap"><i class="fas fa-search"></i><input class="search-input" placeholder="Search..." oninput="filterTable('labTable',this.value)"></div>
          ${canAdd?`<button class="btn btn-teal btn-sm" onclick="openLabOrder()"><i class="fas fa-plus"></i> Order Test</button>`:''}
        </div>
      </div>
      <table id="labTable">
        <thead><tr><th>#</th><th>Patient</th><th>Test</th><th>Category</th><th>Ordered</th><th>Status</th><th>Result</th></tr></thead>
        <tbody>
        ${rows.map(r=>`<tr>
          <td><span style="font-family:'JetBrains Mono',monospace;color:var(--primary2)">${r.test_order_id}</span></td>
          <td>${r.patient_name||'—'}</td>
          <td><strong style="color:var(--text)">${r.test_name||'—'}</strong></td>
          <td><span class="badge b-purple">${r.test_category||'—'}</span></td>
          <td>${(r.order_date||'').substring(0,10)}</td>
          <td>${statusBadge(r.status)}</td>
          <td>${r.is_abnormal?'<span class="badge b-red"><i class="fas fa-exclamation-triangle"></i> Abnormal</span>':r.result_value?'<span class="badge b-green">Normal</span>':'<span class="badge b-amber">Pending</span>'}</td>
        </tr>`).join('')}
        </tbody>
      </table>
    </div></div>`;
}

async function openLabOrder() {
  const [patients, tests] = await Promise.all([
    fetch('/api/patients_list').then(r=>r.json()),
    fetch('/api/lab_catalog').then(r=>r.json()),
  ]);
  document.getElementById('labPatient').innerHTML = patients.map(p=>`<option value="${p.person_id}">${p.first_name} ${p.last_name}</option>`).join('');
  document.getElementById('labTest').innerHTML = tests.map(t=>`<option value="${t.test_id}">${t.test_name} ($${t.cost})</option>`).join('');
  document.getElementById('labDate').value = new Date().toISOString().substring(0,10);
  document.getElementById('labOrderMsg').innerHTML = '';
  openModal('modalLabOrder');
}

async function submitLabOrder() {
  const data = {
    patient_id: document.getElementById('labPatient').value,
    test_id: document.getElementById('labTest').value,
    scheduled_date: document.getElementById('labDate').value,
    notes: document.getElementById('labNotes').value,
  };
  const r = await fetch('/api/add_lab_order',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  const d = await r.json();
  if (d.success) { closeModal('modalLabOrder'); renderLabTests(); }
  else showMsg('labOrderMsg','error', d.error||'Failed to order test');
}

// ══════════════════════════════════════════════
//  ADMISSIONS
// ══════════════════════════════════════════════
async function renderAdmissions() {
  if (!['admin','nurse','receptionist'].includes(currentUser.role)) { accessDenied(['admin','nurse','receptionist']); return; }
  const rows = await fetch('/api/admissions').then(r=>r.json());
  document.getElementById('mainContent').innerHTML = `<div class="page">
    <div class="tcard">
      <div class="tcard-header">
        <div class="tcard-title"><i class="fas fa-procedures"></i> Admissions (${rows.length})</div>
        <div class="search-wrap"><i class="fas fa-search"></i><input class="search-input" placeholder="Search..." oninput="filterTable('admsTable',this.value)"></div>
      </div>
      <table id="admsTable">
        <thead><tr><th>#</th><th>Patient</th><th>Room</th><th>Ward</th><th>Admitted</th><th>Expected Discharge</th><th>Doctor</th><th>Status</th></tr></thead>
        <tbody>
        ${rows.map(r=>`<tr>
          <td><span style="font-family:'JetBrains Mono',monospace;color:var(--primary2)">${r.admission_id}</span></td>
          <td><strong style="color:var(--text)">${r.patient_name||'—'}</strong></td>
          <td>${r.room_number||'—'}</td>
          <td>${r.ward_name||'—'}</td>
          <td>${(r.admission_datetime||'').substring(0,10)}</td>
          <td>${(r.expected_discharge_datetime||'').substring(0,10)||'—'}</td>
          <td>${r.doctor_name||'—'}</td>
          <td>${r.status==='Admitted'?'<span class="badge b-blue">Admitted</span>':'<span class="badge b-green">Discharged</span>'}</td>
        </tr>`).join('')}
        </tbody>
      </table>
    </div></div>`;
}

// ══════════════════════════════════════════════
//  WARDS
// ══════════════════════════════════════════════
async function renderWards() {
  if (!['admin','nurse'].includes(currentUser.role)) { accessDenied(['admin','nurse']); return; }
  const [wards, rooms] = await Promise.all([
    fetch('/api/wards').then(r=>r.json()),
    fetch('/api/rooms').then(r=>r.json()),
  ]);
  document.getElementById('mainContent').innerHTML = `<div class="page">
    <div class="summary-2col">
      <div class="tcard">
        <div class="tcard-header"><div class="tcard-title"><i class="fas fa-hospital"></i> Wards (${wards.length})</div></div>
        <table>
          <thead><tr><th>Ward Name</th><th>Type</th><th>Total Beds</th><th>Available</th></tr></thead>
          <tbody>
          ${wards.map(w=>`<tr>
            <td><strong style="color:var(--text)">${w.ward_name}</strong></td>
            <td><span class="badge b-teal">${w.ward_type||'General'}</span></td>
            <td>${w.total_beds||0}</td>
            <td><span class="${(w.available_beds||0)>0?'badge b-green':'badge b-red'}">${w.available_beds||0}</span></td>
          </tr>`).join('')}
          </tbody>
        </table>
      </div>
      <div class="tcard">
        <div class="tcard-header"><div class="tcard-title"><i class="fas fa-bed"></i> Rooms (${rooms.length})</div></div>
        <table>
          <thead><tr><th>Room No.</th><th>Type</th><th>Beds</th><th>Ward</th><th>Available</th></tr></thead>
          <tbody>
          ${rooms.slice(0,50).map(r=>`<tr>
            <td><strong style="color:var(--text)">${r.room_number}</strong></td>
            <td>${r.room_type||'—'}</td>
            <td>${r.bed_capacity||0}</td>
            <td>${r.ward_name||'—'}</td>
            <td>${r.is_available?'<span class="badge b-green">Yes</span>':'<span class="badge b-red">No</span>'}</td>
          </tr>`).join('')}
          </tbody>
        </table>
      </div>
    </div></div>`;
}

// ══════════════════════════════════════════════
//  DEPARTMENTS
// ══════════════════════════════════════════════
async function renderDepartments() {
  const rows = await fetch('/api/departments').then(r=>r.json());
  document.getElementById('mainContent').innerHTML = `<div class="page">
    <div class="tcard">
      <div class="tcard-header"><div class="tcard-title"><i class="fas fa-building"></i> Departments (${rows.length})</div></div>
      <table>
        <thead><tr><th>#</th><th>Department</th><th>Floor</th><th>Extension</th><th>Doctors</th><th>Rooms</th><th>Appointments</th></tr></thead>
        <tbody>
        ${rows.map(r=>`<tr>
          <td><span style="font-family:'JetBrains Mono',monospace;color:var(--primary2)">${r.dept_id}</span></td>
          <td><strong style="color:var(--text)">${r.dept_name}</strong></td>
          <td>Floor ${r.floor_number||'—'}</td>
          <td><span style="font-family:'JetBrains Mono',monospace">${r.phone_extension||'—'}</span></td>
          <td><span class="badge b-blue">${r.doctor_count||0} doctors</span></td>
          <td>${r.room_count||0}</td>
          <td>${r.appt_count||0}</td>
        </tr>`).join('')}
        </tbody>
      </table>
    </div></div>`;
}

// ══════════════════════════════════════════════
//  INVOICES
// ══════════════════════════════════════════════
async function renderInvoices() {
  if (!['admin','receptionist'].includes(currentUser.role)) { accessDenied(['admin','receptionist']); return; }
  const rows = await fetch('/api/invoices').then(r=>r.json());
  document.getElementById('mainContent').innerHTML = `<div class="page">
    <div class="tcard">
      <div class="tcard-header">
        <div class="tcard-title"><i class="fas fa-file-invoice-dollar"></i> Invoices (${rows.length})</div>
        <div class="search-wrap"><i class="fas fa-search"></i><input class="search-input" placeholder="Search..." oninput="filterTable('invTable',this.value)"></div>
      </div>
      <table id="invTable">
        <thead><tr><th>#</th><th>Patient</th><th>Date</th><th>Subtotal</th><th>Tax</th><th>Total</th><th>Paid</th><th>Status</th></tr></thead>
        <tbody>
        ${rows.map(r=>`<tr>
          <td><span style="font-family:'JetBrains Mono',monospace;color:var(--primary2)">${r.invoice_id}</span></td>
          <td>${r.patient_name||'—'}</td>
          <td>${r.invoice_date||'—'}</td>
          <td>$${(r.subtotal||0).toFixed(2)}</td>
          <td>$${(r.tax||0).toFixed(2)}</td>
          <td><strong style="color:var(--text)">$${(r.total_amount||0).toFixed(2)}</strong></td>
          <td style="color:var(--emerald)">$${(r.amount_paid||0).toFixed(2)}</td>
          <td>${invoiceBadge(r.payment_status)}</td>
        </tr>`).join('')}
        </tbody>
      </table>
    </div></div>`;
}

function invoiceBadge(s) {
  if (s==='Paid') return '<span class="badge b-green"><i class="fas fa-check-circle"></i> Paid</span>';
  if (s==='Partial') return '<span class="badge b-amber"><i class="fas fa-adjust"></i> Partial</span>';
  return '<span class="badge b-red"><i class="fas fa-clock"></i> Pending</span>';
}

// ══════════════════════════════════════════════
//  MEDICINES
// ══════════════════════════════════════════════
async function renderMedicines() {
  const rows = await fetch('/api/medicines').then(r=>r.json());
  document.getElementById('mainContent').innerHTML = `<div class="page">
    <div class="tcard">
      <div class="tcard-header">
        <div class="tcard-title"><i class="fas fa-pills"></i> Medicine Inventory (${rows.length})</div>
        <div class="search-wrap"><i class="fas fa-search"></i><input class="search-input" placeholder="Search..." oninput="filterTable('medTable',this.value)"></div>
      </div>
      <table id="medTable">
        <thead><tr><th>#</th><th>Medicine</th><th>Generic Name</th><th>Category</th><th>Form</th><th>Strength</th><th>Price</th><th>Stock</th><th>Rx Req</th></tr></thead>
        <tbody>
        ${rows.map(r=>`<tr>
          <td><span style="font-family:'JetBrains Mono',monospace;color:var(--primary2)">${r.medicine_id}</span></td>
          <td><strong style="color:var(--text)">${r.medicine_name}</strong></td>
          <td>${r.generic_name||'—'}</td>
          <td><span class="badge b-purple">${r.category||'—'}</span></td>
          <td>${r.dosage_form||'—'}</td>
          <td>${r.strength||'—'}</td>
          <td>$${(r.unit_price||0).toFixed(2)}</td>
          <td><span class="${(r.quantity_in_stock||0)<=r.reorder_level?'badge b-red':'badge b-green'}">${r.quantity_in_stock||0}</span></td>
          <td>${r.requires_prescription?'<span class="badge b-amber">Rx</span>':'<span class="badge b-teal">OTC</span>'}</td>
        </tr>`).join('')}
        </tbody>
      </table>
    </div></div>`;
}

// ══════════════════════════════════════════════
//  ROLE ACCESS GUARD
// ══════════════════════════════════════════════
function accessDenied(requiredRoles) {
  const roleLabels = {admin:'Administrator',doctor:'Doctor',nurse:'Nurse',receptionist:'Receptionist',patient:'Patient'};
  document.getElementById('mainContent').innerHTML = `<div class="page">
    <div style="text-align:center;padding:80px 40px">
      <div style="width:80px;height:80px;background:linear-gradient(135deg,#FFFBEB,#FEF3C7);border-radius:24px;display:inline-flex;align-items:center;justify-content:center;margin-bottom:24px;border:2px solid #FCD34D">
        <i class="fas fa-lock" style="font-size:32px;color:var(--gold2)"></i>
      </div>
      <div style="font-family:'DM Serif Display',serif;font-size:26px;color:var(--text);margin-bottom:10px">Access Restricted</div>
      <div style="color:var(--text3);font-size:14px;max-width:380px;margin:0 auto 24px">
        This section is only accessible to: <strong>${requiredRoles.map(r=>roleLabels[r]||r).join(', ')}</strong>.
      </div>
      <div style="font-size:13px;color:var(--text4)">You are logged in as <strong style="color:var(--gold2)">${roleLabels[currentUser.role]||currentUser.role}</strong></div>
    </div></div>`;
}

// ══════════════════════════════════════════════
//  SQL RUNNER
// ══════════════════════════════════════════════
function renderSQL() {
  if (currentUser.role !== 'admin') {
    document.getElementById('mainContent').innerHTML = '<div class="alert alert-error"><i class="fas fa-ban"></i> Admin access only.</div>';
    return;
  }
  const examples = [
    "SELECT d.dept_name, COUNT(doc.person_id) AS doctors FROM department d LEFT JOIN doctor doc ON d.dept_id=doc.dept_id GROUP BY d.dept_id ORDER BY doctors DESC;",
    "SELECT p.first_name||' '||p.last_name AS patient, COUNT(a.appt_id) AS total_appts FROM patient pt JOIN person p ON pt.person_id=p.person_id LEFT JOIN appointment a ON pt.person_id=a.patient_id GROUP BY pt.person_id ORDER BY total_appts DESC LIMIT 10;",
    "SELECT m.medicine_name, m.quantity_in_stock, m.reorder_level FROM medicine m WHERE m.quantity_in_stock <= m.reorder_level ORDER BY m.quantity_in_stock;",
    "SELECT p.first_name||' '||p.last_name AS patient, i.total_amount, i.amount_paid, i.payment_status FROM invoice i JOIN patient pt ON i.patient_id=pt.person_id JOIN person p ON pt.person_id=p.person_id WHERE i.payment_status='Pending' ORDER BY i.total_amount DESC LIMIT 10;",
    "SELECT w.ward_name, w.total_beds, w.available_beds, w.total_beds-w.available_beds AS occupied FROM ward WHERE parent_ward_id IS NOT NULL ORDER BY occupied DESC;",
  ];
  document.getElementById('mainContent').innerHTML = `<div class="page">
    <div class="tcard" style="padding:24px">
      <div class="tcard-title" style="margin-bottom:18px"><i class="fas fa-database"></i> SQL Query Runner <span class="badge b-red" style="margin-left:8px">Admin Only</span></div>
      <div class="alert alert-info" style="margin-bottom:16px"><i class="fas fa-info-circle"></i> Full CRUD access. Be careful with UPDATE, INSERT, DELETE, DROP statements.</div>
      <textarea class="sql-editor" id="sqlQuery" rows="6" placeholder="-- Enter your SQL query here...
SELECT * FROM patient LIMIT 10;"></textarea>
      <div style="display:flex;gap:12px;margin-top:14px;flex-wrap:wrap">
        <button class="btn btn-teal" onclick="runSQL()"><i class="fas fa-play"></i> Execute Query</button>
        <button class="btn btn-ghost" onclick="document.getElementById('sqlQuery').value=''"><i class="fas fa-eraser"></i> Clear</button>
        <button class="btn btn-ghost" onclick="document.getElementById('sqlQuery').value='SELECT name FROM sqlite_master WHERE type=\\'table\\' ORDER BY name;'"><i class="fas fa-table"></i> List Tables</button>
      </div>
      <div id="sqlResult" class="sql-result"></div>
    </div>
    <div class="tcard" style="padding:24px">
      <div class="tcard-title" style="margin-bottom:14px"><i class="fas fa-lightbulb"></i> Example Queries</div>
      ${examples.map((q,i)=>`<div style="margin-bottom:10px">
        <button class="btn btn-ghost btn-sm" style="width:100%;text-align:left;font-family:'JetBrains Mono',monospace;font-size:11px;padding:10px 14px;justify-content:flex-start;overflow:hidden;text-overflow:ellipsis;white-space:nowrap"
          onclick="document.getElementById('sqlQuery').value=${JSON.stringify(q)}">${q}</button>
      </div>`).join('')}
    </div>
  </div>`;
}

async function runSQL() {
  const q = document.getElementById('sqlQuery').value.trim();
  if (!q) return;
  const resultEl = document.getElementById('sqlResult');
  resultEl.style.display = 'block';
  resultEl.textContent = '⟳ Executing...';
  try {
    const r = await fetch('/api/sql',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query:q})});
    const d = await r.json();
    if (d.error) { resultEl.style.color='#be123c'; resultEl.textContent = '✗ Error: ' + d.error; return; }
    resultEl.style.color = '#bae6fd';
    if (d.type === 'SELECT') {
      if (!d.data || d.data.length === 0) { resultEl.textContent = '✓ Query returned 0 rows.'; return; }
      const cols = Object.keys(d.data[0]);
      const colWidths = cols.map(c => Math.max(c.length, ...d.data.slice(0,50).map(r => String(r[c]||'').length), 6));
      const sep = '+' + colWidths.map(w=>'-'.repeat(w+2)).join('+') + '+';
      const header = '|' + cols.map((c,i)=>' '+c.padEnd(colWidths[i])+' ').join('|') + '|';
      const dataRows = d.data.slice(0,200).map(row => '|' + cols.map((c,i)=>' '+String(row[c]===null?'NULL':row[c]||'').padEnd(colWidths[i])+' ').join('|') + '|');
      resultEl.textContent = [sep,header,sep,...dataRows,sep,`\n✓ ${d.data.length} row(s) returned${d.data.length>200?' (showing first 200)':''}`].join('\n');
    } else {
      resultEl.style.color = '#059669';
      resultEl.textContent = `✓ ${d.type} executed successfully.\n  Rows affected: ${d.rows_affected}\n  Last insert ID: ${d.last_id||'N/A'}`;
    }
  } catch(e) { resultEl.style.color='#be123c'; resultEl.textContent = '✗ Network error: ' + e.message; }
}

// ══════════════════════════════════════════════
//  UTILITIES
// ══════════════════════════════════════════════
function statusBadge(s) {
  const map = {
    'Scheduled':'b-blue','Completed':'b-green','Cancelled':'b-red',
    'No Show':'b-amber','Checked In':'b-teal',
    'Ordered':'b-blue','Processing':'b-amber','Ready':'b-green','Delivered':'b-teal',
    'Admitted':'b-blue','Discharged':'b-green',
  };
  const cls = map[s] || 'b-amber';
  return `<span class="badge ${cls}">${s||'—'}</span>`;
}

function filterTable(tableId, query) {
  const q = query.toLowerCase();
  const rows = document.querySelectorAll(`#${tableId} tbody tr`);
  rows.forEach(r => { r.style.display = r.textContent.toLowerCase().includes(q) ? '' : 'none'; });
}

function openModal(id) { document.getElementById(id).classList.add('open'); }
function closeModal(id) { document.getElementById(id).classList.remove('open'); }

document.querySelectorAll('.overlay').forEach(o => {
  o.addEventListener('click', e => { if (e.target === o) o.classList.remove('open'); });
});

function showMsg(elId, type, msg) {
  const el = document.getElementById(elId);
  el.innerHTML = `<div class="alert alert-${type==='error'?'error':'success'}"><i class="fas fa-${type==='error'?'exclamation-circle':'check-circle'}"></i>${msg}</div>`;
}

function showToast(msg, type='success') {
  const t = document.createElement('div');
  t.className = `alert alert-${type==='error'?'error':'success'}`;
  t.style.cssText = 'position:fixed;bottom:24px;right:24px;z-index:9999;min-width:280px;box-shadow:0 8px 32px rgba(0,0,0,.15);animation:fadeUp .3s ease';
  t.innerHTML = `<i class="fas fa-${type==='error'?'exclamation-circle':'check-circle'}"></i>${msg}`;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 3000);
}

// ══════════════════════════════════════════════
//  PATIENT-SPECIFIC PAGES
// ══════════════════════════════════════════════
function selectRole(role, el) {
  // Update hidden select
  document.getElementById('loginRole').value = role;
  // Update pill styles
  document.querySelectorAll('.role-pill').forEach(p => p.classList.remove('active'));
  el.classList.add('active');
  // Update field labels/placeholders
  updateLoginHint(role);
}

function doLoginWithRipple(e) {
  // Create ripple
  const btn = document.getElementById('loginBtn');
  const ripple = document.createElement('span');
  ripple.className = 'ripple';
  const rect = btn.getBoundingClientRect();
  const size = Math.max(rect.width, rect.height) * 2;
  ripple.style.cssText = `width:${size}px;height:${size}px;left:${e.clientX-rect.left-size/2}px;top:${e.clientY-rect.top-size/2}px`;
  btn.appendChild(ripple);
  setTimeout(() => ripple.remove(), 600);
  doLogin();
}

function updateLoginHint(role) {
  const passIn = document.getElementById('loginPass');
  const userIn = document.getElementById('loginUser');
  const userLbl = document.getElementById('userLabel');
  const passLbl = document.getElementById('passLabel');
  if (role === 'patient') {
    passIn.placeholder = 'Date of Birth (YYYY-MM-DD)';
    userIn.placeholder = 'Your Patient ID number';
    userLbl && (userLbl.textContent = 'Patient ID');
    passLbl && (passLbl.textContent = 'Date of Birth');
  } else {
    passIn.placeholder = 'Enter password';
    userIn.placeholder = 'Enter username';
    userLbl && (userLbl.textContent = 'Username');
    passLbl && (passLbl.textContent = 'Password');
  }
}

async function renderMyAppointments() {
  const rows = await fetch('/api/my/appointments').then(r=>r.json());
  document.getElementById('mainContent').innerHTML = `<div class="page">
    <div class="tcard">
      <div class="tcard-header">
        <div class="tcard-title"><i class="fas fa-calendar-alt"></i> My Appointments (${rows.length})</div>
        <button class="btn btn-teal btn-sm" onclick="navigate('book_appointment')"><i class="fas fa-calendar-plus"></i> Book New</button>
      </div>
      <table>
        <thead><tr><th>Date & Time</th><th>Doctor</th><th>Type</th><th>Status</th><th>Reason</th></tr></thead>
        <tbody>
        ${rows.length===0?'<tr><td colspan="5" style="text-align:center;color:var(--text4);padding:40px"><i class="fas fa-calendar-times" style="font-size:32px;display:block;margin-bottom:12px;color:var(--border2)"></i>No appointments found. <a href="#" onclick="navigate(\'book_appointment\')" style="color:var(--primary2);font-weight:700">Book one now!</a></td></tr>':''}
        ${rows.map(r=>`<tr>
          <td><span style="font-family:'JetBrains Mono',monospace;color:var(--primary2);font-weight:600">${(r.appt_datetime||'').replace('T',' ').substring(0,16)}</span></td>
          <td><strong style="color:var(--text)">Dr. ${r.doctor_name||'—'}</strong><br><span style="font-size:11px;color:var(--text3)">${r.specialization||''}</span></td>
          <td><span class="badge b-blue">${r.appt_type||'—'}</span></td>
          <td>${statusBadge(r.status)}</td>
          <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--text3)">${r.reason||'—'}</td>
        </tr>`).join('')}
        </tbody>
      </table>
    </div></div>`;
}

// ══════════════════════════════════════════════
//  BOOK APPOINTMENT (PATIENT PORTAL)
// ══════════════════════════════════════════════
let bookState = { step: 1, selectedDoctor: null, selectedDate: null, selectedTime: null };

async function renderBookAppointment() {
  const doctors = await fetch('/api/doctors_list').then(r=>r.json());
  bookState = { step: 1, selectedDoctor: null, selectedDate: null, selectedTime: null };

  document.getElementById('mainContent').innerHTML = `<div class="page">
    <div class="tcard" style="overflow:visible">
      <div class="tcard-header" style="background:linear-gradient(135deg,#f0f9ff,#e0f2fe)">
        <div class="tcard-title"><i class="fas fa-calendar-plus"></i> Book an Appointment</div>
        <span style="font-size:13px;color:var(--text3)">Step <span id="bookStepNum">1</span> of 3</span>
      </div>
      <div style="padding:24px">
        <div class="book-steps" id="bookSteps">
          <div class="book-step active" id="bstep1"><i class="fas fa-user-md"></i>Choose Doctor</div>
          <div class="book-step" id="bstep2"><i class="fas fa-calendar"></i>Pick Date & Time</div>
          <div class="book-step" id="bstep3"><i class="fas fa-check-circle"></i>Confirm</div>
        </div>
        <div id="bookContent"></div>
      </div>
    </div>
  </div>`;

  renderBookStep1(doctors);
}

function renderBookStep1(doctors) {
  document.getElementById('bookStepNum').textContent = '1';
  document.getElementById('bookContent').innerHTML = `
    <div style="margin-bottom:16px">
      <div class="search-wrap" style="margin-bottom:16px">
        <i class="fas fa-search"></i>
        <input class="search-input" style="width:100%;max-width:400px" placeholder="Search by name or specialization..." oninput="filterDoctorCards(this.value)">
      </div>
    </div>
    <div id="doctorList">
      ${doctors.map(d=>`
      <div class="doctor-card" id="dcard_${d.person_id}" onclick="selectDoctor(${d.person_id}, '${(d.first_name+' '+d.last_name).replace(/'/g,"\\'")}', '${(d.specialization||'').replace(/'/g,"\\'")}', ${d.consultation_fee||0}, '${(d.dept_name||'').replace(/'/g,"\\'")}')">
        <div class="doctor-card-avatar"><i class="fas fa-user-md"></i></div>
        <div style="flex:1">
          <div class="doctor-card-name">Dr. ${d.first_name} ${d.last_name}</div>
          <div class="doctor-card-spec"><i class="fas fa-stethoscope" style="font-size:10px;margin-right:4px"></i>${d.specialization||'General Practice'}</div>
          <div class="doctor-card-fee"><i class="fas fa-building" style="font-size:10px;margin-right:4px"></i>${d.dept_name||'—'} &nbsp;·&nbsp; Consultation fee: <strong>$${(d.consultation_fee||0).toFixed(2)}</strong></div>
        </div>
        <i class="fas fa-chevron-right" style="color:var(--text4)"></i>
      </div>`).join('')}
    </div>`;
}

function filterDoctorCards(q) {
  document.querySelectorAll('.doctor-card').forEach(card => {
    card.style.display = card.textContent.toLowerCase().includes(q.toLowerCase()) ? '' : 'none';
  });
}

function selectDoctor(id, name, spec, fee, dept) {
  document.querySelectorAll('.doctor-card').forEach(c => c.classList.remove('selected'));
  document.getElementById('dcard_'+id).classList.add('selected');
  bookState.selectedDoctor = {id, name, spec, fee, dept};
  document.getElementById('bstep1').classList.remove('active'); document.getElementById('bstep1').classList.add('done');
  document.getElementById('bstep2').classList.add('active');
  document.getElementById('bookStepNum').textContent = '2';
  renderBookStep2();
}

function renderBookStep2() {
  const today = new Date(); today.setDate(today.getDate()+1);
  const minDate = today.toISOString().split('T')[0];
  const slots = ['08:00','08:30','09:00','09:30','10:00','10:30','11:00','11:30','14:00','14:30','15:00','15:30','16:00','16:30'];
  document.getElementById('bookContent').innerHTML = `
    <div style="background:var(--primary-light);border:1.5px solid var(--border2);border-radius:14px;padding:16px;display:flex;align-items:center;gap:14px;margin-bottom:20px">
      <div style="width:46px;height:46px;border-radius:50%;background:linear-gradient(135deg,var(--primary),var(--teal));display:grid;place-items:center;font-size:20px;color:#fff;flex-shrink:0"><i class="fas fa-user-md"></i></div>
      <div>
        <div style="font-weight:800;font-size:15px">Dr. ${bookState.selectedDoctor.name}</div>
        <div style="font-size:12px;color:var(--primary2)">${bookState.selectedDoctor.spec} · ${bookState.selectedDoctor.dept}</div>
      </div>
      <button class="btn btn-ghost btn-sm" onclick="renderBookStep1AllDoctors()" style="margin-left:auto"><i class="fas fa-undo"></i> Change</button>
    </div>
    <div class="form-row" style="margin-bottom:20px">
      <div class="field-g">
        <label><i class="fas fa-calendar" style="margin-right:6px;color:var(--primary)"></i>Appointment Date</label>
        <input class="form-ctrl" type="date" id="bookDate" min="${minDate}" value="${minDate}" onchange="updateTimeSlots()">
      </div>
      <div class="field-g">
        <label><i class="fas fa-tag" style="margin-right:6px;color:var(--primary)"></i>Appointment Type</label>
        <select class="form-ctrl" id="bookType">
          <option>Consultation</option><option>Follow-up</option><option>Check-up</option><option>Procedure</option><option>Emergency</option>
        </select>
      </div>
    </div>
    <div class="field-g" style="margin-bottom:20px">
      <label><i class="fas fa-clock" style="margin-right:6px;color:var(--primary)"></i>Select Time Slot</label>
      <div id="timeSlots" style="display:flex;flex-wrap:wrap;gap:4px;margin-top:8px">
        ${slots.map(s=>`<div class="time-slot" onclick="selectTime('${s}',this)">${s}</div>`).join('')}
      </div>
    </div>
    <div class="field-g">
      <label><i class="fas fa-comment-medical" style="margin-right:6px;color:var(--primary)"></i>Reason for Visit</label>
      <textarea class="form-ctrl" id="bookReason" rows="3" placeholder="Briefly describe your symptoms or reason for this appointment..."></textarea>
    </div>
    <div style="display:flex;gap:10px;margin-top:4px">
      <button class="btn btn-ghost" onclick="goBackBookStep1()"><i class="fas fa-arrow-left"></i> Back</button>
      <button class="btn btn-teal" onclick="proceedToConfirm()"><i class="fas fa-arrow-right"></i> Continue to Confirm</button>
    </div>`;
}

async function renderBookStep1AllDoctors() {
  const doctors = await fetch('/api/doctors_list').then(r=>r.json());
  document.getElementById('bstep1').classList.remove('done'); document.getElementById('bstep1').classList.add('active');
  document.getElementById('bstep2').classList.remove('active');
  document.getElementById('bookStepNum').textContent = '1';
  renderBookStep1(doctors);
}

async function goBackBookStep1() {
  await renderBookStep1AllDoctors();
}

function selectTime(t, el) {
  document.querySelectorAll('.time-slot').forEach(s => s.classList.remove('selected'));
  el.classList.add('selected');
  bookState.selectedTime = t;
}

function proceedToConfirm() {
  const date = document.getElementById('bookDate').value;
  const type = document.getElementById('bookType').value;
  const reason = document.getElementById('bookReason').value;
  if (!bookState.selectedTime) { showToast('Please select a time slot', 'error'); return; }
  if (!date) { showToast('Please select a date', 'error'); return; }
  bookState.selectedDate = date;
  bookState.apptType = type;
  bookState.reason = reason;
  document.getElementById('bstep2').classList.remove('active'); document.getElementById('bstep2').classList.add('done');
  document.getElementById('bstep3').classList.add('active');
  document.getElementById('bookStepNum').textContent = '3';
  renderBookStep3();
}

function renderBookStep3() {
  const d = bookState;
  document.getElementById('bookContent').innerHTML = `
    <div style="background:linear-gradient(135deg,#f0fdf4,#dcfce7);border:1.5px solid #a7f3d0;border-radius:18px;padding:28px;margin-bottom:20px;text-align:center">
      <div style="font-size:48px;margin-bottom:12px"><i class="fas fa-calendar-check" style="color:#059669"></i></div>
      <div style="font-family:'DM Serif Display',serif;font-size:22px;color:var(--text);margin-bottom:6px">Review Your Appointment</div>
      <div style="font-size:13px;color:var(--text3)">Please confirm the details below before booking</div>
    </div>
    <div class="info-grid" style="margin-bottom:24px">
      <div class="info-card"><div class="info-label"><i class="fas fa-user-md" style="color:var(--primary);margin-right:5px"></i>Doctor</div><div class="info-val">Dr. ${d.selectedDoctor.name}</div></div>
      <div class="info-card"><div class="info-label"><i class="fas fa-stethoscope" style="color:var(--primary);margin-right:5px"></i>Specialization</div><div class="info-val">${d.selectedDoctor.spec}</div></div>
      <div class="info-card"><div class="info-label"><i class="fas fa-calendar" style="color:var(--primary);margin-right:5px"></i>Date</div><div class="info-val">${d.selectedDate}</div></div>
      <div class="info-card"><div class="info-label"><i class="fas fa-clock" style="color:var(--primary);margin-right:5px"></i>Time</div><div class="info-val">${d.selectedTime}</div></div>
      <div class="info-card"><div class="info-label"><i class="fas fa-tag" style="color:var(--primary);margin-right:5px"></i>Type</div><div class="info-val">${d.apptType}</div></div>
      <div class="info-card"><div class="info-label"><i class="fas fa-dollar-sign" style="color:var(--primary);margin-right:5px"></i>Consultation Fee</div><div class="info-val" style="color:var(--emerald)">$${d.selectedDoctor.fee.toFixed(2)}</div></div>
    </div>
    ${d.reason?`<div class="info-card" style="margin-bottom:20px"><div class="info-label"><i class="fas fa-comment-medical" style="color:var(--primary);margin-right:5px"></i>Reason</div><div class="info-val" style="font-size:13px;font-weight:400">${d.reason}</div></div>`:''}
    <div id="bookConfirmMsg"></div>
    <div style="display:flex;gap:10px">
      <button class="btn btn-ghost" onclick="goBackStep2()"><i class="fas fa-arrow-left"></i> Back</button>
      <button class="btn btn-teal" style="flex:1;justify-content:center;padding:14px" onclick="submitBooking()">
        <i class="fas fa-calendar-check"></i> Confirm Booking
      </button>
    </div>`;
}

function goBackStep2() {
  document.getElementById('bstep3').classList.remove('active');
  document.getElementById('bstep2').classList.remove('done');
  document.getElementById('bstep2').classList.add('active');
  document.getElementById('bookStepNum').textContent = '2';
  renderBookStep2();
}

async function submitBooking() {
  const d = bookState;
  const data = {
    patient_id: currentUser.user_id,
    doctor_id: d.selectedDoctor.id,
    appt_date: d.selectedDate,
    appt_time: d.selectedTime,
    appt_type: d.apptType,
    duration_minutes: 30,
    reason: d.reason,
  };
  try {
    const res = await fetch('/api/add_appointment',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
    const result = await res.json();
    if (result.success) {
      document.getElementById('bookConfirmMsg').innerHTML = `<div class="alert alert-success"><i class="fas fa-check-circle"></i> Appointment booked successfully! Redirecting to your appointments...</div>`;
      setTimeout(() => navigate('my_appointments'), 2000);
    } else {
      document.getElementById('bookConfirmMsg').innerHTML = `<div class="alert alert-error"><i class="fas fa-exclamation-circle"></i>${result.error||'Booking failed. Please try again.'}</div>`;
    }
  } catch(e) {
    document.getElementById('bookConfirmMsg').innerHTML = `<div class="alert alert-error"><i class="fas fa-exclamation-circle"></i>Network error. Please try again.</div>`;
  }
}

async function renderMyRecords() {
  const rows = await fetch('/api/my/records').then(r=>r.json());
  document.getElementById('mainContent').innerHTML = `<div class="page">
    ${rows.length===0?'<div class="alert alert-info"><i class="fas fa-info-circle"></i>No medical records found.</div>':''}
    ${rows.map(r=>`
    <div class="tcard" style="padding:24px;margin-bottom:16px">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:16px;flex-wrap:wrap;gap:12px">
        <div>
          <div style="font-family:'DM Serif Display',serif;font-size:18px;color:var(--text);margin-bottom:4px">${r.diagnosis||'Visit Record'}</div>
          <div style="font-size:12px;color:var(--text3)">${r.visit_date||'—'} &nbsp;·&nbsp; Dr. ${r.doctor_name||'—'}</div>
        </div>
        ${r.follow_up_date?`<span class="badge b-amber"><i class="fas fa-calendar"></i> Follow-up: ${r.follow_up_date}</span>`:''}
      </div>
      <div class="info-grid">
        ${r.symptoms?`<div class="info-card"><div class="info-label">Symptoms</div><div class="info-val" style="font-size:13px">${r.symptoms}</div></div>`:''}
        ${r.treatment?`<div class="info-card"><div class="info-label">Treatment</div><div class="info-val" style="font-size:13px">${r.treatment}</div></div>`:''}
        ${r.blood_pressure_systolic?`<div class="info-card"><div class="info-label">Blood Pressure</div><div class="info-val">${r.blood_pressure_systolic}/${r.blood_pressure_diastolic} mmHg</div></div>`:''}
        ${r.heart_rate?`<div class="info-card"><div class="info-label">Heart Rate</div><div class="info-val">${r.heart_rate} bpm</div></div>`:''}
        ${r.temperature?`<div class="info-card"><div class="info-label">Temperature</div><div class="info-val">${r.temperature} °C</div></div>`:''}
        ${r.weight_kg?`<div class="info-card"><div class="info-label">Weight / Height</div><div class="info-val">${r.weight_kg} kg / ${r.height_cm||'?'} cm</div></div>`:''}
      </div>
    </div>`).join('')}
  </div>`;
}

async function renderMyPrescriptions() {
  const rows = await fetch('/api/my/prescriptions').then(r=>r.json());
  document.getElementById('mainContent').innerHTML = `<div class="page">
    <div class="tcard">
      <div class="tcard-header"><div class="tcard-title"><i class="fas fa-prescription-bottle-alt"></i> My Prescriptions (${rows.length})</div></div>
      <table>
        <thead><tr><th>Medicine</th><th>Dosage</th><th>Frequency</th><th>Duration</th><th>Date</th><th>Status</th></tr></thead>
        <tbody>
        ${rows.length===0?'<tr><td colspan="6" style="text-align:center;color:var(--text3);padding:32px">No prescriptions found.</td></tr>':''}
        ${rows.map(r=>`<tr>
          <td><strong style="color:var(--text)">${r.medicine_name||'—'}</strong><br><span style="font-size:11px;color:var(--text3)">${r.generic_name||''}</span></td>
          <td>${r.dosage||'—'}</td>
          <td>${r.frequency||'—'}</td>
          <td>${r.duration_days||'—'} days</td>
          <td>${r.prescribed_date||'—'}</td>
          <td>${r.is_dispensed?'<span class="badge b-green"><i class="fas fa-check"></i> Dispensed</span>':'<span class="badge b-amber">Pending</span>'}</td>
        </tr>`).join('')}
        </tbody>
      </table>
    </div></div>`;
}

async function renderMyLabTests() {
  const rows = await fetch('/api/my/labtests').then(r=>r.json());
  document.getElementById('mainContent').innerHTML = `<div class="page">
    <div class="tcard">
      <div class="tcard-header"><div class="tcard-title"><i class="fas fa-flask"></i> My Lab Tests (${rows.length})</div></div>
      <table>
        <thead><tr><th>Test</th><th>Category</th><th>Ordered</th><th>Scheduled</th><th>Status</th><th>Result</th></tr></thead>
        <tbody>
        ${rows.length===0?'<tr><td colspan="6" style="text-align:center;color:var(--text3);padding:32px">No lab tests ordered.</td></tr>':''}
        ${rows.map(r=>`<tr>
          <td><strong style="color:var(--text)">${r.test_name||'—'}</strong></td>
          <td><span class="badge b-purple">${r.test_category||'—'}</span></td>
          <td>${(r.order_date||'').substring(0,10)}</td>
          <td>${r.scheduled_date||'—'}</td>
          <td>${statusBadge(r.status)}</td>
          <td>${r.result_value?`<span class="${r.is_abnormal?'badge b-red':'badge b-green'}">${r.result_value}</span>`:'<span class="badge b-amber">Pending</span>'}</td>
        </tr>`).join('')}
        </tbody>
      </table>
    </div></div>`;
}

async function renderMyInvoices() {
  const rows = await fetch('/api/my/invoices').then(r=>r.json());
  let totalOwed = rows.filter(r=>r.payment_status!=='Paid').reduce((s,r)=>s+(r.total_amount-r.amount_paid),0);
  document.getElementById('mainContent').innerHTML = `<div class="page">
    ${totalOwed>0?`<div class="alert alert-error" style="margin-bottom:20px"><i class="fas fa-exclamation-circle"></i>Outstanding balance: <strong>$${totalOwed.toFixed(2)}</strong></div>`:'<div class="alert alert-success" style="margin-bottom:20px"><i class="fas fa-check-circle"></i>All bills are paid. Thank you!</div>'}
    <div class="tcard">
      <div class="tcard-header"><div class="tcard-title"><i class="fas fa-file-invoice-dollar"></i> My Bills (${rows.length})</div></div>
      <table>
        <thead><tr><th>Invoice #</th><th>Date</th><th>Total</th><th>Paid</th><th>Balance</th><th>Status</th></tr></thead>
        <tbody>
        ${rows.length===0?'<tr><td colspan="6" style="text-align:center;color:var(--text3);padding:32px">No invoices found.</td></tr>':''}
        ${rows.map(r=>`<tr>
          <td><span style="font-family:'JetBrains Mono',monospace;color:var(--primary2)">#${r.invoice_id}</span></td>
          <td>${r.invoice_date||'—'}</td>
          <td><strong style="color:var(--text)">$${(r.total_amount||0).toFixed(2)}</strong></td>
          <td style="color:var(--emerald)">$${(r.amount_paid||0).toFixed(2)}</td>
          <td style="color:${(r.total_amount-r.amount_paid)>0?'#be123c':'#059669'}">$${((r.total_amount||0)-(r.amount_paid||0)).toFixed(2)}</td>
          <td>${invoiceBadge(r.payment_status)}</td>
        </tr>`).join('')}
        </tbody>
      </table>
    </div></div>`;
}

async function renderStatistics() {
  destroyCharts();
  document.getElementById('mainContent').innerHTML = '<div class="loading"><div class="spinner"></div>Loading analytics...</div>';
  let s;
  try {
    s = await fetch('/api/admin_stats').then(r=>r.json());
    if (s.error) throw new Error(s.error);
  } catch(e) {
    document.getElementById('mainContent').innerHTML = `<div class="alert alert-error"><i class="fas fa-exclamation-triangle"></i>Failed to load statistics: ${e.message}</div>`;
    return;
  }

  const BLUE='#2196F3',GOLD='#F59E0B',TEAL='#0d9488',GREEN='#059669',
        PURPLE='#7c3aed',ROSE='#e11d48',AMBER='#D97706',NAVY='#1565C0';

  // Compute KPIs from real data
  const totalAppts   = (s.appt_status||[]).reduce((a,r)=>a+r.c,0);
  const totalInvs    = (s.inv_status||[]).reduce((a,r)=>a+r.c,0);
  const occupiedBeds = (s.wards||[]).reduce((a,r)=>a+(r.occupied||0),0);
  const totalBeds    = (s.wards||[]).reduce((a,r)=>a+(r.total_beds||0),0);
  const occupancy    = totalBeds>0?Math.round(occupiedBeds/totalBeds*100):0;
  const lowStockCount= (s.low_stock||[]).length;
  const lab          = s.lab_results || {};

  document.getElementById('mainContent').innerHTML = `<div class="page">

    <!-- Header Banner -->
    <div style="background:linear-gradient(135deg,#1565C0 0%,#0D47A1 60%,#0a3570 100%);border-radius:20px;padding:28px 32px;margin-bottom:28px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:16px">
      <div>
        <div style="font-size:12px;color:rgba(255,255,255,.65);font-weight:700;text-transform:uppercase;letter-spacing:.12em;margin-bottom:6px"><i class="fas fa-chart-bar"></i> &nbsp;Admin Analytics</div>
        <div style="font-family:'DM Serif Display',serif;font-size:28px;color:#fff;margin-bottom:4px">Database Statistics</div>
        <div style="font-size:12px;color:rgba(255,255,255,.7)">Live overview of all hospital data &nbsp;·&nbsp; ${new Date().toLocaleDateString('en-GB',{weekday:'long',year:'numeric',month:'long',day:'numeric'})}</div>
      </div>
      <div style="display:flex;gap:10px;flex-wrap:wrap">
        <div style="background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.2);border-radius:12px;padding:12px 20px;text-align:center">
          <div style="font-size:22px;font-weight:800;color:#FCD34D">${totalAppts}</div>
          <div style="font-size:11px;color:rgba(255,255,255,.7);text-transform:uppercase;letter-spacing:.08em">Total Appts</div>
        </div>
        <div style="background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.2);border-radius:12px;padding:12px 20px;text-align:center">
          <div style="font-size:22px;font-weight:800;color:#86efac">${occupancy}%</div>
          <div style="font-size:11px;color:rgba(255,255,255,.7);text-transform:uppercase;letter-spacing:.08em">Bed Occupancy</div>
        </div>
        <div style="background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.2);border-radius:12px;padding:12px 20px;text-align:center">
          <div style="font-size:22px;font-weight:800;color:#fca5a5">${lowStockCount}</div>
          <div style="font-size:11px;color:rgba(255,255,255,.7);text-transform:uppercase;letter-spacing:.08em">Low Stock</div>
        </div>
      </div>
    </div>

    <!-- Row 1: Monthly trend + Appointment status -->
    <div class="chart-grid-2" style="margin-bottom:20px">
      <div class="tcard chart-card">
        <div class="tcard-header">
          <div class="tcard-title"><i class="fas fa-chart-line" style="color:${BLUE}"></i> Appointments — Last 6 Months</div>
        </div>
        <div class="chart-wrap"><canvas id="stChartMonthly"></canvas></div>
      </div>
      <div class="tcard chart-card">
        <div class="tcard-header">
          <div class="tcard-title"><i class="fas fa-chart-pie" style="color:${GOLD}"></i> Appointment Status Breakdown</div>
        </div>
        <div class="chart-wrap" style="display:flex;align-items:center;justify-content:center"><canvas id="stChartApptStatus"></canvas></div>
      </div>
    </div>

    <!-- Row 2: Gender + Invoice + Lab -->
    <div class="chart-grid-3" style="margin-bottom:20px">
      <div class="tcard chart-card">
        <div class="tcard-header">
          <div class="tcard-title"><i class="fas fa-venus-mars" style="color:${TEAL}"></i> Patient Gender Split</div>
        </div>
        <div class="chart-wrap" style="display:flex;align-items:center;justify-content:center"><canvas id="stChartGender"></canvas></div>
      </div>
      <div class="tcard chart-card">
        <div class="tcard-header">
          <div class="tcard-title"><i class="fas fa-file-invoice-dollar" style="color:${GREEN}"></i> Invoice Payment Status</div>
        </div>
        <div class="chart-wrap" style="display:flex;align-items:center;justify-content:center"><canvas id="stChartInvoice"></canvas></div>
      </div>
      <div class="tcard chart-card">
        <div class="tcard-header">
          <div class="tcard-title"><i class="fas fa-flask" style="color:${PURPLE}"></i> Lab Test Results</div>
        </div>
        <div class="chart-wrap" style="display:flex;align-items:center;justify-content:center"><canvas id="stChartLab"></canvas></div>
      </div>
    </div>

    <!-- Row 3: Departments bar + Ward occupancy -->
    <div class="chart-grid-2" style="margin-bottom:20px">
      <div class="tcard chart-card">
        <div class="tcard-header">
          <div class="tcard-title"><i class="fas fa-building" style="color:${NAVY}"></i> Doctors per Department</div>
        </div>
        <div class="chart-wrap"><canvas id="stChartDepts"></canvas></div>
      </div>
      <div class="tcard chart-card">
        <div class="tcard-header">
          <div class="tcard-title"><i class="fas fa-hospital" style="color:${TEAL}"></i> Ward Bed Occupancy</div>
        </div>
        <div class="chart-wrap"><canvas id="stChartWards"></canvas></div>
      </div>
    </div>

    <!-- Row 4: Admission status + Low stock -->
    <div class="chart-grid-2" style="margin-bottom:20px">
      <div class="tcard chart-card">
        <div class="tcard-header">
          <div class="tcard-title"><i class="fas fa-procedures" style="color:${ROSE}"></i> Admissions by Status</div>
        </div>
        <div class="chart-wrap" style="display:flex;align-items:center;justify-content:center"><canvas id="stChartAdm"></canvas></div>
      </div>
      <div class="tcard chart-card">
        <div class="tcard-header">
          <div class="tcard-title"><i class="fas fa-exclamation-triangle" style="color:${ROSE}"></i> Low Stock Medicines</div>
        </div>
        <div class="chart-wrap"><canvas id="stChartLowStock"></canvas></div>
      </div>
    </div>

    <!-- Summary table -->
    <div class="tcard" style="margin-bottom:20px">
      <div class="tcard-header">
        <div class="tcard-title"><i class="fas fa-table" style="color:${NAVY}"></i> Invoice Payment Summary</div>
      </div>
      <table>
        <thead><tr><th>Status</th><th>Count</th><th>% of Total</th><th>Bar</th></tr></thead>
        <tbody>
        ${(s.inv_status||[]).map(r=>{
          const pct = totalInvs>0?Math.round(r.c/totalInvs*100):0;
          const colors={'Paid':GREEN,'Pending':GOLD,'Overdue':ROSE,'Partially Paid':TEAL};
          const col=colors[r.payment_status]||BLUE;
          return `<tr>
            <td><span class="badge" style="background:${col}20;color:${col};border:1px solid ${col}40">${r.payment_status}</span></td>
            <td><strong>${r.c}</strong></td>
            <td>${pct}%</td>
            <td><div style="background:#f1f5f9;border-radius:20px;height:8px;min-width:120px"><div style="background:${col};height:8px;border-radius:20px;width:${pct}%"></div></div></td>
          </tr>`;
        }).join('')}
        </tbody>
      </table>
    </div>

  </div>`;

  // Chart defaults
  const cd = {
    responsive:true, maintainAspectRatio:true,
    plugins:{ legend:{ labels:{ font:{family:"'Plus Jakarta Sans',sans-serif",size:12}, color:'#334155' } } }
  };

  // 1. Monthly line chart
  _adminCharts.stMonthly = new Chart(document.getElementById('stChartMonthly'), {
    type:'line',
    data:{
      labels: (s.appt_monthly||[]).map(r=>r.month),
      datasets:[{
        label:'Appointments', data:(s.appt_monthly||[]).map(r=>r.c),
        borderColor:BLUE, backgroundColor:'rgba(33,150,243,.12)', borderWidth:3,
        fill:true, tension:0.45, pointBackgroundColor:GOLD, pointRadius:5, pointHoverRadius:8
      }]
    },
    options:{...cd, scales:{y:{beginAtZero:true,ticks:{color:'#64748b'},grid:{color:'rgba(0,0,0,.05)'}},x:{ticks:{color:'#64748b'},grid:{display:false}}}}
  });

  // 2. Appointment status doughnut
  const apptCols={'Scheduled':BLUE,'Completed':GREEN,'Cancelled':ROSE,'No-Show':AMBER,'Checked In':TEAL};
  _adminCharts.stApptStatus = new Chart(document.getElementById('stChartApptStatus'), {
    type:'doughnut',
    data:{
      labels:(s.appt_status||[]).map(r=>r.status),
      datasets:[{data:(s.appt_status||[]).map(r=>r.c), backgroundColor:(s.appt_status||[]).map(r=>apptCols[r.status]||NAVY), borderWidth:3,borderColor:'#fff',hoverOffset:8}]
    },
    options:{...cd, cutout:'65%', plugins:{...cd.plugins, legend:{position:'right',labels:{...cd.plugins.legend.labels}}}}
  });

  // 3. Gender pie
  const gColors={'Male':BLUE,'Female':ROSE,'Other':TEAL,'Unknown':AMBER};
  _adminCharts.stGender = new Chart(document.getElementById('stChartGender'), {
    type:'pie',
    data:{
      labels:(s.gender||[]).map(r=>r.gender||'Unknown'),
      datasets:[{data:(s.gender||[]).map(r=>r.c), backgroundColor:(s.gender||[]).map(r=>gColors[r.gender]||PURPLE), borderWidth:3,borderColor:'#fff',hoverOffset:6}]
    },
    options:{...cd, plugins:{...cd.plugins, legend:{position:'bottom',labels:{...cd.plugins.legend.labels}}}}
  });

  // 4. Invoice doughnut
  const invCols={'Paid':GREEN,'Pending':GOLD,'Overdue':ROSE,'Partially Paid':TEAL};
  _adminCharts.stInvoice = new Chart(document.getElementById('stChartInvoice'), {
    type:'doughnut',
    data:{
      labels:(s.inv_status||[]).map(r=>r.payment_status),
      datasets:[{data:(s.inv_status||[]).map(r=>r.c), backgroundColor:(s.inv_status||[]).map(r=>invCols[r.payment_status]||NAVY), borderWidth:3,borderColor:'#fff',hoverOffset:6}]
    },
    options:{...cd, cutout:'60%', plugins:{...cd.plugins, legend:{position:'bottom',labels:{...cd.plugins.legend.labels}}}}
  });

  // 5. Lab results doughnut
  _adminCharts.stLab = new Chart(document.getElementById('stChartLab'), {
    type:'doughnut',
    data:{
      labels:['Normal','Abnormal','Pending'],
      datasets:[{data:[lab.normal||0,lab.abnormal||0,lab.pending||0], backgroundColor:[GREEN,ROSE,AMBER], borderWidth:3,borderColor:'#fff',hoverOffset:6}]
    },
    options:{...cd, cutout:'60%', plugins:{...cd.plugins, legend:{position:'bottom',labels:{...cd.plugins.legend.labels}}}}
  });

  // 6. Departments horizontal bar
  _adminCharts.stDepts = new Chart(document.getElementById('stChartDepts'), {
    type:'bar',
    data:{
      labels:(s.departments||[]).map(r=>r.dept_name),
      datasets:[{label:'Doctors', data:(s.departments||[]).map(r=>r.c),
        backgroundColor:(s.departments||[]).map((_,i)=>[BLUE,GOLD,TEAL,GREEN,PURPLE,ROSE][i%6]),
        borderRadius:8, borderSkipped:false}]
    },
    options:{...cd, indexAxis:'y', scales:{x:{beginAtZero:true,ticks:{stepSize:1,color:'#64748b'},grid:{color:'rgba(0,0,0,.05)'}},y:{ticks:{color:'#334155'},grid:{display:false}}}}
  });

  // 7. Ward occupancy grouped bar
  _adminCharts.stWards = new Chart(document.getElementById('stChartWards'), {
    type:'bar',
    data:{
      labels:(s.wards||[]).map(r=>r.ward_name),
      datasets:[
        {label:'Total Beds', data:(s.wards||[]).map(r=>r.total_beds), backgroundColor:'rgba(33,150,243,.25)',borderColor:BLUE,borderWidth:2,borderRadius:6},
        {label:'Occupied',   data:(s.wards||[]).map(r=>r.occupied),   backgroundColor:'rgba(245,158,11,.7)',borderColor:GOLD,borderWidth:2,borderRadius:6},
      ]
    },
    options:{...cd, scales:{y:{beginAtZero:true,ticks:{color:'#64748b'},grid:{color:'rgba(0,0,0,.05)'}},x:{ticks:{color:'#334155',maxRotation:30},grid:{display:false}}}}
  });

  // 8. Admission status doughnut
  const admCols={'Admitted':BLUE,'Discharged':GREEN,'Transferred':TEAL,'Deceased':ROSE};
  _adminCharts.stAdm = new Chart(document.getElementById('stChartAdm'), {
    type:'doughnut',
    data:{
      labels:(s.adm_status||[]).map(r=>r.status),
      datasets:[{data:(s.adm_status||[]).map(r=>r.c), backgroundColor:(s.adm_status||[]).map(r=>admCols[r.status]||PURPLE), borderWidth:3,borderColor:'#fff',hoverOffset:6}]
    },
    options:{...cd, cutout:'62%', plugins:{...cd.plugins, legend:{position:'right',labels:{...cd.plugins.legend.labels}}}}
  });

  // 9. Low stock horizontal bar
  _adminCharts.stLowStock = new Chart(document.getElementById('stChartLowStock'), {
    type:'bar',
    data:{
      labels:(s.low_stock||[]).map(r=>r.medicine_name),
      datasets:[
        {label:'In Stock',      data:(s.low_stock||[]).map(r=>r.quantity_in_stock), backgroundColor:'rgba(225,29,72,.7)',borderColor:ROSE,borderWidth:2,borderRadius:6},
        {label:'Reorder Level', data:(s.low_stock||[]).map(r=>r.reorder_level),     backgroundColor:'rgba(245,158,11,.35)',borderColor:GOLD,borderWidth:2,borderRadius:6},
      ]
    },
    options:{...cd, indexAxis:'y', scales:{x:{beginAtZero:true,ticks:{color:'#64748b'},grid:{color:'rgba(0,0,0,.05)'}},y:{ticks:{color:'#334155',font:{size:11}},grid:{display:false}}}}
  });
}

async function renderMyProfile() {
  document.getElementById('mainContent').innerHTML = '<div class="loading"><div class="spinner"></div>Loading profile...</div>';
  let d;
  try {
    const res = await fetch('/api/my/profile');
    d = await res.json();
    if (d.error) throw new Error(d.error);
  } catch(e) {
    document.getElementById('mainContent').innerHTML = `<div class="alert alert-error"><i class="fas fa-exclamation-triangle"></i>Failed to load profile: ${e.message}</div>`;
    return;
  }

  const p = d.person || {};
  const role = currentUser.role;

  // Use currentUser.name as display fallback if DB record is empty
  const displayName = (p.first_name && p.last_name)
    ? `${p.first_name} ${p.last_name}`
    : currentUser.name || '—';

  let extraCards = '';
  let roleIcon = 'fa-id-card';
  let roleLabel = 'Profile';
  let roleBadgeColor = 'var(--primary2)';
  let roleBg = 'linear-gradient(135deg,#EFF6FF,#DBEAFE)';
  let professionalSection = '';

  if (role === 'patient') {
    const pt = d.patient || {};
    roleIcon = 'fa-procedures'; roleLabel = 'Patient'; roleBadgeColor = 'var(--teal)';
    roleBg = 'linear-gradient(135deg,#f0fdfa,#ccfbf1)';
    extraCards = `
      <div class="info-card"><div class="info-label">Blood Type</div><div class="info-val">${p.blood_type||'—'}</div></div>
      <div class="info-card"><div class="info-label">Marital Status</div><div class="info-val">${pt.marital_status||'—'}</div></div>
      <div class="info-card"><div class="info-label">Occupation</div><div class="info-val">${pt.occupation||'—'}</div></div>
      <div class="info-card"><div class="info-label">Insurance Provider</div><div class="info-val">${pt.insurance_provider||'—'}</div></div>
      <div class="info-card"><div class="info-label">Insurance Number</div><div class="info-val">${pt.insurance_number||'—'}</div></div>`;

  } else if (role === 'doctor') {
    const doc = d.doctor || {};
    roleIcon = 'fa-user-md'; roleLabel = 'Doctor'; roleBadgeColor = '#1565C0';
    roleBg = 'linear-gradient(135deg,#EFF6FF,#DBEAFE)';
    professionalSection = `
      <div style="margin-top:24px">
        <div style="font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:.1em;color:var(--text3);margin-bottom:12px">
          <i class="fas fa-stethoscope" style="color:var(--primary);margin-right:6px"></i>Professional Details
        </div>
        <div class="info-grid">
          <div class="info-card" style="--tile-bg:#EFF6FF">
            <div class="info-label">Specialization</div>
            <div class="info-val" style="color:var(--primary2);font-weight:700">${doc.specialization||'—'}</div>
          </div>
          <div class="info-card">
            <div class="info-label">License Number</div>
            <div class="info-val" style="font-family:'JetBrains Mono',monospace;font-size:13px">${doc.license_number||'—'}</div>
          </div>
          <div class="info-card">
            <div class="info-label">Qualification</div>
            <div class="info-val">${doc.qualification||'—'}</div>
          </div>
          <div class="info-card">
            <div class="info-label">Department</div>
            <div class="info-val">${doc.dept_name||'—'}</div>
          </div>
          <div class="info-card">
            <div class="info-label">Consultation Fee</div>
            <div class="info-val" style="color:#d97706;font-weight:800;font-size:18px">${doc.consultation_fee?'$'+Number(doc.consultation_fee).toFixed(2):'—'}</div>
          </div>
          <div class="info-card">
            <div class="info-label">Years of Experience</div>
            <div class="info-val" style="font-weight:700">${doc.years_of_experience?doc.years_of_experience+' yrs':'—'}</div>
          </div>
          <div class="info-card">
            <div class="info-label">Max Appointments / Day</div>
            <div class="info-val">${doc.max_appointments_per_day||'—'}</div>
          </div>
        </div>
      </div>`;

  } else if (role === 'nurse') {
    const nu = d.nurse || {};
    roleIcon = 'fa-user-nurse'; roleLabel = 'Nurse'; roleBadgeColor = '#0d9488';
    roleBg = 'linear-gradient(135deg,#f0fdfa,#ccfbf1)';
    professionalSection = `
      <div style="margin-top:24px">
        <div style="font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:.1em;color:var(--text3);margin-bottom:12px">
          <i class="fas fa-notes-medical" style="color:var(--teal);margin-right:6px"></i>Professional Details
        </div>
        <div class="info-grid">
          <div class="info-card">
            <div class="info-label">License Number</div>
            <div class="info-val" style="font-family:'JetBrains Mono',monospace;font-size:13px">${nu.license_number||'—'}</div>
          </div>
          <div class="info-card">
            <div class="info-label">Qualification</div>
            <div class="info-val">${nu.qualification||'—'}</div>
          </div>
          <div class="info-card">
            <div class="info-label">Ward Assignment</div>
            <div class="info-val" style="color:var(--teal);font-weight:700">${nu.ward_name||'—'}</div>
          </div>
          <div class="info-card">
            <div class="info-label">Ward Type</div>
            <div class="info-val">${nu.ward_type||'—'}</div>
          </div>
          <div class="info-card">
            <div class="info-label">Shift</div>
            <div class="info-val" style="font-weight:700">${nu.shift_timing||'—'}</div>
          </div>
          <div class="info-card">
            <div class="info-label">Employment Date</div>
            <div class="info-val">${nu.employment_date||'—'}</div>
          </div>
        </div>
      </div>`;
  }

  document.getElementById('mainContent').innerHTML = `<div class="page">

    <!-- Hero banner -->
    <div style="background:${roleBg};border:1.5px solid var(--border);border-radius:20px;padding:28px 32px;margin-bottom:24px;display:flex;align-items:center;gap:22px;flex-wrap:wrap">
      <div style="width:72px;height:72px;border-radius:20px;background:linear-gradient(135deg,${roleBadgeColor},${roleBadgeColor}bb);display:grid;place-items:center;font-size:30px;color:#fff;flex-shrink:0;box-shadow:0 6px 20px ${roleBadgeColor}44">
        <i class="fas ${roleIcon}"></i>
      </div>
      <div style="flex:1">
        <div style="font-family:'DM Serif Display',serif;font-size:26px;color:var(--text);line-height:1.1;margin-bottom:6px">${displayName}</div>
        <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
          <span style="background:${roleBadgeColor}18;border:1.5px solid ${roleBadgeColor}44;border-radius:8px;padding:4px 12px;font-size:12px;font-weight:700;color:${roleBadgeColor}">
            <i class="fas ${roleIcon}" style="margin-right:5px"></i>${roleLabel}
          </span>
          ${p.person_id ? `<span style="font-family:'JetBrains Mono',monospace;font-size:12px;color:var(--text3);background:var(--surface2);padding:4px 10px;border-radius:8px;border:1px solid var(--border)">ID: ${p.person_id}</span>` : ''}
          ${p.gender ? `<span style="font-size:12px;color:var(--text3)">${p.gender}</span>` : ''}
        </div>
      </div>
    </div>

    <!-- Personal Info -->
    <div class="tcard" style="margin-bottom:20px">
      <div class="tcard-header">
        <div class="tcard-title"><i class="fas fa-address-card" style="color:var(--gold2)"></i> Personal Information</div>
      </div>
      <div style="padding:18px 22px">
        <div class="info-grid">
          <div class="info-card"><div class="info-label">Date of Birth</div><div class="info-val">${p.date_of_birth||'—'}</div></div>
          <div class="info-card"><div class="info-label">Gender</div><div class="info-val">${p.gender||'—'}</div></div>
          <div class="info-card"><div class="info-label">Blood Type</div><div class="info-val"><span class="badge b-red">${p.blood_type||'—'}</span></div></div>
          <div class="info-card"><div class="info-label">Phone</div><div class="info-val">${p.phone_number||'—'}</div></div>
          <div class="info-card"><div class="info-label">Email</div><div class="info-val">${p.email||'—'}</div></div>
          <div class="info-card"><div class="info-label">Address</div><div class="info-val">${p.physical_address||'—'}</div></div>
          <div class="info-card"><div class="info-label">National ID</div><div class="info-val" style="font-family:'JetBrains Mono',monospace;font-size:13px">${p.id_number||'—'}</div></div>
          <div class="info-card"><div class="info-label">Emergency Contact</div><div class="info-val">${p.emergency_contact_name||'—'}<br><span style="font-size:12px;color:var(--text3)">${p.emergency_contact_phone||''}</span></div></div>
          ${extraCards}
        </div>
      </div>
    </div>

    ${professionalSection ? `<div class="tcard">${professionalSection}</div>` : ''}

  </div>`;
}
</script>
</body>
</html>
"""

# ── ROUTES ──────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/api/whoami')
def api_whoami():
    if 'user_id' in session:
        return jsonify({'logged_in':True, 'role':session['role'], 'name':session['name'], 'user_id':session['user_id']})
    return jsonify({'logged_in':False})

@app.route('/api/admin_stats')
@login_required
def api_admin_stats():
    if session.get('role') != 'admin':
        return jsonify({'error': 'Admin only'}), 403
    try:
        # Appointments by status
        appt_status = query_db("SELECT status, COUNT(*) c FROM appointment GROUP BY status ORDER BY c DESC")
        # Appointments per month (last 6 months)
        appt_monthly = query_db("""
            SELECT strftime('%Y-%m', appt_datetime) AS month, COUNT(*) c
            FROM appointment
            WHERE appt_datetime >= date('now','-6 months')
            GROUP BY month ORDER BY month""")
        # Patients by gender
        gender = query_db("SELECT gender, COUNT(*) c FROM person WHERE person_id IN (SELECT person_id FROM patient) GROUP BY gender")
        # Top 5 departments by doctor count
        depts = query_db("""SELECT d.dept_name, COUNT(doc.person_id) c
            FROM department d LEFT JOIN doctor doc ON d.dept_id=doc.dept_id
            GROUP BY d.dept_id ORDER BY c DESC LIMIT 6""")
        # Ward occupancy
        wards = query_db("""SELECT ward_name,
            total_beds, (total_beds - available_beds) AS occupied
            FROM ward WHERE parent_ward_id IS NOT NULL ORDER BY total_beds DESC LIMIT 8""")
        # Invoice payment status
        inv_status = query_db("SELECT payment_status, COUNT(*) c FROM invoice GROUP BY payment_status")
        # Lab test results (normal/abnormal/pending)
        lab_results = query_db("""SELECT
            SUM(CASE WHEN result_value IS NOT NULL AND is_abnormal=0 THEN 1 ELSE 0 END) AS normal,
            SUM(CASE WHEN is_abnormal=1 THEN 1 ELSE 0 END) AS abnormal,
            SUM(CASE WHEN result_value IS NULL THEN 1 ELSE 0 END) AS pending
            FROM patient_lab_test""")
        # Medicine stock alerts
        low_stock = query_db("""SELECT medicine_name, quantity_in_stock, reorder_level
            FROM medicine WHERE quantity_in_stock <= reorder_level ORDER BY quantity_in_stock LIMIT 8""")
        # Admissions by status
        adm_status = query_db("SELECT status, COUNT(*) c FROM admission GROUP BY status")

        return jsonify({
            'appt_status': appt_status,
            'appt_monthly': appt_monthly,
            'gender': gender,
            'departments': depts,
            'wards': wards,
            'inv_status': inv_status,
            'lab_results': lab_results[0] if lab_results else {},
            'low_stock': low_stock,
            'adm_status': adm_status,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/login_stats')
def api_login_stats():
    try:
        return jsonify({
            'patients': query_db("SELECT COUNT(*) c FROM patient")[0]['c'],
            'doctors': query_db("SELECT COUNT(*) c FROM doctor")[0]['c'],
            'appointments': query_db("SELECT COUNT(*) c FROM appointment")[0]['c'],
        })
    except: return jsonify({'patients':'—','doctors':'—','appointments':'—'})

@app.route('/api/login', methods=['POST'])
def api_login():
    d = request.json
    u, p, r = d.get('username','').strip(), d.get('password',''), d.get('role','')
    # Patient login: username = person_id, password = date_of_birth
    if r == 'patient':
        person_id, full_name = resolve_patient(u, p)
        if person_id is None:
            return jsonify({'success':False,'error':'Invalid Patient ID or Date of Birth. Use YYYY-MM-DD format.'})
        session['user_id'] = person_id
        session['role'] = 'patient'
        session['username'] = str(person_id)
        session['name'] = full_name
        return jsonify({'success':True,'role':'patient','name':full_name,'user_id':person_id})
    # Staff login
    staff = STAFF_USERS.get(u)
    if not staff or staff['password'] != p:
        return jsonify({'success':False,'error':'Invalid username or password'})
    if staff['role'] != r:
        return jsonify({'success':False,'error':f'This account is a {staff["role"]}, not a {r}'})
    person_id, display_name, role = resolve_staff(u)
    session['user_id'] = person_id
    session['role'] = role
    session['username'] = u
    session['name'] = display_name
    return jsonify({'success':True,'role':role,'name':display_name,'user_id':person_id})

@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.clear(); return jsonify({'success':True})

# ── DASHBOARD ────────────────────────────────────────────────
@app.route('/api/dashboard')
@login_required
def api_dashboard():
    role, uid = session['role'], session['user_id']
    stats, today_appts = {}, []
    today = date.today().isoformat()

    # Shared today appointments query (all roles see today's schedule)
    appts_sql = """
        SELECT a.appt_datetime, a.status,
          pp.first_name||' '||pp.last_name AS patient_name,
          dp.first_name||' '||dp.last_name AS doctor_name
        FROM appointment a
        JOIN patient pt ON a.patient_id=pt.person_id
        JOIN person pp ON pt.person_id=pp.person_id
        JOIN doctor doc ON a.doctor_id=doc.person_id
        JOIN person dp ON doc.person_id=dp.person_id
        ORDER BY a.appt_datetime LIMIT 8"""

    if role == 'admin':
        stats = {
            'Patients':        query_db("SELECT COUNT(*) c FROM patient")[0]['c'],
            'Doctors':         query_db("SELECT COUNT(*) c FROM doctor")[0]['c'],
            'Nurses':          query_db("SELECT COUNT(*) c FROM nurse")[0]['c'],
            'Appointments':    query_db("SELECT COUNT(*) c FROM appointment")[0]['c'],
            'Departments':     query_db("SELECT COUNT(*) c FROM department")[0]['c'],
            'Available Rooms': query_db("SELECT COUNT(*) c FROM room WHERE is_available=1")[0]['c'],
            'Medicines':       query_db("SELECT COUNT(*) c FROM medicine")[0]['c'],
            'Admissions':      query_db("SELECT COUNT(*) c FROM admission WHERE status='Admitted'")[0]['c'],
        }
        today_appts = query_db(appts_sql)

    elif role == 'doctor' and uid:
        # Use doctor-specific counts; fall back to totals if uid not in DB
        my_appts = query_db("SELECT COUNT(*) c FROM appointment WHERE doctor_id=?",(uid,))[0]['c']
        if my_appts == 0:
            # uid not found as doctor — show all data
            stats = {
                'Total Appointments': query_db("SELECT COUNT(*) c FROM appointment")[0]['c'],
                'Total Patients':     query_db("SELECT COUNT(*) c FROM patient")[0]['c'],
                'Medical Records':    query_db("SELECT COUNT(*) c FROM medical_record")[0]['c'],
                'Prescriptions':      query_db("SELECT COUNT(*) c FROM prescription")[0]['c'],
            }
        else:
            stats = {
                'My Appointments': my_appts,
                'Patients Seen':   query_db("SELECT COUNT(DISTINCT patient_id) c FROM medical_record WHERE doctor_id=?",(uid,))[0]['c'],
                'Medical Records': query_db("SELECT COUNT(*) c FROM medical_record WHERE doctor_id=?",(uid,))[0]['c'],
                'Prescriptions':   query_db("SELECT COUNT(*) c FROM prescription p JOIN medical_record mr ON p.record_id=mr.record_id WHERE mr.doctor_id=?",(uid,))[0]['c'],
            }
        today_appts = query_db(appts_sql)

    elif role == 'nurse':
        ward_info = []
        if uid:
            ward_info = query_db("SELECT w.ward_name,w.total_beds,w.available_beds FROM nurse n JOIN ward w ON n.ward_id=w.ward_id WHERE n.person_id=?",(uid,))
        if ward_info:
            stats = {
                'Ward': ward_info[0]['ward_name'],
                'Total Beds': ward_info[0]['total_beds'],
                'Available Beds': ward_info[0]['available_beds'],
            }
        else:
            stats = {
                'Patients':     query_db("SELECT COUNT(*) c FROM patient")[0]['c'],
                'Wards':        query_db("SELECT COUNT(*) c FROM ward")[0]['c'],
                'Total Beds':   query_db("SELECT COALESCE(SUM(total_beds),0) c FROM ward WHERE parent_ward_id IS NOT NULL")[0]['c'],
            }
        stats['Admissions'] = query_db("SELECT COUNT(*) c FROM admission WHERE status='Admitted'")[0]['c']
        today_appts = query_db(appts_sql)

    elif role == 'receptionist':
        stats = {
            'Patients':           query_db("SELECT COUNT(*) c FROM patient")[0]['c'],
            'Today Appointments': query_db("SELECT COUNT(*) c FROM appointment WHERE date(appt_datetime)=?",(today,))[0]['c'],
            'Pending Invoices':   query_db("SELECT COUNT(*) c FROM invoice WHERE payment_status='Pending'")[0]['c'],
            'Admissions':         query_db("SELECT COUNT(*) c FROM admission WHERE status='Admitted'")[0]['c'],
        }
        today_appts = query_db(appts_sql)

    elif role == 'patient':
        stats = {
            'My Appointments': query_db("SELECT COUNT(*) c FROM appointment WHERE patient_id=?",(uid,))[0]['c'],
            'Medical Records':  query_db("SELECT COUNT(*) c FROM medical_record WHERE patient_id=?",(uid,))[0]['c'],
            'Prescriptions':    query_db("""SELECT COUNT(*) c FROM prescription p JOIN medical_record mr ON p.record_id=mr.record_id WHERE mr.patient_id=?""",(uid,))[0]['c'],
            'Pending Bills':    query_db("SELECT COUNT(*) c FROM invoice WHERE patient_id=? AND payment_status!='Paid'",(uid,))[0]['c'],
        }
        today_appts = query_db("""
            SELECT a.appt_datetime, a.status,
              dp.first_name||' '||dp.last_name AS doctor_name, NULL AS patient_name
            FROM appointment a
            JOIN doctor doc ON a.doctor_id=doc.person_id
            JOIN person dp ON doc.person_id=dp.person_id
            WHERE a.patient_id=? AND date(a.appt_datetime)=?
            ORDER BY a.appt_datetime""", (uid, today))

    return jsonify({'stats':stats,'today_appts':today_appts})

# ── PATIENTS ─────────────────────────────────────────────────
@app.route('/api/patients')
@login_required
def api_patients():
    role, uid = session['role'], session['user_id']
    base_sql = """
        SELECT pt.person_id, p.first_name, p.last_name, p.phone_number,
               p.gender, p.blood_type, p.date_of_birth, pt.insurance_provider
        FROM patient pt JOIN person p ON pt.person_id=p.person_id
        ORDER BY p.last_name LIMIT 300"""
    if role == 'doctor' and uid:
        # Try to get only this doctor's patients; fall back to all if none found
        rows = query_db("""
            SELECT pt.person_id, p.first_name, p.last_name, p.phone_number,
                   p.gender, p.blood_type, p.date_of_birth, pt.insurance_provider
            FROM patient pt JOIN person p ON pt.person_id=p.person_id
            WHERE pt.person_id IN (
                SELECT DISTINCT patient_id FROM appointment WHERE doctor_id=?
                UNION SELECT DISTINCT patient_id FROM medical_record WHERE doctor_id=?
            ) ORDER BY p.last_name""", (uid,uid))
        if not rows:
            rows = query_db(base_sql)
    else:
        rows = query_db(base_sql)
    return jsonify(rows)

@app.route('/api/patients_list')
@login_required
def api_patients_list():
    return jsonify(query_db("SELECT pt.person_id, p.first_name, p.last_name FROM patient pt JOIN person p ON pt.person_id=p.person_id ORDER BY p.last_name LIMIT 300"))

@app.route('/api/admin/add_patient', methods=['POST'])
@login_required
def api_add_patient():
    d = request.json
    try:
        exec_tx([
            ("""INSERT INTO person(first_name,last_name,id_number,date_of_birth,gender,phone_number,email,physical_address,blood_type,is_active)
                VALUES(?,?,?,?,?,?,?,?,?,1)""",
             (d['first_name'],d['last_name'],d.get('id_number'),d['date_of_birth'],d['gender'],
              d['phone_number'],d.get('email'),d.get('physical_address'),d.get('blood_type'))),
        ])
        pid = query_db("SELECT MAX(person_id) m FROM person")[0]['m']
        mutate_db("""INSERT INTO patient(person_id,insurance_provider,insurance_number,registration_fee_paid)VALUES(?,?,?,0)""",
                  (pid,d.get('insurance_provider'),d.get('insurance_number')))
        return jsonify({'success':True,'id':pid})
    except Exception as e: return jsonify({'success':False,'error':str(e)})

@app.route('/api/admin/delete_patient', methods=['POST'])
@login_required
def api_delete_patient():
    if session['role'] != 'admin': return jsonify({'error':'Admin only'})
    pid = request.json['id']
    try:
        exec_tx([
            ("DELETE FROM invoice_line_item WHERE invoice_id IN (SELECT invoice_id FROM invoice WHERE patient_id=?)",(pid,)),
            ("DELETE FROM invoice WHERE patient_id=?",(pid,)),
            ("DELETE FROM prescription WHERE record_id IN (SELECT record_id FROM medical_record WHERE patient_id=?)",(pid,)),
            ("DELETE FROM patient_lab_test WHERE patient_id=?",(pid,)),
            ("DELETE FROM admission WHERE patient_id=?",(pid,)),
            ("DELETE FROM appointment WHERE patient_id=?",(pid,)),
            ("DELETE FROM medical_record WHERE patient_id=?",(pid,)),
            ("DELETE FROM patient WHERE person_id=?",(pid,)),
            ("DELETE FROM person WHERE person_id=?",(pid,)),
        ])
        return jsonify({'success':True})
    except Exception as e: return jsonify({'success':False,'error':str(e)})

# ── DOCTORS ──────────────────────────────────────────────────
@app.route('/api/doctors')
@login_required
def api_doctors():
    return jsonify(query_db("""
        SELECT doc.person_id, p.first_name, p.last_name, p.phone_number,
               doc.license_number, doc.specialization, d.dept_name,
               doc.years_experience, doc.consultation_fee, doc.qualification
        FROM doctor doc
        JOIN person p ON doc.person_id=p.person_id
        JOIN department d ON doc.dept_id=d.dept_id
        ORDER BY p.last_name"""))

@app.route('/api/doctors_list')
@login_required
def api_doctors_list():
    return jsonify(query_db("SELECT doc.person_id, p.first_name, p.last_name, doc.specialization FROM doctor doc JOIN person p ON doc.person_id=p.person_id ORDER BY p.last_name"))

@app.route('/api/admin/add_doctor', methods=['POST'])
@login_required
def api_add_doctor():
    if session['role'] != 'admin': return jsonify({'error':'Admin only'})
    d = request.json
    try:
        exec_tx([
            ("""INSERT INTO person(first_name,last_name,date_of_birth,gender,phone_number,email,is_active)VALUES(?,?,?,?,?,?,1)""",
             (d['first_name'],d['last_name'],d.get('date_of_birth'),d.get('gender'),d['phone_number'],d.get('email'))),
        ])
        pid = query_db("SELECT MAX(person_id) m FROM person")[0]['m']
        mutate_db("""INSERT INTO doctor(person_id,license_number,specialization,dept_id,qualification,years_experience,consultation_fee,max_appointments_per_day)
                     VALUES(?,?,?,?,?,?,?,?)""",
                  (pid,d['license_number'],d['specialization'],d['dept_id'],d.get('qualification'),
                   d.get('years_experience',0),d.get('consultation_fee',50),d.get('max_appointments_per_day',20)))
        return jsonify({'success':True,'id':pid})
    except Exception as e: return jsonify({'success':False,'error':str(e)})

@app.route('/api/admin/delete_doctor', methods=['POST'])
@login_required
def api_delete_doctor():
    if session['role'] != 'admin': return jsonify({'error':'Admin only'})
    did = request.json['id']
    try:
        exec_tx([
            ("DELETE FROM prescription WHERE record_id IN (SELECT record_id FROM medical_record WHERE doctor_id=?)",(did,)),
            ("DELETE FROM patient_lab_test WHERE doctor_id=?",(did,)),
            ("DELETE FROM medical_record WHERE doctor_id=?",(did,)),
            ("DELETE FROM appointment WHERE doctor_id=?",(did,)),
            ("DELETE FROM doctor WHERE person_id=?",(did,)),
            ("DELETE FROM person WHERE person_id=?",(did,)),
        ])
        return jsonify({'success':True})
    except Exception as e: return jsonify({'success':False,'error':str(e)})

# ── NURSES ───────────────────────────────────────────────────
@app.route('/api/nurses')
@login_required
def api_nurses():
    return jsonify(query_db("""
        SELECT n.person_id, p.first_name, p.last_name, p.phone_number,
               n.license_number, n.qualification, w.ward_name, n.shift
        FROM nurse n
        JOIN person p ON n.person_id=p.person_id
        JOIN ward w ON n.ward_id=w.ward_id
        ORDER BY p.last_name"""))

@app.route('/api/admin/add_nurse', methods=['POST'])
@login_required
def api_add_nurse():
    if session['role'] != 'admin': return jsonify({'error':'Admin only'})
    d = request.json
    try:
        exec_tx([
            ("""INSERT INTO person(first_name,last_name,date_of_birth,gender,phone_number,email,is_active)VALUES(?,?,?,?,?,?,1)""",
             (d['first_name'],d['last_name'],d.get('date_of_birth'),d.get('gender'),d['phone_number'],d.get('email'))),
        ])
        pid = query_db("SELECT MAX(person_id) m FROM person")[0]['m']
        mutate_db("INSERT INTO nurse(person_id,license_number,qualification,ward_id,shift)VALUES(?,?,?,?,?)",
                  (pid,d['license_number'],d['qualification'],d['ward_id'],d.get('shift','Rotating')))
        return jsonify({'success':True,'id':pid})
    except Exception as e: return jsonify({'success':False,'error':str(e)})

@app.route('/api/admin/delete_nurse', methods=['POST'])
@login_required
def api_delete_nurse():
    if session['role'] != 'admin': return jsonify({'error':'Admin only'})
    nid = request.json['id']
    try:
        exec_tx([("DELETE FROM nurse WHERE person_id=?",(nid,)),("DELETE FROM person WHERE person_id=?",(nid,))])
        return jsonify({'success':True})
    except Exception as e: return jsonify({'success':False,'error':str(e)})

# ── APPOINTMENTS ─────────────────────────────────────────────
@app.route('/api/appointments')
@login_required
def api_appointments():
    role, uid = session['role'], session['user_id']
    base = """SELECT a.appt_id, a.appt_datetime, a.appt_type, a.status, a.reason,
              pp.first_name||' '||pp.last_name AS patient_name,
              dp.first_name||' '||dp.last_name AS doctor_name
            FROM appointment a
            JOIN patient pt ON a.patient_id=pt.person_id
            JOIN person pp ON pt.person_id=pp.person_id
            JOIN doctor doc ON a.doctor_id=doc.person_id
            JOIN person dp ON doc.person_id=dp.person_id"""
    if role == 'doctor' and uid:
        rows = query_db(base + " WHERE a.doctor_id=? ORDER BY a.appt_datetime DESC LIMIT 100", (uid,))
        if not rows:
            rows = query_db(base + " ORDER BY a.appt_datetime DESC LIMIT 200")
    else:
        rows = query_db(base + " ORDER BY a.appt_datetime DESC LIMIT 200")
    return jsonify(rows)

@app.route('/api/add_appointment', methods=['POST'])
@login_required
def api_add_appointment():
    d = request.json
    try:
        dt = f"{d['appt_date']} {d['appt_time']}:00"
        mutate_db("""INSERT INTO appointment(patient_id,doctor_id,appt_datetime,appt_type,status,reason,duration_minutes)
                     VALUES(?,?,?,?,?,?,?)""",
                  (d['patient_id'],d['doctor_id'],dt,d.get('appt_type','Consultation'),
                   'Scheduled',d.get('reason'),d.get('duration_minutes',30)))
        return jsonify({'success':True})
    except Exception as e: return jsonify({'success':False,'error':str(e)})

@app.route('/api/update_appointment', methods=['POST'])
@login_required
def api_update_appointment():
    d = request.json
    try:
        mutate_db("UPDATE appointment SET status=? WHERE appt_id=?", (d['status'],d['id']))
        if d['status'] == 'Checked In':
            mutate_db("UPDATE appointment SET check_in_time=DATETIME('now') WHERE appt_id=?",(d['id'],))
        elif d['status'] == 'Completed':
            mutate_db("UPDATE appointment SET check_out_time=DATETIME('now') WHERE appt_id=?",(d['id'],))
        return jsonify({'success':True})
    except Exception as e: return jsonify({'success':False,'error':str(e)})

@app.route('/api/delete_appointment', methods=['POST'])
@login_required
def api_delete_appointment():
    try:
        mutate_db("DELETE FROM appointment WHERE appt_id=?", (request.json['id'],))
        return jsonify({'success':True})
    except Exception as e: return jsonify({'success':False,'error':str(e)})

# ── MEDICAL RECORDS ──────────────────────────────────────────
@app.route('/api/records')
@login_required
def api_records():
    role, uid = session['role'], session['user_id']
    base = """SELECT mr.record_id, mr.visit_date, mr.diagnosis, mr.treatment, mr.symptoms,
              mr.blood_pressure_systolic, mr.blood_pressure_diastolic,
              mr.heart_rate, mr.temperature, mr.weight_kg, mr.height_cm, mr.follow_up_date,
              pp.first_name||' '||pp.last_name AS patient_name,
              dp.first_name||' '||dp.last_name AS doctor_name
            FROM medical_record mr
            JOIN patient pt ON mr.patient_id=pt.person_id
            JOIN person pp ON pt.person_id=pp.person_id
            JOIN doctor doc ON mr.doctor_id=doc.person_id
            JOIN person dp ON doc.person_id=dp.person_id"""
    if role == 'doctor' and uid:
        rows = query_db(base + " WHERE mr.doctor_id=? ORDER BY mr.visit_date DESC LIMIT 100", (uid,))
        if not rows:
            rows = query_db(base + " ORDER BY mr.visit_date DESC LIMIT 200")
    else:
        rows = query_db(base + " ORDER BY mr.visit_date DESC LIMIT 200")
    return jsonify(rows)

@app.route('/api/add_record', methods=['POST'])
@login_required
def api_add_record():
    d = request.json; uid = session['user_id']
    # For non-doctors, use first doctor in DB as fallback
    doctor_id = uid
    if session['role'] != 'doctor':
        dr = query_db("SELECT person_id FROM doctor LIMIT 1")
        if dr: doctor_id = dr[0]['person_id']
    try:
        mutate_db("""INSERT INTO medical_record(patient_id,doctor_id,visit_date,diagnosis,treatment,symptoms,
                     blood_pressure_systolic,blood_pressure_diastolic,heart_rate,temperature,weight_kg,height_cm,follow_up_date)
                     VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                  (d['patient_id'],doctor_id,d['visit_date'],d['diagnosis'],d.get('treatment'),
                   d.get('symptoms'),d.get('blood_pressure_systolic'),d.get('blood_pressure_diastolic'),
                   d.get('heart_rate'),d.get('temperature'),d.get('weight_kg'),d.get('height_cm'),
                   d.get('follow_up_date')))
        return jsonify({'success':True})
    except Exception as e: return jsonify({'success':False,'error':str(e)})

@app.route('/api/delete_record', methods=['POST'])
@login_required
def api_delete_record():
    if session['role'] not in ['admin','doctor']: return jsonify({'error':'Not allowed'})
    rid = request.json['id']
    try:
        exec_tx([
            ("DELETE FROM prescription WHERE record_id=?",(rid,)),
            ("DELETE FROM medical_record WHERE record_id=?",(rid,)),
        ])
        return jsonify({'success':True})
    except Exception as e: return jsonify({'success':False,'error':str(e)})

# ── PRESCRIPTIONS ────────────────────────────────────────────
@app.route('/api/prescriptions')
@login_required
def api_prescriptions():
    role, uid = session['role'], session['user_id']
    base = """SELECT p.prescription_id, p.dosage, p.frequency, p.duration_days,
              p.quantity_prescribed, p.prescribed_date, p.is_dispensed,
              m.medicine_name,
              pp.first_name||' '||pp.last_name AS patient_name
            FROM prescription p
            JOIN medicine m ON p.medicine_id=m.medicine_id
            JOIN medical_record mr ON p.record_id=mr.record_id
            JOIN patient pt ON mr.patient_id=pt.person_id
            JOIN person pp ON pt.person_id=pp.person_id"""
    if role == 'doctor' and uid:
        rows = query_db(base + " WHERE mr.doctor_id=? ORDER BY p.prescribed_date DESC LIMIT 100",(uid,))
        if not rows:
            rows = query_db(base + " ORDER BY p.prescribed_date DESC LIMIT 200")
    else:
        rows = query_db(base + " ORDER BY p.prescribed_date DESC LIMIT 200")
    return jsonify(rows)

@app.route('/api/add_prescription', methods=['POST'])
@login_required
def api_add_prescription():
    d = request.json
    try:
        mutate_db("""INSERT INTO prescription(record_id,medicine_id,dosage,frequency,duration_days,
                     quantity_prescribed,instructions,prescribed_date,is_dispensed)
                     VALUES(?,?,?,?,?,?,?,DATE('now'),0)""",
                  (d['record_id'],d['medicine_id'],d['dosage'],d.get('frequency'),
                   d.get('duration_days'),d.get('quantity_prescribed'),d.get('instructions')))
        return jsonify({'success':True})
    except Exception as e: return jsonify({'success':False,'error':str(e)})

# ── LAB TESTS ────────────────────────────────────────────────
@app.route('/api/lab_tests')
@login_required
def api_lab_tests():
    role, uid = session['role'], session['user_id']
    base = """SELECT plt.test_order_id, plt.order_date, plt.status, plt.result_value,
              plt.is_abnormal, plt.scheduled_date,
              ltc.test_name, ltc.test_category,
              pp.first_name||' '||pp.last_name AS patient_name
            FROM patient_lab_test plt
            JOIN lab_test_catalog ltc ON plt.test_id=ltc.test_id
            JOIN patient pt ON plt.patient_id=pt.person_id
            JOIN person pp ON pt.person_id=pp.person_id"""
    if role == 'doctor' and uid:
        rows = query_db(base + " WHERE plt.doctor_id=? ORDER BY plt.order_date DESC LIMIT 100",(uid,))
        if not rows:
            rows = query_db(base + " ORDER BY plt.order_date DESC LIMIT 200")
    else:
        rows = query_db(base + " ORDER BY plt.order_date DESC LIMIT 200")
    return jsonify(rows)

@app.route('/api/lab_catalog')
@login_required
def api_lab_catalog():
    return jsonify(query_db("SELECT test_id, test_name, test_category, cost FROM lab_test_catalog WHERE is_active=1 ORDER BY test_name"))

@app.route('/api/add_lab_order', methods=['POST'])
@login_required
def api_add_lab_order():
    d = request.json; uid = session['user_id']
    doctor_id = uid
    if session['role'] != 'doctor':
        dr = query_db("SELECT person_id FROM doctor LIMIT 1")
        if dr: doctor_id = dr[0]['person_id']
    try:
        mutate_db("""INSERT INTO patient_lab_test(patient_id,doctor_id,test_id,order_date,scheduled_date,status,notes)
                     VALUES(?,?,?,DATETIME('now'),?,?,?)""",
                  (d['patient_id'],doctor_id,d['test_id'],d.get('scheduled_date'),'Ordered',d.get('notes')))
        return jsonify({'success':True})
    except Exception as e: return jsonify({'success':False,'error':str(e)})

# ── ADMISSIONS ───────────────────────────────────────────────
@app.route('/api/admissions')
@login_required
def api_admissions():
    return jsonify(query_db("""
        SELECT adm.admission_id, adm.admission_datetime, adm.expected_discharge_datetime,
               adm.status, adm.admission_reason,
               pp.first_name||' '||pp.last_name AS patient_name,
               dp.first_name||' '||dp.last_name AS doctor_name,
               r.room_number, w.ward_name
        FROM admission adm
        JOIN patient pt ON adm.patient_id=pt.person_id
        JOIN person pp ON pt.person_id=pp.person_id
        JOIN doctor doc ON adm.admitting_doctor_id=doc.person_id
        JOIN person dp ON doc.person_id=dp.person_id
        JOIN room r ON adm.room_id=r.room_id
        JOIN ward w ON r.ward_id=w.ward_id
        ORDER BY adm.admission_datetime DESC LIMIT 200"""))

# ── WARDS / ROOMS ────────────────────────────────────────────
@app.route('/api/wards')
@login_required
def api_wards():
    return jsonify(query_db("SELECT ward_id, ward_name, ward_type, total_beds, available_beds FROM ward ORDER BY ward_name"))

@app.route('/api/wards_list')
@login_required
def api_wards_list():
    return jsonify(query_db("SELECT ward_id, ward_name FROM ward ORDER BY ward_name"))

@app.route('/api/rooms')
@login_required
def api_rooms():
    return jsonify(query_db("""
        SELECT r.room_id, r.room_number, r.room_type, r.bed_capacity, r.is_available,
               w.ward_name
        FROM room r JOIN ward w ON r.ward_id=w.ward_id
        ORDER BY r.room_number LIMIT 200"""))

# ── DEPARTMENTS ──────────────────────────────────────────────
@app.route('/api/departments')
@login_required
def api_departments():
    return jsonify(query_db("""
        SELECT d.dept_id, d.dept_name, d.floor_number, d.phone_extension,
               COUNT(DISTINCT doc.person_id) AS doctor_count,
               COUNT(DISTINCT r.room_id) AS room_count,
               COUNT(DISTINCT a.appt_id) AS appt_count
        FROM department d
        LEFT JOIN doctor doc ON d.dept_id=doc.dept_id
        LEFT JOIN room r ON d.dept_id=r.dept_id
        LEFT JOIN appointment a ON doc.person_id=a.doctor_id
        GROUP BY d.dept_id ORDER BY d.dept_name"""))

@app.route('/api/departments_list')
@login_required
def api_departments_list():
    return jsonify(query_db("SELECT dept_id, dept_name FROM department ORDER BY dept_name"))

# ── INVOICES ─────────────────────────────────────────────────
@app.route('/api/invoices')
@login_required
def api_invoices():
    return jsonify(query_db("""
        SELECT i.invoice_id, i.invoice_date, i.due_date, i.subtotal, i.tax,
               i.total_amount, i.amount_paid, i.payment_status,
               pp.first_name||' '||pp.last_name AS patient_name
        FROM invoice i
        JOIN patient pt ON i.patient_id=pt.person_id
        JOIN person pp ON pt.person_id=pp.person_id
        ORDER BY i.invoice_date DESC LIMIT 200"""))

# ── MEDICINES ────────────────────────────────────────────────
@app.route('/api/medicines')
@login_required
def api_medicines():
    return jsonify(query_db("SELECT * FROM medicine ORDER BY medicine_name LIMIT 300"))

@app.route('/api/medicines_list')
@login_required
def api_medicines_list():
    return jsonify(query_db("SELECT medicine_id, medicine_name, strength, dosage_form FROM medicine WHERE quantity_in_stock>0 ORDER BY medicine_name"))

# ── SQL RUNNER ───────────────────────────────────────────────
@app.route('/api/sql', methods=['POST'])
@login_required
def api_sql():
    if session['role'] != 'admin': return jsonify({'error':'Admin access only'})
    q = request.json.get('query','').strip()
    if not q: return jsonify({'error':'Empty query'})
    conn = get_db()
    try:
        cur = conn.execute(q); conn.commit()
        if q.upper().lstrip().startswith('SELECT'):
            rows = [dict(r) for r in cur.fetchall()]
            conn.close(); return jsonify({'type':'SELECT','data':rows})
        qtype = q.upper().strip().split()[0]
        r = {'type':qtype,'rows_affected':cur.rowcount,'last_id':cur.lastrowid}
        conn.close(); return jsonify(r)
    except Exception as e:
        conn.close(); return jsonify({'error':str(e)})

# ── PATIENT PORTAL ROUTES ───────────────────────────────────
@app.route('/api/my/appointments')
@login_required
def api_my_appointments():
    uid = session['user_id']
    return jsonify(query_db("""
        SELECT a.appt_id, a.appt_datetime, a.appt_type, a.status, a.reason,
               dp.first_name||' '||dp.last_name AS doctor_name, doc.specialization
        FROM appointment a
        JOIN doctor doc ON a.doctor_id=doc.person_id
        JOIN person dp ON doc.person_id=dp.person_id
        WHERE a.patient_id=? ORDER BY a.appt_datetime DESC""", (uid,)))

@app.route('/api/my/records')
@login_required
def api_my_records():
    uid = session['user_id']
    return jsonify(query_db("""
        SELECT mr.record_id, mr.visit_date, mr.diagnosis, mr.treatment, mr.symptoms,
               mr.blood_pressure_systolic, mr.blood_pressure_diastolic,
               mr.heart_rate, mr.temperature, mr.weight_kg, mr.height_cm, mr.follow_up_date,
               dp.first_name||' '||dp.last_name AS doctor_name
        FROM medical_record mr
        JOIN doctor doc ON mr.doctor_id=doc.person_id
        JOIN person dp ON doc.person_id=dp.person_id
        WHERE mr.patient_id=? ORDER BY mr.visit_date DESC""", (uid,)))

@app.route('/api/my/prescriptions')
@login_required
def api_my_prescriptions():
    uid = session['user_id']
    return jsonify(query_db("""
        SELECT p.prescription_id, p.dosage, p.frequency, p.duration_days,
               p.quantity_prescribed, p.prescribed_date, p.is_dispensed,
               m.medicine_name, m.generic_name, m.dosage_form
        FROM prescription p
        JOIN medicine m ON p.medicine_id=m.medicine_id
        JOIN medical_record mr ON p.record_id=mr.record_id
        WHERE mr.patient_id=? ORDER BY p.prescribed_date DESC""", (uid,)))

@app.route('/api/my/labtests')
@login_required
def api_my_labtests():
    uid = session['user_id']
    return jsonify(query_db("""
        SELECT plt.test_order_id, plt.order_date, plt.scheduled_date, plt.status,
               plt.result_value, plt.is_abnormal, ltc.test_name, ltc.test_category
        FROM patient_lab_test plt
        JOIN lab_test_catalog ltc ON plt.test_id=ltc.test_id
        WHERE plt.patient_id=? ORDER BY plt.order_date DESC""", (uid,)))

@app.route('/api/my/invoices')
@login_required
def api_my_invoices():
    uid = session['user_id']
    return jsonify(query_db("""
        SELECT invoice_id, invoice_date, due_date, subtotal, tax, total_amount, amount_paid, payment_status
        FROM invoice WHERE patient_id=? ORDER BY invoice_date DESC""", (uid,)))

@app.route('/api/my/profile')
@login_required
def api_my_profile():
    uid = session['user_id']
    role = session['role']
    username = session.get('username', '')

    # If uid is None (admin/receptionist with no DB record) return name-only info
    if uid is None:
        return jsonify({'person': {'first_name': session.get('name', username), 'last_name': '', 'person_id': '—'}, 'role': role})

    # For doctor/nurse: if uid somehow not found, try re-resolving from username
    if role in ('doctor', 'nurse'):
        check = query_db("SELECT person_id FROM person WHERE person_id=?", (uid,))
        if not check:
            # Re-resolve from username
            person_id, _, _ = resolve_staff(username)
            if person_id:
                uid = person_id
                # Update session
                session['user_id'] = uid

    person = query_db("SELECT * FROM person WHERE person_id=?", (uid,))
    result = {'person': person[0] if person else {}}
    if role == 'patient':
        patient = query_db("SELECT marital_status, occupation, insurance_provider, insurance_number FROM patient WHERE person_id=?", (uid,))
        result['patient'] = patient[0] if patient else {}
    elif role == 'doctor':
        doctor = query_db("""
            SELECT d.license_number, d.specialization, d.qualification, d.years_of_experience,
                   d.consultation_fee, d.max_appointments_per_day, dept.dept_name
            FROM doctor d LEFT JOIN department dept ON d.dept_id=dept.dept_id
            WHERE d.person_id=?""", (uid,))
        result['doctor'] = doctor[0] if doctor else {}
    elif role == 'nurse':
        nurse = query_db("""
            SELECT n.license_number, n.qualification, n.shift_timing, n.employment_date,
                   w.ward_name, w.ward_type
            FROM nurse n LEFT JOIN ward w ON n.ward_id=w.ward_id
            WHERE n.person_id=?""", (uid,))
        result['nurse'] = nurse[0] if nurse else {}
    return jsonify(result)

# ── MAIN ─────────────────────────────────────────────────────
if __name__ == '__main__':
    if not os.path.exists(DB_NAME):
        print(f"\n⚠  Database '{DB_NAME}' not found.")
        print(f"   Run: python create_sqlite_db.py  then  python populate_db.py\n")
    else:
        print(f"✓  Connected to {DB_NAME}")

    print("\n" + "="*60)
    print("  MediCare HMS — Complete Web Interface (Final)")
    print("="*60)
    print("\n  Open: http://localhost:5000")
    print("\n  Credentials:")
    print("    admin       / admin123    (Administrator)")
    print("    drsmith     / doctor123   (Doctor)")
    print("    nurse1      / nurse123    (Nurse)")
    print("    reception   / recept123   (Receptionist)")
    print("\n  Features:")
    print("    • Role-based access control (4 roles)")
    print("    • Patients, Doctors, Nurses CRUD")
    print("    • Appointments scheduling & status tracking")
    print("    • Medical Records with vitals")
    print("    • Prescriptions & Lab Test ordering")
    print("    • Admissions, Wards, Rooms overview")
    print("    • Invoice management")
    print("    • Medicine inventory")
    print("    • Admin SQL Query Runner")
    print("\nPress Ctrl+C to stop\n")
    app.run(debug=True, port=5000)
