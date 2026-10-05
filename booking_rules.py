from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo


def minutes(value):
    try:
        h, m = value.split(':')
        if len(h) != 2 or len(m) != 2 or not 0 <= int(h) < 24 or not 0 <= int(m) < 60:
            raise ValueError()
        return int(h) * 60 + int(m)
    except (ValueError, AttributeError, TypeError):
        raise ValueError('Horário inválido.')


def clock(value):
    return f'{value // 60:02d}:{value % 60:02d}'


def parse_day(value):
    try:
        parsed = date.fromisoformat(value)
        if parsed.isoformat() != value:
            raise ValueError()
        return parsed
    except (ValueError, TypeError):
        raise ValueError('Data inválida.')


def candidates(config, day, duration, now=None):
    parsed = parse_day(day)
    now = now or datetime.now(ZoneInfo(config['timezone']))
    if parsed < now.date() or parsed > now.date() + timedelta(days=config['advanceDays']) or day in config['closedDates']:
        return []
    weekday = (parsed.weekday() + 1) % 7
    slots = set()
    for start, end in config['hours'].get(str(weekday), []):
        for m in range(minutes(start), minutes(end) - duration + 1, config['intervalMinutes']):
            if parsed == now.date() and m <= now.hour * 60 + now.minute:
                continue
            slots.add(m)
    return sorted(slots)


def free_slots(config, day, duration, busy, now=None):
    return [m for m in candidates(config, day, duration, now) if not any(m < b['end_minute'] and m + duration > b['start_minute'] for b in busy)]
