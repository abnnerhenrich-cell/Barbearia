const assert=require('node:assert/strict');const S=require('./schedule.js');
const c={timezone:'America/Sao_Paulo',intervalMinutes:30,advanceDays:60,closedDates:[],hours:{0:[],1:[['09:00','12:00'],['13:00','20:00']],6:[['09:00','18:00']]}};
const now=new Date('2026-10-05T15:05:00Z'); // segunda, 12:05 no estabelecimento.
assert.equal(S.dateInfo(now,c.timezone).date,'2026-10-05');
assert.deepEqual(S.slots(c,'2026-10-04',30,now),[]);
assert.deepEqual(S.slots(c,'2026-10-11',30,now),[]);
const today=S.slots(c,'2026-10-05',75,now);assert.equal(today[0],'13:00');assert.equal(today.at(-1),'18:30');
assert(!today.includes('19:00'));assert(!today.includes('12:30'));
assert.deepEqual(S.slots({...c,closedDates:['2026-10-05']},'2026-10-05',30,now),[]);
assert.deepEqual(S.slots(c,'2027-01-04',30,now),[]);
const morning=S.slots(c,'2026-10-05',75,new Date('2026-10-05T11:00:00Z'));assert(morning.includes('10:30'));assert(!morning.includes('11:00'));assert(!morning.includes('11:30'));
assert.deepEqual(S.slots(c,'2026-02-30',30,now),[]);
assert.deepEqual(S.slots(c,'2026-10-05',-1,now),[]);
assert.equal(S.dateInfo(new Date('2026-10-06T01:00:00Z'),c.timezone).date,'2026-10-05');
console.log('11 verificações de datas, horários, pausas e fuso passaram.');
