/* Regras da solicitação de horário. Não representa disponibilidade de uma agenda. */
(function (root) {
  const minutes = time => {const m=/^(\d{2}):(\d{2})$/.exec(time);if(!m||+m[1]>23||+m[2]>59)return NaN;return +m[1]*60 + +m[2];};
  const dateInfo = (now, timezone) => {
    const parts = Object.fromEntries(new Intl.DateTimeFormat('en-CA', {timeZone:timezone,year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(now).map(p=>[p.type,p.value]));
    return {date:`${parts.year}-${parts.month}-${parts.day}`,minute:+parts.hour*60 + +parts.minute};
  };
  const addDays = (date, count) => {const d=new Date(date+'T12:00:00Z');d.setUTCDate(d.getUTCDate()+count);return d.toISOString().slice(0,10);};
  function slots(config, date, duration, now=new Date()) {
    if(!/^\d{4}-\d{2}-\d{2}$/.test(date)||!Number.isFinite(duration)||duration<=0)return [];
    const current=dateInfo(now,config.timezone);if(date<current.date||date>addDays(current.date,config.advanceDays)||config.closedDates.includes(date))return [];
    const d=new Date(date+'T12:00:00Z');if(isNaN(d)||d.toISOString().slice(0,10)!==date)return [];
    const result=new Set();const interval=Number(config.intervalMinutes);if(!Number.isFinite(interval)||interval<=0)return [];
    for(const [start,end] of config.hours[d.getUTCDay()]||[]){const first=minutes(start),last=minutes(end);if(!Number.isFinite(first)||!Number.isFinite(last))continue;for(let m=first;m+duration<=last;m+=interval){if(date===current.date&&m<=current.minute)continue;result.add(`${String(Math.floor(m/60)).padStart(2,'0')}:${String(m%60).padStart(2,'0')}`);}}
    return [...result].sort();
  }
  const api={minutes,dateInfo,addDays,slots};root.BravoSchedule=api;if(typeof module!=='undefined')module.exports=api;
})(typeof window!=='undefined'?window:globalThis);
