import json
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import pytest
from werkzeug.security import generate_password_hash
from app import create_app

@pytest.fixture(params=["sqlite", "postgres"])
def app(tmp_path, request):
    config=json.loads(Path('settings.json').read_text())
    config['professionals']=[{'id':'p1','name':'João'},{'id':'p2','name':'Pedro'}]
    config['hours']={str(i):[['09:00','12:00'],['13:00','20:00']] for i in range(7)}
    database_url=''
    schema=None
    if request.param=='postgres':
        if not os.environ.get('TEST_DATABASE_URL'):pytest.skip('TEST_DATABASE_URL não configurada')
        import psycopg
        from psycopg.conninfo import make_conninfo
        schema='bravo_test_'+uuid.uuid4().hex
        with psycopg.connect(os.environ['TEST_DATABASE_URL'],autocommit=True) as conn:
            conn.execute('CREATE EXTENSION IF NOT EXISTS btree_gist WITH SCHEMA public')
            conn.execute('CREATE SCHEMA '+schema)
        database_url=make_conninfo(os.environ['TEST_DATABASE_URL'],options='-csearch_path='+schema+',public')
    app=create_app({'TESTING':True,'SECRET_KEY':'test-secret-key-with-at-least-32-chars','ADMIN_PASSWORD_HASH':generate_password_hash('test-password-long'),'SQLITE_PATH':str(tmp_path/'test.sqlite3'),'DATABASE_URL':database_url,'DISABLE_RATE_LIMIT':True,'SITE_SETTINGS':config})
    app.extensions['database'].init()
    yield app
    if schema:
        import psycopg
        with psycopg.connect(os.environ['TEST_DATABASE_URL'],autocommit=True) as conn:
            conn.execute('DROP SCHEMA '+schema+' CASCADE')

@pytest.fixture
def day(app):
    return (datetime.now(ZoneInfo(app.extensions['site_settings']['timezone'])).date()+timedelta(days=1)).isoformat()

def session(client):
    return client.get('/api/session').json['csrf']

def reserve(client,day,professional='p1',time='09:00',service='corte',key=None):
    token=session(client)
    return client.post('/api/bookings',json={'name':'Cliente Teste','phone':'11999999999','date':day,'time':time,'service':service,'professional':professional,'consent':True,'requestKey':key or str(uuid.uuid4())},headers={'X-CSRF-Token':token})

def login(client):
    token=session(client)
    response=client.post('/api/admin/login',json={'username':'admin','password':'test-password-long'},headers={'X-CSRF-Token':token})
    assert response.status_code==200
    return response.json['csrf']

def slots(client,day,professional='p1',service='corte'):
    response=client.get('/api/availability',query_string={'date':day,'professional':professional,'service':service})
    assert response.status_code==200
    return response.json['slots']

def test_booking_blocks_overlap_and_cancellation_releases(app,day):
    customer=app.test_client();before=slots(customer,day)
    response=reserve(customer,day,time='09:00',service='combo')
    assert response.status_code==201
    bid=response.json['booking']['id']
    assert '09:00' not in slots(customer,day) and '10:00' not in slots(customer,day)
    assert '10:30' in slots(customer,day)
    assert reserve(app.test_client(),day,time='09:30').status_code==409
    admin=app.test_client();token=login(admin)
    assert admin.post(f'/api/admin/bookings/{bid}/status',json={'status':'cancelled','note':'Cliente cancelou'},headers={'X-CSRF-Token':token}).status_code==200
    assert slots(customer,day)==before
    listed=admin.get('/api/admin/bookings',query_string={'date':day}).json['bookings']
    assert listed[0]['status']=='cancelled'
    assert len(admin.get(f'/api/admin/bookings/{bid}/history').json['history'])==2

def test_professionals_independent_any_assigns_free(app,day):
    assert reserve(app.test_client(),day,'p1').status_code==201
    assert '09:00' in slots(app.test_client(),day,'p2')
    second=reserve(app.test_client(),day,'any')
    assert second.status_code==201 and second.json['booking']['professional']=='Pedro'
    assert '09:00' not in slots(app.test_client(),day,'any')

def test_idempotency_and_owner(app,day):
    client=app.test_client();key=str(uuid.uuid4())
    first=reserve(client,day,key=key);again=reserve(client,day,key=key)
    assert first.status_code==201 and again.status_code==200
    assert first.json['booking']['id']==again.json['booking']['id']
    assert reserve(app.test_client(),day,key=key).status_code==409

def test_concurrent_booking_one_wins(app,day):
    def task(_):return reserve(app.test_client(),day).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses=list(pool.map(task,range(2)))
    assert sorted(responses)==[201,409]

def test_concurrent_any_uses_each_professional(app,day):
    def task(_):return reserve(app.test_client(),day,'any').status_code
    with ThreadPoolExecutor(max_workers=3) as pool:
        responses=list(pool.map(task,range(3)))
    assert sorted(responses)==[201,201,409]

def test_auth_csrf_and_validation(app,day):
    client=app.test_client()
    assert client.get('/api/admin/bookings').status_code==401
    assert client.post('/api/bookings',json={}).status_code==403
    token=session(client)
    assert client.post('/api/admin/login',json={'username':'admin','password':'wrong'},headers={'X-CSRF-Token':token}).status_code==401
    assert reserve(client,'2001-01-01').status_code==409
    assert reserve(client,day,time='12:00').status_code==409
    assert reserve(client,day,service='unknown').status_code==400
    assert client.post('/api/bookings',json={'name':'A','phone':'1'},headers={'X-CSRF-Token':token}).status_code==400

def test_admin_confirm_cancel_and_no_resurrection(app,day):
    booking=reserve(app.test_client(),day).json['booking'];admin=app.test_client();token=login(admin)
    path=f"/api/admin/bookings/{booking['id']}/status"
    assert admin.post(path,json={'status':'confirmed'},headers={'X-CSRF-Token':token}).status_code==200
    assert admin.post(path,json={'status':'completed'},headers={'X-CSRF-Token':token}).status_code==409
    assert admin.post(path,json={'status':'cancelled'},headers={'X-CSRF-Token':token}).status_code==200
    assert admin.post(path,json={'status':'confirmed'},headers={'X-CSRF-Token':token}).status_code==409
    assert admin.post('/api/admin/logout',json={},headers={'X-CSRF-Token':token}).status_code==200
    assert admin.get('/api/admin/bookings').status_code==401

def test_manual_block_and_release(app,day):
    admin=app.test_client();token=login(admin)
    body={'professional':'any','date':day,'start':'13:00','end':'14:00','note':'Reunião'}
    assert admin.post('/api/admin/blocks',json=body,headers={'X-CSRF-Token':token}).status_code==201
    assert '13:00' not in slots(app.test_client(),day,'any')
    assert reserve(app.test_client(),day,'p1',time='12:30').status_code==409
    assert admin.post('/api/admin/blocks',json=body,headers={'X-CSRF-Token':token}).status_code==409
    for item in admin.get('/api/admin/bookings',query_string={'date':day}).json['bookings']:
        assert admin.post(f"/api/admin/bookings/{item['id']}/status",json={'status':'cancelled'},headers={'X-CSRF-Token':token}).status_code==200
    assert '13:00' in slots(app.test_client(),day,'any')

def test_block_cannot_override_customer(app,day):
    reserve(app.test_client(),day,'p1');admin=app.test_client();token=login(admin)
    assert admin.post('/api/admin/blocks',json={'professional':'p1','date':day,'start':'09:00','end':'10:00'},headers={'X-CSRF-Token':token}).status_code==409

def test_no_pii_public(app,day):
    booking=reserve(app.test_client(),day).json['booking']
    assert 'name' not in booking and 'phone' not in booking
    client=app.test_client()
    assert client.get('/api/admin/bookings/'+booking['id']+'/history').status_code==401
    assert client.get('/').status_code==200
    assert client.get('/static/app.js').status_code==200
    assert client.get('/api/config.js').status_code==200
    assert client.get('/admin').status_code==200

def test_persistence_after_app_restart(app,day):
    reserve(app.test_client(),day)
    new=create_app({k:app.config[k] for k in ['TESTING','SECRET_KEY','ADMIN_PASSWORD_HASH','SQLITE_PATH','DATABASE_URL','DISABLE_RATE_LIMIT']}|{'SITE_SETTINGS':app.extensions['site_settings']})
    assert '09:00' not in slots(new.test_client(),day)

def test_missing_credentials_fail_closed(tmp_path):
    missing=create_app({'SECRET_KEY':'','ADMIN_PASSWORD_HASH':'','SQLITE_PATH':str(tmp_path/'empty.sqlite3')})
    assert missing.test_client().get('/').status_code==503
    assert missing.test_client().get('/api/session').status_code==503

def test_login_limit_is_durable(app):
    app.config['DISABLE_RATE_LIMIT']=False
    client=app.test_client();token=session(client)
    for _ in range(8):
        assert client.post('/api/admin/login',json={'username':'admin','password':'wrong'},headers={'X-CSRF-Token':token}).status_code==401
    assert client.post('/api/admin/login',json={'username':'admin','password':'test-password-long'},headers={'X-CSRF-Token':token}).status_code==429

def test_booking_requires_consent_and_honeypot_empty(app,day):
    client=app.test_client();token=session(client)
    body={'name':'Teste','phone':'11999999999','service':'corte','professional':'p1','date':day,'time':'09:00','requestKey':str(uuid.uuid4()),'consent':False}
    assert client.post('/api/bookings',json=body,headers={'X-CSRF-Token':token}).status_code==400
    body['consent']=True;body['website']='spam'
    assert client.post('/api/bookings',json=body,headers={'X-CSRF-Token':token}).status_code==400

def test_health_and_password_change_invalidate_session(app):
    client=app.test_client();login(client)
    assert client.get('/api/health').json['ok'] is True
    app.config['ADMIN_PASSWORD_HASH']=generate_password_hash('another-password-long')
    assert client.get('/api/admin/bookings').status_code==401


def test_postgres_constraint_protects_direct_insert(app,day):
    if not app.extensions['database'].postgres:pytest.skip('Teste específico de PostgreSQL')
    reserve(app.test_client(),day)
    import psycopg
    with pytest.raises(psycopg.errors.ExclusionViolation):
        with app.extensions['database'].transaction(write=True) as conn:
            row=dict(conn.execute('SELECT * FROM bookings LIMIT 1').fetchone())
            row['id']=str(uuid.uuid4());row['request_key']=str(uuid.uuid4())
            keys=list(row)
            conn.execute('INSERT INTO bookings('+','.join(keys)+') VALUES('+','.join('?' for _ in keys)+')',tuple(row[k] for k in keys))
