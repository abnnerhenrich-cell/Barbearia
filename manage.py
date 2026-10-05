"""Configuração local e inicialização do banco sem expor segredos no console."""
import argparse
import getpass
import json
import secrets
from pathlib import Path
from werkzeug.security import generate_password_hash

parser=argparse.ArgumentParser(description='Configurar e inicializar BRAVO')
parser.add_argument('action',choices=['setup','init-db','credentials','anonymize'])
args=parser.parse_args()
if args.action=='credentials':
    # Única ação que imprime credenciais geradas: uso local pelo proprietário.
    password=getpass.getpass('Nova senha do painel (mínimo 12 caracteres): ')
    if len(password)<12:raise SystemExit('Use pelo menos 12 caracteres.')
    if password!=getpass.getpass('Repita a senha: '):raise SystemExit('Senhas diferentes.')
    print('Copie estes valores somente nas variáveis de ambiente da sua hospedagem:')
    print('SECRET_KEY='+secrets.token_hex(32))
    print('ADMIN_PASSWORD_HASH='+generate_password_hash(password))
elif args.action=='anonymize':
    from app import app
    booking_id=input('ID completo do agendamento encerrado: ').strip()
    with app.extensions['database'].transaction(write=True) as conn:
        row=conn.execute('SELECT status FROM bookings WHERE id=?',(booking_id,)).fetchone()
        if not row:raise SystemExit('Registro não encontrado.')
        if row['status'] not in ('cancelled','completed'):raise SystemExit('Encerre ou cancele o atendimento primeiro.')
        if input('Digite ANONIMIZAR para remover nome, telefone e observações: ')!='ANONIMIZAR':raise SystemExit('Operação não realizada.')
        conn.execute("UPDATE bookings SET customer_name='Dados removidos',customer_phone='',note='',owner_key='' WHERE id=?",(booking_id,))
        conn.execute("UPDATE audit SET note='' WHERE booking_id=?",(booking_id,))
    print('Dados pessoais e observações removidos. O registro operacional foi preservado.')
elif args.action=='setup':
    path=Path(__file__).with_name('.env')
    if path.exists():
        raise SystemExit('.env já existe. Edite-o ou remova-o conscientemente antes de repetir.')
    username=input('Usuário do painel [admin]: ').strip() or 'admin'
    password=getpass.getpass('Senha do painel (mínimo 12 caracteres): ')
    if len(password)<12:raise SystemExit('Use pelo menos 12 caracteres.')
    if password!=getpass.getpass('Repita a senha: '):raise SystemExit('Senhas diferentes.')
    database=getpass.getpass('DATABASE_URL do Neon (Enter para SQLite local): ').strip()
    lines={'APP_ENV':'development','SECRET_KEY':secrets.token_hex(32),'ADMIN_USERNAME':username,'ADMIN_PASSWORD_HASH':generate_password_hash(password),'DATABASE_URL':database,'BUSINESS_WHATSAPP':''}
    path.write_text('\n'.join(k+'='+json.dumps(v) for k,v in lines.items())+'\n', encoding='utf-8')
    try:path.chmod(0o600)
    except OSError:pass
    print('Arquivo .env criado. Não envie para o GitHub. Próximo passo: python manage.py init-db')
else:
    from app import app
    app.extensions['database'].init()
    print('Banco inicializado. As tabelas existentes foram preservadas.')
