"""Read-only window evidence. A timed Tado pause never confirms physical closure."""
from copy import deepcopy
from datetime import datetime
import math
import time

WINDOW_POLICY = 1
RECOVERY_SECONDS = 900
TADO_SUFFIXES = ('openWindowDetected', 'openWindow.detectedTime', 'openWindow.expiry',
                 'openWindow.remainingTimeInSeconds')


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def fresh(state, max_age, now):
    state = state if isinstance(state, dict) else {}
    value, stamp = state.get('val'), state.get('ts')
    if value is None:
        return None, 'unavailable', None
    if state.get('q') or state.get('ack') is not True or not number(stamp) or stamp <= 0 or stamp/1000 > now+60:
        return None, 'error', None
    stamp /= 1000
    return (None, 'stale', stamp) if now-stamp > max_age else (value, 'valid', stamp)


def unknown(reason='no_closed_evidence', quality='unavailable'):
    return {'state': 'unknown', 'quality': quality, 'source': 'unconfigured',
            'updated_at': None, 'valid_until': None, 'eligible_after': None,
            'training_allowed': False, 'reason': reason, 'contacts': []}


def refresh(window, now=None, connected=True):
    now = time.time() if now is None else now
    result = deepcopy(window) if isinstance(window, dict) else unknown()
    if not connected or (result.get('quality') == 'valid' and
                         (not number(result.get('valid_until')) or now > result['valid_until'])):
        result.update(state='unknown', quality='stale', training_allowed=False, reason='stale_window_evidence')
    elif result.get('state') == 'closed' and result.get('quality') == 'valid':
        allowed = number(result.get('eligible_after')) and now >= result['eligible_after']
        result.update(training_allowed=bool(allowed), reason='closed' if allowed else 'recovery')
    else:
        result['training_allowed'] = False
    return result


def observe(tado, configured_contacts, states, now=None):
    """Pure interpretation of already read states; this module has no device API."""
    now = time.time() if now is None else now
    result = unknown()
    detected, quality, stamp = fresh(tado.get('openWindowDetected'), 900, now)
    if quality == 'valid' and type(detected) is not bool:
        detected, quality = None, 'error'
    result['tado_detection'] = {'value': detected, 'quality': quality, 'updated_at': stamp}
    positive = [stamp+900] if quality == 'valid' and detected is True else []
    remaining, rq, rt = fresh(tado.get('openWindow.remainingTimeInSeconds'), 900, now)
    result['tado_pause'] = {'remaining_seconds': remaining if rq == 'valid' and number(remaining) else None,
                            'quality': rq, 'updated_at': rt}
    if rq == 'valid' and number(remaining) and 0 < remaining <= 86400:
        until = rt+remaining
        if until > now:
            positive.append(min(rt+900, until))
    timing = []
    for key in ('openWindow.detectedTime', 'openWindow.expiry'):
        value, q, ts = fresh(tado.get(key), 900, now)
        try:
            date = datetime.fromisoformat(value.replace('Z', '+00:00')) if q == 'valid' and isinstance(value, str) else None
            timing.append((date.timestamp(), ts) if date and date.tzinfo else None)
        except (ValueError, OverflowError):
            timing.append(None)
    if all(timing):
        start, end = timing[0][0], timing[1][0]
        result['tado_pause'].update(detected_at=start, expires_at=end)
        if start <= now+60 and now < end <= now+86400 and start < end:
            positive.append(min(end, timing[0][1]+900, timing[1][1]+900))

    contacts = []
    if configured_contacts:
        if not isinstance(configured_contacts, list):
            result.update(source='contact', quality='error', reason='invalid_contact_config')
            return result
        for config in configured_contacts:
            item = {'state': 'unknown', 'quality': 'error', 'updated_at': None}
            contacts.append(item)
            if not isinstance(config, dict) or not isinstance(config.get('id'), str) or type(config.get('open_value')) is not bool:
                continue
            item['id'] = config['id']
            age = config.get('max_age_seconds', 86400)
            if not number(age) or not 60 <= age <= 604800:
                continue
            value, q, ts = fresh(states.get(config['id']), age, now)
            item.update(quality=q, updated_at=ts)
            if q != 'valid':
                continue
            if type(value) is not bool:
                item['quality'] = 'error'
                continue
            item.update(state='open' if value == config['open_value'] else 'closed', valid_until=ts+age)
            lc = states[config['id']].get('lc')
            changed = lc/1000 if number(lc) and 0 < lc/1000 <= now+60 else ts
            item['eligible_after'] = changed+RECOVERY_SECONDS
            if 'availability_id' in config:
                if not isinstance(config['availability_id'], str) or not config['availability_id']:
                    item.update(state='unknown', quality='error')
                    continue
                available, aq, at = fresh(states.get(config['availability_id']), age, now)
                if aq != 'valid' or available is not True:
                    item.update(state='unknown', quality=aq if aq != 'valid' else 'unavailable')
                else:
                    item['valid_until'] = min(item['valid_until'], at+age)
        result.update(source='contact', contacts=contacts)
        valid_open = [c for c in contacts if c['quality'] == 'valid' and c['state'] == 'open']
        if valid_open:
            result.update(state='open', quality='valid', updated_at=max(c['updated_at'] for c in valid_open),
                          valid_until=max(c['valid_until'] for c in valid_open), reason='contact_open')
        elif all(c['quality'] == 'valid' and c['state'] == 'closed' for c in contacts):
            result.update(state='closed', quality='valid', updated_at=min(c['updated_at'] for c in contacts),
                          valid_until=min(c['valid_until'] for c in contacts),
                          eligible_after=max(c['eligible_after'] for c in contacts))
        else:
            result.update(quality='stale' if any(c['quality'] == 'stale' for c in contacts) else 'unavailable', reason='contact_unknown')
    if positive:
        result.update(state='open', quality='valid', source='tado_detection', updated_at=now,
                      valid_until=max(positive), reason='tado_detected_open')
    # False/null/expired Tado detection does not change unknown into closed.
    return refresh(result, now)


def exclusion(window, now):
    """Return a training exclusion reason, preserving events inside reduced buckets."""
    if not isinstance(window, dict):
        return 'unknown'
    merged = window.get('excluded_in_bucket', [])
    for reason in ('open', 'unknown', 'recovery'):
        if reason in merged:
            return reason
    current = refresh(window, now)
    if current.get('state') == 'open' and current.get('quality') == 'valid':
        return 'open'
    if current.get('state') != 'closed' or current.get('quality') != 'valid' or current.get('source') != 'contact':
        return 'unknown'
    return None if current.get('training_allowed') is True else 'recovery'
