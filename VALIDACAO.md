# Validação da entrega

## Verificado

15 testes automatizados passaram com SQLite local, usando requisições reais ao aplicativo Flask pelo cliente de testes:

- Reserva salva e período bloqueado conforme a duração.
- Cancelamento libera o período e mantém o histórico.
- Profissionais independentes e atribuição sem preferência.
- Reenvio com a mesma chave retorna a mesma reserva.
- Duas reservas simultâneas: uma aceita, outra recusada.
- Três reservas sem preferência para dois profissionais: duas aceitas, uma recusada.
- Login obrigatório, senha incorreta, sessão e proteção CSRF.
- Confirmação, cancelamento, conclusão após término e proibição de reativação.
- Bloqueios manuais e liberação.
- Proteção de reservas existentes contra bloqueios.
- Dados pessoais não expostos nos endpoints públicos.
- Persistência após recriação do aplicativo.
- Falta de credenciais impede a abertura do sistema.
- Limite de tentativas de login persistente.
- Consentimento, campo de proteção e invalidação da sessão após troca de senha.

A sintaxe Python e JavaScript, a estrutura HTML, os identificadores e os caminhos dos arquivos locais foram conferidos.

## PostgreSQL e implantação

O código usa transações, locks por profissional/data e uma restrição de exclusão no PostgreSQL, baseada em intervalos sem sobreposição. Os mesmos testes foram preparados para PostgreSQL e há um teste adicional da restrição diretamente no banco.

Neste ambiente não foi possível iniciar um servidor PostgreSQL. Esses testes ficaram sem execução; nenhuma conexão com a conta Neon do usuário ou publicação na Vercel foi realizada. Não foi realizada revisão visual em navegador.

Antes de liberar o site ao público, execute a inicialização em um banco Neon dedicado e faça a sequência de reserva, conflito e cancelamento descrita em INICIAR-AQUI.md.

Para executar a suíte também em PostgreSQL, use um banco **exclusivo de testes** e configure `TEST_DATABASE_URL` no ambiente. O usuário de teste precisa poder criar a extensão btree_gist e schemas. A suíte cria e remove schemas temporários com prefixo bravo_test_; nunca configure essa variável com o banco de produção.

Documentação técnica consultada:
- https://vercel.com/docs/frameworks/backend/flask
- https://www.postgresql.org/docs/current/rangetypes.html
- https://www.psycopg.org/psycopg3/docs/advanced/prepare.html
