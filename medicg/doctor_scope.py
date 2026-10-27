"""Server-side specialty scope for medical accounts."""
import unicodedata

def norm(value):
 return unicodedata.normalize('NFKD',str(value or '')).encode('ascii','ignore').decode().strip().casefold()

def specialties(doctor):
 return list(dict.fromkeys(s for s in [doctor.get('esp',''),doctor.get('esp2',''),doctor.get('esp3',''),doctor.get('esp4','')] if isinstance(s,str) and s.strip()))

def scope(data,user):
 doctor=next((m for m in data.get('medicos',[]) if str(m.get('id'))==str(user.get('medicoId')) and m.get('estado')!='inactivo'),{})
 allowed={norm(s) for s in specialties(doctor)}
 ids={str(p.get('id')) for p in data.get('pacientes',[]) if norm(p.get('esp')) in allowed}
 ids.update(str(c.get('pac')) for c in data.get('citas',[]) if norm(c.get('esp')) in allowed and norm(c.get('estado')) not in ('cancelada','cancelado','anulada','anulado'))
 active={str(p['id']) for p in data.get('pacientes',[]) if not p.get('deletedAt')}
 return ids & active,allowed

def context(conn):
 from medicg_app import get_json_key
 return {k:get_json_key(conn,k,[]) or [] for k in ('pacientes','medicos','citas')}

def filter_data(data,user):
 ids,allowed=scope(data,user)
 result=dict(data)
 result['pacientes']=[p for p in data.get('pacientes',[]) if str(p.get('id')) in ids]
 for key in ('notas','recetas','archivosClinicos'):
  result[key]={k:v for k,v in (data.get(key) or {}).items() if str(k) in ids}
 result['citas']=[c for c in data.get('citas',[]) if str(c.get('med'))==str(user.get('medicoId')) and str(c.get('pac')) in ids]
 for key in ('facturas','cotizaciones','cajas'):
  result[key]=[]
 # Service selections may contain negotiated prices; doctors receive clinical concepts only.
 result['citas']=[{**c,'serviciosSolicitados':[{k:v for k,v in item.items() if k in ('id','kind','nombre','quantity')} for item in c.get('serviciosSolicitados',[])]} for c in result['citas']]
 return result

def merge_write(conn,user,key,value):
 from medicg_app import get_json_key
 ids,allowed=scope(context(conn),user)
 current=get_json_key(conn,key,{} if key in ('notas','recetas','archivosClinicos') else []) or ({} if key in ('notas','recetas','archivosClinicos') else [])
 if key in ('notas','recetas','archivosClinicos'):
  if any(str(k) not in ids for k in value):raise ValueError('No puedes modificar historias de otra especialidad.')
  return {**{k:v for k,v in current.items() if str(k) not in ids},**value}
 if key=='pacientes':raise ValueError('Los médicos no pueden registrar ni editar pacientes.')
 return value

def check_patient(conn,user,patient_id):
 if user.get('rol')!='medico':return
 if str(patient_id) not in scope(context(conn),user)[0]:raise ValueError('Paciente fuera de tus especialidades.')
