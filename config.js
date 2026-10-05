/* Personalize este arquivo para cada cliente. Nenhum dado secreto deve ficar aqui. */
window.SITE_CONFIG = {
  brand: 'STYLE',
  tagline: 'BARBEARIA & ESTILO',
  title: 'Style — Barbearia & estilo',
  description: 'Cortes, barba e cuidado masculino. Solicite seu horário pelo WhatsApp.',
  headline: 'Mais que um corte.\nSeu melhor estilo.',
  intro: 'Corte preciso, barba alinhada e um tempo só seu. O cuidado que faz diferença, do primeiro detalhe ao último acabamento.',
  about: 'Um espaço para desacelerar, cuidar de você e sair pronto para o próximo compromisso. Aqui, seu estilo tem lugar.',
  whatsapp: '5514988094123', // Número real com 55 + DDD + número, somente dígitos.
  address: 'Rua dos Alfeneiros, nº 4', // Endereço real. Se vazio, não será exibido.
  city: 'Bauru',
  mapsUrl: '', // Link https:// do Google Maps, opcional.
  colors: { background: '#171d19', cream: '#f2ede4', accent: '#bc8962' },
  services: [
    { id: 'corte', name: 'Corte masculino', description: 'Tesoura ou máquina, degradê e acabamento. Um corte pensado para você.', price: 45, duration: 45 },
    { id: 'combo', name: 'Corte + barba', description: 'Visual renovado por inteiro. Corte personalizado e barba com toalha quente.', price: 75, duration: 75, featured: true },
    { id: 'barba', name: 'Barba completa', description: 'Desenho, alinhamento e finalização para uma barba bem cuidada.', price: 35, duration: 30 }
  ],
  professionals: ['Sem preferência', 'Abnner'], // Ex.: ['Sem preferência', 'João', 'Pedro']
  timezone: 'America/Sao_Paulo',
  intervalMinutes: 30,
  advanceDays: 60,
  /* Dias: 0 domingo, 1 segunda, ..., 6 sábado. Inclua intervalos para almoço. */
  hours: { 0: [], 1: [['09:00','20:00']], 2: [['09:00','20:00']], 3: [['09:00','20:00']], 4: [['09:00','20:00']], 5: [['09:00','20:00']], 6: [['09:00','18:00']] },
  closedDates: [] // Ex.: ['2026-12-25']; datas no formato AAAA-MM-DD.
};
