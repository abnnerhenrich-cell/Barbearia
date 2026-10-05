import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import time
import uuid
from datetime import datetime, timedelta, timezone
from functools import wraps
from pathlib import Path
from zoneinfo import ZoneInfo

from flask import Flask, jsonify, request, session, render_template, redirect, url_for, Response
from werkzeug.exceptions import HTTPException
from werkzeug.security import check_password_hash
from booking_rules import clock, minutes, parse_day, free_slots
from db import Database

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE = Path(__file__).resolve().parent


def create_app(overrides=None):
    app = Flask(__name__, static_folder='public/static', static_url_path='/static')
    app.config.update(
        SECRET_KEY=os.environ.get('SECRET_KEY'),
        DATABASE_URL=os.environ.get('DATABASE_URL', ''),
        SQLITE_PATH=str(BASE / 'local.sqlite3'),
        ADMIN_USERNAME=os.environ.get('ADMIN_USERNAME', 'admin'),
        ADMIN_PASSWORD_HASH=os.environ.get('ADMIN_PASSWORD_HASH', ''),
        SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax',
        SESSION_COOKIE_SECURE=bool(os.environ.get('VERCEL') or os.environ.get('APP_ENV') == 'production'),
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8), MAX_CONTENT_LENGTH=16384,
        TESTING=False,
    )
    if overrides:
        app.config.update(overrides)
    production = bool(os.environ.get('VERCEL') or os.environ.get('APP_ENV') == 'production')
    ready = bool(app.config['SECRET_KEY'] and len(app.config['SECRET_KEY']) >= 32 and app.config['ADMIN_PASSWORD_HASH'])
    if production and not app.config['DATABASE_URL']:
        ready = False
    if not ready:
        # Sem credenciais não exponha painel, reservas ou cookies com segredo padrão.
        app.secret_key = secrets.token_hex(32)
    config = json.loads((BASE / 'settings.json').read_text(encoding='utf-8'))
    if os.environ.get('BUSINESS_WHATSAPP'):
        config['whatsapp'] = os.environ['BUSINESS_WHATSAPP']
    if overrides and overrides.get('SITE_SETTINGS'):
        config = overrides['SITE_SETTINGS']
    validate_settings(config)
    db = Database(app)
    app.extensions['database'] = db
    app.extensions['site_settings'] = config

    def utcnow():
        return datetime.now(timezone.utc).isoformat()

    def auth_stamp():
        return hashlib.sha256(app.config['ADMIN_PASSWORD_HASH'].encode()).hexdigest()

    def authenticated():
        return session.get('admin') == app.config['ADMIN_USERNAME'] and hmac.compare_digest(session.get('auth_stamp', ''), auth_stamp())

    def require_admin(fn):
        @wraps(fn)
        def inner(*args, **kwargs):
            if not authenticated():
                return jsonify(error='Entre no painel para continuar.'), 401
            return fn(*args, **kwargs)
        return inner

    def csrf_token():
        if 'csrf' not in session:
            session['csrf'] = secrets.token_urlsafe(32)
        return session['csrf']

    def client_key():
        if 'client' not in session:
            session['client'] = secrets.token_urlsafe(32)
        return session['client']

    def limit(kind, maximum, window, extra=''):
        if app.config['TESTING'] and app.config.get('DISABLE_RATE_LIMIT', False):
            return True
        ip = request.remote_addr or 'unknown'
        if os.environ.get('VERCEL'):
            ip = request.headers.get('x-vercel-forwarded-for', ip).split(',')[0].strip()
        bucket = int(time.time()) // window
        raw = f'{kind}|{ip}|{extra}|{bucket}'
        key = hmac.new(app.secret_key.encode(), raw.encode(), hashlib.sha256).hexdigest()
        with db.transaction(write=True) as conn:
            row = conn.execute('INSERT INTO rate_limits(key,hits,expires_at) VALUES(?,1,?) ON CONFLICT(key) DO UPDATE SET hits=rate_limits.hits+1 RETURNING hits', (key, (bucket + 1) * window)).fetchone()
            conn.execute('DELETE FROM rate_limits WHERE expires_at < ?', (int(time.time()) - window,))
        return row['hits'] <= maximum

    def find_service(service_id):
        service = next((s for s in config['services'] if s['id'] == service_id), None)
        if not service:
            raise ValueError('Selecione um serviço válido.')
        return service

    def professionals(professional_id):
        if professional_id == 'any':
            return config['professionals']
        result = [p for p in config['professionals'] if p['id'] == professional_id]
        if not result:
            raise ValueError('Selecione um profissional válido.')
        return result

    def busy(conn, professional_id, day):
        return conn.execute("SELECT start_minute,end_minute FROM bookings WHERE professional_id=? AND day=? AND status <> 'cancelled'", (professional_id, day)).fetchall()

    def available(conn, prof, day, duration):
        return free_slots(config, day, duration, busy(conn, prof['id'], day))

    def audit(conn, booking_id, action, actor, note=''):
        conn.execute('INSERT INTO audit(id,booking_id,action,actor,note,created_at) VALUES(?,?,?,?,?,?)', (str(uuid.uuid4()), booking_id, action, actor, note, utcnow()))

    def public_booking(row):
        return {'id':row['id'], 'reference':row['id'][:8].upper(), 'service':row['service_name'], 'professional':row['professional_name'], 'date':row['day'], 'time':clock(row['start_minute']), 'end':clock(row['end_minute']), 'status':row['status'], 'price':row['price_cents']/100}

    @app.before_request
    def protect():
        if request.path.startswith('/static/'):
            return
        if not ready:
            if request.path.startswith('/api/'):
                return jsonify(error='Configuração pendente. O responsável precisa configurar banco e credenciais.'), 503
            return render_template('setup-required.html'), 503
        if request.method in ('POST','PATCH','DELETE','PUT'):
            token = request.headers.get('X-CSRF-Token', '')
            if not token or not hmac.compare_digest(token, session.get('csrf', '')):
                return jsonify(error='Sua sessão expirou. Atualize a página.'), 403

    @app.after_request
    def headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'same-origin'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; form-action 'self'; base-uri 'self'"
        if not request.path.startswith('/static/'):
            response.headers['Cache-Control'] = 'no-store'
        return response

    @app.errorhandler(ValueError)
    def value_error(error):
        return jsonify(error=str(error)), 400

    @app.errorhandler(Exception)
    def unexpected(error):
        if isinstance(error, HTTPException):
            if request.path.startswith('/api/'):
                return jsonify(error=error.description), error.code
            return error
        # Não exponha SQL, URL de conexão nem dados pessoais nos logs/respostas.
        app.logger.error('Falha interna: %s', type(error).__name__)
        return jsonify(error='Não foi possível concluir. Tente novamente. Se persistir, contate a barbearia.'), 503

    @app.get('/')
    def index():
        return render_template('index.html')

    @app.get('/api/config.js')
    def site_config():
        return Response('window.SITE_CONFIG = ' + json.dumps(config, ensure_ascii=False) + ';', mimetype='application/javascript')

    @app.get('/api/session')
    def session_info():
        client_key()
        return jsonify(csrf=csrf_token(), authenticated=authenticated())

    @app.get('/api/health')
    def health():
        try:
            with db.transaction() as conn:
                conn.execute('SELECT id FROM bookings LIMIT 1')
                if conn.postgres and not conn.execute("SELECT 1 FROM pg_constraint WHERE conname='bravo_no_overlap' AND conrelid='bookings'::regclass").fetchone():
                    return jsonify(ok=False, error='Inicialize o banco com setup-neon.sql.'), 503
            return jsonify(ok=True)
        except Exception:
            return jsonify(ok=False, error='Banco indisponível ou não inicializado.'), 503

    @app.get('/api/availability')
    def availability():
        service = find_service(request.args.get('service'))
        day = request.args.get('date', '')
        parse_day(day)
        profs = professionals(request.args.get('professional', 'any'))
        with db.transaction() as conn:
            result = sorted({clock(m) for prof in profs for m in available(conn, prof, day, service['duration'])})
        return jsonify(slots=result)

    @app.post('/api/bookings')
    def book():
        body = request.get_json(silent=True) or {}
        if not isinstance(body, dict):
            raise ValueError('Solicitação inválida.')
        if body.get('website'):
            raise ValueError('Solicitação inválida.')
        name = str(body.get('name','')).strip()
        phone = re.sub(r'\D','',str(body.get('phone','')))
        if len(phone) in (10,11):
            phone = '55'+phone
        if not 2 <= len(name) <= 80 or not re.fullmatch(r'55\d{10,11}', phone):
            raise ValueError('Informe nome e telefone brasileiro com DDD válidos.')
        if body.get('consent') is not True:
            raise ValueError('Confirme o envio dos dados para reservar.')
        try:
            request_key = str(uuid.UUID(str(body.get('requestKey',''))))
        except ValueError:
            raise ValueError('Chave de reserva inválida. Atualize a página.')
        service = find_service(body.get('service'))
        profs = sorted(professionals(body.get('professional', 'any')), key=lambda p:p['id'])
        day = str(body.get('date',''))
        parse_day(day)
        start = minutes(body.get('time',''))
        owner = client_key()
        # Reenvios após falha de conexão retornam a reserva já salva, sem duplicar.
        with db.transaction() as conn:
            existing = conn.execute('SELECT * FROM bookings WHERE request_key=?', (request_key,)).fetchone()
            if existing:
                if existing['owner_key'] != owner:
                    return jsonify(error='Chave de reserva inválida.'), 409
                return jsonify(booking=public_booking(existing), repeated=True)
        if not limit('booking', 20, 3600):
            return jsonify(error='Muitas solicitações. Tente novamente mais tarde.'), 429
        with db.transaction(write=True) as conn:
            # Ordem de locks determinística inclusive na escolha "Sem preferência".
            for prof in profs:
                conn.lock(prof['id'], day)
            existing = conn.execute('SELECT * FROM bookings WHERE request_key=?', (request_key,)).fetchone()
            if existing:
                if existing['owner_key'] != owner:
                    return jsonify(error='Chave de reserva inválida.'), 409
                return jsonify(booking=public_booking(existing), repeated=True)
            prof = next((p for p in profs if start in available(conn,p,day,service['duration'])), None)
            if not prof:
                return jsonify(error='Esse horário acabou de ficar indisponível. Escolha outro.'), 409
            booking_id = str(uuid.uuid4())
            now = utcnow()
            conn.execute('INSERT INTO bookings(id,request_key,owner_key,customer_name,customer_phone,service_id,service_name,price_cents,professional_id,professional_name,day,start_minute,end_minute,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', (booking_id,request_key,owner,name,phone,service['id'],service['name'],round(service['price']*100),prof['id'],prof['name'],day,start,start+service['duration'],'pending',now,now))
            audit(conn,booking_id,'created','customer')
            row = conn.execute('SELECT * FROM bookings WHERE id=?', (booking_id,)).fetchone()
        return jsonify(booking=public_booking(row)), 201

    @app.get('/admin')
    def admin_page():
        return render_template('admin.html' if authenticated() else 'login.html')

    @app.post('/api/admin/login')
    def login():
        if not limit('login', 8, 900):
            return jsonify(error='Muitas tentativas. Aguarde 15 minutos.'), 429
        body = request.get_json(silent=True) or {}
        if not isinstance(body,dict):
            raise ValueError('Dados inválidos.')
        password = str(body.get('password',''))
        if len(password)>256 or not hmac.compare_digest(str(body.get('username','')), app.config['ADMIN_USERNAME']) or not check_password_hash(app.config['ADMIN_PASSWORD_HASH'],password):
            return jsonify(error='Usuário ou senha incorretos.'), 401
        session.clear()
        session.permanent = True
        session['admin'] = app.config['ADMIN_USERNAME']
        session['auth_stamp'] = auth_stamp()
        return jsonify(ok=True,csrf=csrf_token())

    @app.post('/api/admin/logout')
    @require_admin
    def logout():
        session.clear()
        return jsonify(ok=True)

    @app.get('/api/admin/bookings')
    @require_admin
    def admin_bookings():
        day = request.args.get('date',datetime.now(ZoneInfo(config['timezone'])).date().isoformat())
        parse_day(day)
        with db.transaction() as conn:
            rows = conn.execute('SELECT * FROM bookings WHERE day=? ORDER BY start_minute,professional_name', (day,)).fetchall()
        result=[]
        for row in rows:
            item=public_booking(row)
            item.update(name=row['customer_name'],phone=row['customer_phone'],professionalId=row['professional_id'],note=row['note'])
            result.append(item)
        return jsonify(bookings=result)

    @app.post('/api/admin/bookings/<booking_id>/status')
    @require_admin
    def change_status(booking_id):
        body = request.get_json(silent=True) or {}
        if not isinstance(body,dict):
            raise ValueError('Dados inválidos.')
        target = body.get('status')
        note = str(body.get('note','')).strip()[:300]
        with db.transaction(write=True) as conn:
            suffix = ' FOR UPDATE' if conn.postgres else ''
            row = conn.execute('SELECT * FROM bookings WHERE id=?'+suffix, (booking_id,)).fetchone()
            if not row:
                return jsonify(error='Agendamento não encontrado.'), 404
            allowed={'pending':{'confirmed','cancelled'}, 'confirmed':{'completed','cancelled'}, 'blocked':{'cancelled'}}
            if target not in allowed.get(row['status'],set()):
                return jsonify(error='Essa alteração não é permitida para o estado atual.'), 409
            if target=='completed':
                now=datetime.now(ZoneInfo(config['timezone']))
                if row['day'] > now.date().isoformat() or (row['day']==now.date().isoformat() and row['end_minute']>now.hour*60+now.minute):
                    return jsonify(error='Aguarde o término do horário para concluir.'), 409
            conn.execute('UPDATE bookings SET status=?,note=?,updated_at=? WHERE id=?', (target,note,utcnow(),booking_id))
            audit(conn,booking_id,target,app.config['ADMIN_USERNAME'],note)
        return jsonify(ok=True)

    @app.get('/api/admin/bookings/<booking_id>/history')
    @require_admin
    def history(booking_id):
        with db.transaction() as conn:
            rows=conn.execute('SELECT action,actor,note,created_at FROM audit WHERE booking_id=? ORDER BY created_at',(booking_id,)).fetchall()
        return jsonify(history=[dict(row) for row in rows])

    @app.post('/api/admin/blocks')
    @require_admin
    def block():
        body=request.get_json(silent=True) or {}
        if not isinstance(body,dict):raise ValueError('Dados inválidos.')
        profs=sorted(professionals(body.get('professional')),key=lambda p:p['id'])
        day=str(body.get('date',''));parse_day(day)
        start=minutes(body.get('start',''))
        end=1440 if body.get('end')=='24:00' else minutes(body.get('end',''))
        if end<=start:raise ValueError('O término deve ser depois do início.')
        note=str(body.get('note','Pausa / indisponibilidade')).strip()[:300]
        with db.transaction(write=True) as conn:
            for prof in profs:conn.lock(prof['id'],day)
            if any(start<b['end_minute'] and end>b['start_minute'] for prof in profs for b in busy(conn,prof['id'],day)):
                return jsonify(error='O período contém uma reserva ou bloqueio. Cancele a reserva antes de bloquear.'),409
            for prof in profs:
                bid=str(uuid.uuid4());now=utcnow()
                conn.execute('INSERT INTO bookings(id,request_key,owner_key,customer_name,customer_phone,service_id,service_name,price_cents,professional_id,professional_name,day,start_minute,end_minute,status,note,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(bid,str(uuid.uuid4()),'admin','','','block','Bloqueio manual',0,prof['id'],prof['name'],day,start,end,'blocked',note,now,now))
                audit(conn,bid,'blocked',app.config['ADMIN_USERNAME'],note)
        return jsonify(ok=True),201

    return app


def validate_settings(c):
    ZoneInfo(c['timezone'])
    assert isinstance(c['intervalMinutes'],int) and 5<=c['intervalMinutes']<=120
    assert isinstance(c['advanceDays'],int) and 1<=c['advanceDays']<=365
    assert c['professionals'] and len({p['id'] for p in c['professionals']})==len(c['professionals'])
    assert all(p['id']!='any' and p['id'] and p['name'] for p in c['professionals'])
    assert c['services'] and len({s['id'] for s in c['services']})==len(c['services'])
    assert all(s['id'] and s['name'] and isinstance(s['duration'],int) and 5<=s['duration']<=480 and isinstance(s['price'],(int,float)) and 0<=s['price']<=100000 for s in c['services'])
    for ranges in c['hours'].values():
        for start,end in ranges:
            assert minutes(start)<minutes(end)
    for day in c['closedDates']:parse_day(day)

app=create_app()

if __name__=='__main__':
    app.run(host='127.0.0.1',port=int(os.environ.get('PORT','5000')),debug=False)
