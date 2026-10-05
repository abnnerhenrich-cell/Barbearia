# BRAVO — Versão comercial 1.0

Template de site para barbearias com catálogo, preços, equipe e solicitação de horário pelo WhatsApp. HTML, CSS e JavaScript, sem dependências, banco de dados ou mensalidade de software obrigatória. O serviço de hospedagem e eventual domínio são contratados separadamente.

## Instalação

1. Extraia o ZIP.
2. Edite `config.js` com os dados reais do cliente.
3. Abra `index.html` no navegador para conferir.
4. Envie o conteúdo desta pasta para a raiz do repositório/hospedagem, mantendo a pasta `assets`.

Para GitHub Pages, use a branch que contém `index.html` na pasta raiz. Documentação oficial:
https://docs.github.com/pt/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site

Não é necessário rodar npm, fazer build ou criar variáveis de ambiente. Não envie o ZIP fechado para servir o site.

## Personalização em config.js

- `brand`, `tagline`, `title`, `description`: nome e identificação.
- `headline`, `intro`, `about`: textos principais.
- `whatsapp`: número real, 55 + DDD + número, somente dígitos. Vem vazio para não direcionar clientes a um telefone fictício.
- `address`, `city`, `mapsUrl`: localização real. Endereço vazio fica oculto.
- `colors`: três cores, em hexadecimal.
- `services`: nome, descrição, preço numérico, duração em minutos, identificador único e destaque opcional. Cards, opções e totais usam esses mesmos dados.
- `professionals`: nomes da equipe. O padrão é “Sem preferência”.
- `hours`: horários por dia da semana. Domingo é 0 e sábado é 6. Exemplo de pausa para almoço: `[['09:00','12:00'],['13:00','19:00']]`.
- `closedDates`: feriados/fechamentos, no formato `AAAA-MM-DD`.
- `intervalMinutes`: intervalo entre opções de início (padrão: 30).
- `advanceDays`: prazo máximo para solicitar (padrão: 60 dias).
- `timezone`: fuso do estabelecimento (padrão: America/Sao_Paulo).

Valores iniciais de serviços e horários são um modelo e precisam de validação pelo cliente. BRAVO é uma marca de apresentação, sem verificação de registro ou exclusividade.

## Conteúdo e arquivos

- `index.html`: estrutura do site.
- `styles.css`: aparência e layout responsivo.
- `config.js`: configurações por cliente.
- `schedule.js`: regras de datas e horários.
- `app.js`: catálogo, interação e integração com WhatsApp.
- `assets/barbearia.jpg`: foto local usada na apresentação inicial.
- `GUIA-DE-VENDA.md`: escopo e roteiro de entrega.
- `test-schedule.cjs`: testes das regras de horários, executáveis com `node test-schedule.cjs`.
- `.nojekyll`: publicação de arquivos estáticos.

## Escopo real

É um site de apresentação com solicitação pelo WhatsApp. Ele não controla horários ocupados, não registra reservas, não tem painel administrativo, pagamento, login ou envio automático de mensagens. Duas pessoas podem solicitar o mesmo horário; o estabelecimento confirma e organiza sua agenda no atendimento. As opções apenas respeitam expediente, duração, pausas, datas fechadas e horário atual.

O visitante revisa e envia a mensagem no WhatsApp. O formulário não salva dados pessoais em servidor ou armazenamento do navegador. A seção de privacidade descreve este comportamento e deve ser revista se a implantação acrescentar ferramentas de análise, formulários externos ou outros tratamentos de dados.

## Verificação

Sintaxe de todos os scripts; testes de horário passado, domingo fechado, almoço, duração do serviço, fechamento por data, limite de antecedência e fuso. Presença de arquivos e componentes verificada. Revisão visual em navegador não foi realizada neste ambiente; confira em celular e desktop antes da entrega ao cliente.
