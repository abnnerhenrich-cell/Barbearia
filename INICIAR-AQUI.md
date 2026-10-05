# BRAVO — Sistema de agendamento 2.0

Esta versão substitui o site estático. Agora a reserva é salva no banco e bloqueia o período por profissional. O painel fica em `/admin`.

## O que já funciona

- Catálogo e preços vindos do mesmo arquivo de configuração.
- Reserva persistente com nome e telefone do cliente.
- Disponibilidade considerando duração, profissional, expediente, almoço, feriados e bloqueios.
- Sem preferência: atribui um profissional livre e informa qual foi escolhido.
- Reserva pendente já bloqueia o horário.
- Proteção transacional contra duas reservas sobrepostas.
- Painel com login: agenda por data/profissional/status, confirmação, cancelamento, conclusão, bloqueio de períodos e histórico.
- Cancelamento libera o período imediatamente, preservando o registro.
- Botão para o barbeiro abrir uma mensagem de confirmação ou cancelamento no WhatsApp.

O WhatsApp não envia mensagens sozinho. O barbeiro clica, revisa e envia. Não há pagamento online nem login de cliente. O cancelamento do cliente é solicitado ao estabelecimento, que cancela pelo painel.

## Caminho rápido: GitHub + Neon + Vercel

### 1. Personalize o estabelecimento

Edite `settings.json`. Ele substitui o antigo `config.js`; não copie o config.js antigo para esta versão.

Preencha nome, WhatsApp real (`55` + DDD + número), endereço, serviços, preços, durações e equipe. Exemplo:

```json
"professionals": [
  {"id": "joao", "name": "João"},
  {"id": "pedro", "name": "Pedro"}
]
```

O `id` deve ser único e estável. Se renomear o profissional, mantenha o ID. Registros anteriores preservam o nome e o preço da época da reserva. Não troque o ID de alguém com reservas futuras. O expediente informado vale para a equipe; diferenças individuais podem ser tratadas com bloqueios no painel.

### 2. Prepare o banco Neon

1. Crie um banco PostgreSQL dedicado para esta barbearia.
2. Abra o SQL Editor desse banco.
3. Cole e execute o arquivo `setup-neon.sql` completo.
4. Copie a connection string fornecida pelo Neon, com SSL, para usar em `DATABASE_URL`.

O script cria tabelas e a regra de bloqueio de sobreposição. Não use o banco do Veterani para este projeto. Use um banco por cliente/barbearia. A inicialização é repetível e não apaga dados existentes.

### 3. Gere a senha do painel

No seu computador, com Python 3.12 ou superior, abra um terminal na pasta extraída:

```bash
python -m pip install -r requirements.txt
python manage.py credentials
```

O comando pede uma senha de pelo menos 12 caracteres sem mostrar o que você digita. Ele gera dois valores para copiar nas variáveis da Vercel: `SECRET_KEY` e `ADMIN_PASSWORD_HASH`. Guarde a senha que você escolheu. Não cole os valores gerados no GitHub nem no chat.

### 4. Envie para o GitHub

Envie **todo o conteúdo desta pasta** para a raiz de um novo repositório, incluindo `app.py`, `requirements.txt`, `vercel.json`, `settings.json`, `templates` e `public`.

Este é um aplicativo Flask com servidor. **GitHub Pages não executa esta versão.** O GitHub guarda o código e a Vercel executa o site e a API.

### 5. Configure e publique na Vercel

Importe o repositório na Vercel como projeto Flask. Mantenha a pasta raiz do projeto e o Build Command padrão. Não configure comando npm nem saída estática.

Cadastre as variáveis de ambiente de produção:

| Variável | Valor |
| --- | --- |
| `APP_ENV` | `production` |
| `DATABASE_URL` | connection string do banco Neon dedicado |
| `SECRET_KEY` | valor gerado pelo comando credentials |
| `ADMIN_USERNAME` | usuário escolhido, por exemplo `admin` |
| `ADMIN_PASSWORD_HASH` | valor gerado pelo comando credentials |
| `BUSINESS_WHATSAPP` | opcional: telefone real, substitui o settings.json |

Publique o projeto. Se alterar uma variável depois, faça novo deploy para aplicá-la. Não coloque valores secretos em arquivos do repositório.

### 6. Confira a implantação

1. Abra `https://SEU-DOMINIO/api/health`: deve responder `{"ok": true}`.
2. Abra `https://SEU-DOMINIO/admin` e entre com usuário e senha escolhidos.
3. Faça uma reserva de teste pelo site.
4. Confira que o mesmo período desaparece para aquele profissional.
5. Cancele no painel e confira a liberação.
6. Verifique o funcionamento no seu celular e no computador antes de entregar ao cliente.

Use um banco separado para previews e testes. Nunca aponte uma demonstração pública ou preview de desenvolvimento para a agenda real do cliente.

## Testar no computador sem Neon

```bash
python -m pip install -r requirements.txt
python manage.py setup
python manage.py init-db
python app.py
```

No `setup`, deixe DATABASE_URL vazio para usar SQLite local. Abra http://127.0.0.1:5000 e http://127.0.0.1:5000/admin.

O comando cria `.env` e você escolhe usuário e senha. O banco local fica em `local.sqlite3`. Esses arquivos são ignorados pelo Git. **SQLite é só para desenvolvimento; na Vercel o sistema exige PostgreSQL.**

## Recuperar ou trocar a senha

Execute `python manage.py credentials`, escolha uma nova senha e atualize `SECRET_KEY` e `ADMIN_PASSWORD_HASH` na Vercel. Faça novo deploy. A troca encerra as sessões antigas. O usuário pode ser alterado em `ADMIN_USERNAME`.

## Como cancelar

1. No painel, selecione a data da reserva.
2. Localize o cliente.
3. Clique em Cancelar, registre uma observação se quiser e confirme.
4. O período já está liberado. Para avisar o cliente, clique em Avisar cancelamento e envie a mensagem pelo WhatsApp.

Registros cancelados não podem ser reativados; faça uma nova reserva para garantir uma nova verificação de disponibilidade. Atendimento concluído mantém o registro e pode ser concluído somente após o horário final. Os valores concluídos no painel são a soma dos preços dos serviços, não uma confirmação de pagamento recebido.

## Reservas pendentes e bloqueios

Pendentes continuam bloqueados até confirmação ou cancelamento pelo responsável. Não há expiração automática. Verifique a agenda regularmente. Para pausa ou folga, use Bloquear período. Para liberar, cancele o bloqueio na lista. O sistema recusa bloquear sobre reservas existentes: combine o cancelamento ou a remarcação primeiro.

O catálogo, equipe e expediente são alterados em `settings.json` e aplicados por novo deploy. Evite editar preços, durações, expediente e IDs durante uma atualização gradual com reservas em andamento; confira os agendamentos futuros após mudanças.

## Privacidade e conservação dos dados

O administrador controla quem conhece a senha do painel. Use uma credencial por estabelecimento. O responsável define o prazo de retenção e responde às solicitações dos clientes.

Para remover nome, telefone e observações de um agendamento encerrado, configure localmente o `.env` com o mesmo banco e execute:

```bash
python manage.py anonymize
```

Informe o ID completo da reserva (campo `id` na resposta autenticada da agenda) e confirme conscientemente. A ação preserva apenas o registro operacional; backups do banco seguem a política do provedor. Não há botão público de exclusão nem ferramenta que zera a agenda automaticamente.

## Arquivos e verificação

A imagem original do site foi mantida em `public/static/assets/barbearia.jpg`. Referência da foto: https://images.unsplash.com/photo-1503951914875-452162b0f3f1.

O projeto inclui testes automatizados das reservas, acesso ao painel, cancelamento, bloqueios, persistência, reenvio de pedidos, proteção CSRF e concorrência. Para rodar:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

A implantação na sua conta Neon/Vercel não foi realizada nesta entrega. Os testes são documentados em `VALIDACAO.md`.

Referências oficiais utilizadas:
- https://vercel.com/docs/frameworks/backend/flask
- https://www.postgresql.org/docs/current/rangetypes.html
