"""Reception of walk-in consultations; does not reserve a scheduled time slot."""
import datetime, uuid

def register(conn,user,payload):
 from medicg_app import get_json_key,set_json_key,audit
 from medicg.doctor_scope import context, filter_data, specialties
 from medicg.cash import CashError, effective_unit
 try:request_id=str(uuid.UUID(str(payload.get('requestId'))))
 except (ValueError,TypeError):raise CashError('Identificador de registro inválido.')
 citas=get_json_key(conn,'citas',[]) or []
 existing=next((c for c in citas if c.get('walkinRequest')==request_id and c.get('registeredBy')==user['id']),None)
 if existing:return {'ok':True,'appointment':existing,'appointments':filter_data({**context(conn),'citas':citas},user)['citas'] if user.get('rol')=='medico' else citas}
 patient=next((p for p in get_json_key(conn,'pacientes',[]) if str(p.get('id'))==str(payload.get('patientId')) and not p.get('deletedAt')),None)
 doctor=next((m for m in get_json_key(conn,'medicos',[]) if str(m.get('id'))==str(payload.get('doctorId')) and m.get('estado')!='inactivo'),None)
 if user.get('rol')=='medico':
  from medicg.doctor_scope import check_patient
  try:check_patient(conn,user,payload.get('patientId'))
  except ValueError as exc:raise CashError(str(exc))
 if not patient or not doctor:raise CashError('Selecciona un paciente activo y un médico.')
 if user.get('rol')=='medico' and str(user.get('medicoId'))!=str(doctor['id']):raise CashError('Solo puedes registrar tus propias consultas.')
 specialty=payload.get('specialty') or doctor.get('esp','General')
 if specialty not in specialties(doctor):raise CashError('Selecciona una especialidad del médico.')
 reason=payload.get('reason','')
 if not isinstance(reason,str) or not 3<=len(reason.strip())<=2000:raise CashError('Escribe el motivo de consulta (3 a 2000 caracteres).')
 rows=payload.get('items',[])
 if not isinstance(rows,list) or not 1<=len(rows)<=100:raise CashError('Agrega entre 1 y 100 servicios o exámenes.')
 items=[]
 for row in rows:
  if not isinstance(row,dict) or row.get('kind') not in ('servicio','examen'):raise CashError('Concepto inválido.')
  catalog=get_json_key(conn,'servicios' if row['kind']=='servicio' else 'examenes',[])
  item=next((i for i in catalog if str(i.get('id'))==str(row.get('id'))),None)
  q=row.get('quantity')
  if not item or isinstance(q,bool) or not isinstance(q,int) or not 1<=q<=1000:raise CashError('Revisa el concepto y su cantidad.')
  price, discount, catalog_unit, unit = effective_unit(item, row['kind'], row, user)
  clean={'kind':row['kind'],'id':item['id'],'quantity':q,'nombre':item['nombre'],'precioCatalogoNeto':float(catalog_unit)}
  if 'unitPrice' in row:clean['unitPrice']=float(unit)
  items.append(clean)
 stamp=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-5))).isoformat(timespec='seconds')
 try:
  date=datetime.date.fromisoformat(payload.get('date',stamp[:10])).isoformat()
 except (ValueError,TypeError):raise CashError('Selecciona una fecha válida.')
 raw_time=payload.get('time',stamp[11:16])
 try:
  if not isinstance(raw_time,str) or len(raw_time)!=5 or raw_time[2]!=':':raise ValueError()
  attention_time=datetime.datetime.strptime(raw_time,'%H:%M').strftime('%H:%M')
 except (ValueError,TypeError):raise CashError('Selecciona una hora válida.')
 ids=get_json_key(conn,'nextIds',{}) or {};number=max(int(ids.get('cita') or 1),max((int(c.get('id') or 0) for c in citas),default=0)+1);ids['cita']=number+1
 a={'id':number,'pac':patient['id'],'med':doctor['id'],'esp':specialty,'tipo':'Eventual','modalidad':'presencial','fecha':date,'hora':attention_time,'estado':'Pendiente','motivo':'Sin cita previa: '+reason.strip(),'origen':'sin_cita','serviciosSolicitados':items,'createdAt':stamp,'updatedAt':stamp,'registeredBy':user['id'],'walkinRequest':request_id,'notif':'Sin recordatorio'}
 citas.append(a);set_json_key(conn,'citas',citas);set_json_key(conn,'nextIds',ids);audit(conn,user,'walkin_register','citas',{'id':number,'patientId':patient['id'],'concepts':len(items)})
 return {'ok':True,'appointment':a,'appointments':filter_data({**context(conn),'citas':citas},user)['citas'] if user.get('rol')=='medico' else citas,'nextIds':ids}
