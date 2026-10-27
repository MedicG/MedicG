"""Native WebRTC signaling with authenticated two-party appointment rooms."""
import os, json, time, secrets, hashlib, datetime
import hmac, base64

class VideoError(ValueError):
    pass

def window(a):
    try:
        start = int(datetime.datetime.fromisoformat(a['fecha'] + 'T' + a['hora'] + ':00-05:00').timestamp())
        return start - 1800, start + 7200
    except (KeyError, ValueError, TypeError):
        return 0, 0

def is_doctor_of(user, a):
    # Doctors, including administrators linked to a doctor profile (superadmin doctors).
    return user.get('rol') in ('medico', 'admin') and bool(user.get('medicoId')) and str(user.get('medicoId')) == str(a.get('med'))

def permitted(user, a):
    return is_doctor_of(user, a) or (user.get('rol') == 'paciente' and str(user.get('patientId')) == str(a.get('pac')))

def appointments(conn, user):
    from medicg_app import get_json_key, can_save_key
    staff = user.get('rol') == 'admin' or (user.get('rol') in ('recepcion', 'secretaria') and can_save_key(user, 'citas'))
    patients = {str(p['id']): p for p in get_json_key(conn, 'pacientes', []) if not p.get('deletedAt')}
    doctors = {str(m['id']): m for m in get_json_key(conn, 'medicos', [])}
    if user.get('rol') == 'medico':
        from medicg.doctor_scope import context, scope
        visible_ids = scope(context(conn),user)[0]
        patients = {k:v for k,v in patients.items() if k in visible_ids}
    result = []
    for a in get_json_key(conn, 'citas', []):
        if a.get('modalidad') != 'online' or str(a.get('pac')) not in patients or not (staff or permitted(user, a)):
            continue
        p = patients[str(a['pac'])]
        opens, ends = window(a)
        result.append({'id': a['id'], 'fecha': a['fecha'], 'hora': a['hora'], 'estado': a['estado'], 'paciente': (p.get('nombres', '') + ' ' + p.get('apellidos', '')).strip(), 'medico': doctors.get(str(a['med']), {}).get('nombre', ''), 'canJoin': permitted(user, a) and a['estado'] == 'Confirmada' and opens <= time.time() < ends})
    return {'appointments': sorted(result, key=lambda a: (a['fecha'], a['hora']), reverse=True), 'configured': True, 'relayConfigured': bool(os.environ.get('MEDICG_TURN_URLS') and os.environ.get('MEDICG_TURN_SECRET'))}


def authorize(conn, user, appointment_id):
    from medicg_app import get_json_key
    a = next((a for a in get_json_key(conn, 'citas', []) if str(a.get('id')) == str(appointment_id)), None)
    if a and user.get('rol') == 'medico':
        from medicg.doctor_scope import check_patient
        try:check_patient(conn,user,a.get('pac'))
        except ValueError as exc:raise VideoError(str(exc))
    if not a or a.get('modalidad') != 'online' or not permitted(user, a):
        raise VideoError('Solo el médico asignado y el paciente pueden entrar a esta consulta.')
    if not any(str(p.get('id')) == str(a.get('pac')) and not p.get('deletedAt') for p in get_json_key(conn, 'pacientes', [])):
        raise VideoError('El paciente no está activo.')
    opens, ends = window(a)
    if a.get('estado') != 'Confirmada' or not opens <= time.time() < ends:
        raise VideoError('La cita debe estar confirmada. Puedes entrar desde 30 minutos antes y hasta 2 horas después del inicio.')
    return a

def ice_servers(user):
    servers = []
    stun = [x.strip() for x in os.environ.get('MEDICG_STUN_URLS', '').split(',') if x.strip().startswith('stun:')]
    if stun:
        servers.append({'urls': stun})
    urls = [x.strip() for x in os.environ.get('MEDICG_TURN_URLS', '').split(',') if x.strip().startswith(('turn:', 'turns:'))]
    secret = os.environ.get('MEDICG_TURN_SECRET', '')
    if urls and secret:
        username = str(int(time.time()) + 10800) + ':' + str(user['id'])
        credential = base64.b64encode(hmac.new(secret.encode(), username.encode(), hashlib.sha1).digest()).decode()
        servers.append({'urls': urls, 'username': username, 'credential': credential})
    return servers

def operation(conn, user, payload):
    from medicg_app import audit
    a = authorize(conn, user, payload.get('appointmentId'))
    role = 'doctor' if is_doctor_of(user, a) else 'patient'
    other = 'patient' if role == 'doctor' else 'doctor'
    action = payload.get('action')
    if action not in ('join','poll','description','leave'):
        raise VideoError('Operación inválida.')
    sid = payload.get('sessionId', '')
    if not isinstance(sid, str) or not 16 <= len(sid) <= 80 or not all(c.isalnum() or c in '-_' for c in sid):
        raise VideoError('Identificador de sesión inválido.')
    now = int(time.time())
    fingerprint = hashlib.sha256(json.dumps([a.get(k) for k in ('id','pac','med','fecha','hora')]).encode()).hexdigest()
    row = conn.execute('select state from telehealth_native where appointment_id = ?', (str(a['id']),)).fetchone()
    state = json.loads(row['state']) if row else {}
    if state.get('fingerprint') != fingerprint:
        state = {'fingerprint': fingerprint}
    for r in ('doctor','patient'):
        if state.get(r, {}).get('seen', 0) < now - 30:
            state.pop(r, None)
    mine = state.get(role)
    if action == 'join':
        if mine and (mine['sid'] != sid or mine['uid'] != str(user['id'])):
            raise VideoError('Ya tienes esta consulta abierta en otra pestaña. Ciérrala o espera 30 segundos.')
        if not mine:
            state[role] = {'sid': sid, 'seen': now, 'uid': str(user['id'])}
            audit(conn, user, 'telehealth_join', 'citas', {'id': a['id']})
    elif not mine or mine['sid'] != sid or mine['uid'] != str(user['id']):
        raise VideoError('La sesión terminó. Vuelve a entrar a la consulta.')
    if action == 'leave':
        state.pop(role, None)
    else:
        state[role]['seen'] = now
    pair = hashlib.sha256((state.get('doctor', {}).get('sid','') + ':' + state.get('patient', {}).get('sid','')).encode()).hexdigest() if state.get('doctor') and state.get('patient') else ''
    if state.get('pair') != pair:
        state['pair'] = pair
        state.pop('offer', None); state.pop('answer', None)
    if action == 'description':
        desc = payload.get('description')
        kind = 'offer' if role == 'doctor' else 'answer'
        if not pair or payload.get('pair') != pair:
            raise VideoError('El otro participante cambió de conexión. Vuelve a entrar.')
        if not isinstance(desc, dict) or desc.get('type') != kind or not isinstance(desc.get('sdp'), str) or not 1 <= len(desc['sdp']) <= 65536 or not desc['sdp'].startswith('v=0'):
            raise VideoError('Descripción de conexión inválida.')
        if kind == 'answer' and not state.get('offer'):
            raise VideoError('Espera la conexión del médico.')
        state[kind] = {'type':kind,'sdp':desc['sdp']}
    conn.execute('delete from telehealth_native where expires_at < ?', (now,))
    conn.execute('insert into telehealth_native(appointment_id,state,expires_at) values(?,?,?) on conflict(appointment_id) do update set state=excluded.state,expires_at=excluded.expires_at', (str(a['id']),json.dumps(state),now+35))
    result = {'role':role,'peerPresent':bool(state.get(other)), 'pair':pair, 'description':state.get('answer' if role=='doctor' else 'offer'), 'expiresAt':window(a)[1]}
    if action == 'join':
        result['iceServers'] = ice_servers(user)
    return result
