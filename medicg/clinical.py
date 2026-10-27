"""Specialty follow-up entries: append-only records with server-authenticated authorship."""
import datetime as dt
import uuid
from medicg.doctor_scope import norm, specialties, check_patient

VERSION='2026-09-20.1'
SOURCES=[{'title':'MSP Ecuador · Catálogo de guías de práctica clínica','url':'https://www.salud.gob.ec/guias-de-practica-clinica/'},{'title':'MSP · Control prenatal (2016)','url':'https://www.salud.gob.ec/wp-content/uploads/2014/05/GPC-CPN-final-mayo-2016-DNN.pdf'},{'title':'OMS · Atención prenatal, material de formación (2024)','url':'https://iris.who.int/bitstream/handle/10665/379574/WHO-AFRO-ULC-2024-08-eng.pdf'},{'title':'OMS · Atención posnatal (2022)','url':'https://www.who.int/publications/i/item/9789240045989'},{'title':'OMS · Intervenciones de rehabilitación (2023)','url':'https://www.who.int/teams/noncommunicable-diseases/sensory-functions-disability-and-rehabilitation/rehabilitation/service-delivery/package-of-interventions-for-rehabilitation'}]

def fields(*labels):return [{'id':'f'+str(i),'label':label,'type':'textarea'} for i,label in enumerate(labels)]
PROFILES={
 'general':{'name':'Medicina General','fields':fields('Problemas activos y antecedentes relevantes','Medicamentos, adherencia y alergias','Signos vitales y examen dirigido','Prevención, hábitos y factores de riesgo','Resultados revisados y evolución')},
 'ginecologia':{'name':'Ginecología','fields':fields('Historia menstrual, FUM y síntomas ginecológicos','Antecedentes obstétricos: gestaciones, partos, cesáreas, pérdidas y complicaciones','Antecedentes sexuales y reproductivos; anticoncepción y preferencias','Examen ginecológico y mamario: indicación, consentimiento y hallazgos','Tamizaje cervical: fecha, prueba, resultado y seguimiento','Pruebas de laboratorio o imagen revisadas')},
 'prenatal':{'name':'Control prenatal','fields':fields('Antecedentes obstétricos y evolución del embarazo actual','FUM, confiabilidad y método de datación','Edad gestacional (semanas + días) y fecha probable de parto confirmadas por profesional','Presión arterial, peso y valoración nutricional','Altura uterina, frecuencia cardíaca fetal y movimientos fetales, según etapa','Grupo sanguíneo/Rh, hemoglobina, orina y pruebas revisadas: fecha y resultados','Ecografías: fecha, hallazgos y conducta','Medicamentos, suplementos, inmunizaciones y adherencia','Síntomas, signos de alarma, evaluación y acciones realizadas','Salud mental, apoyo social y necesidades de protección','Consejería, preferencias y plan de nacimiento / referencia')},
 'posparto':{'name':'Seguimiento posparto','fields':fields('Fecha, lugar y vía del parto; días o semanas desde el nacimiento','Complicaciones del embarazo, parto y hospitalización','Signos vitales, dolor, sangrado/loquios y valoración general','Involución uterina, periné o herida quirúrgica: hallazgos','Lactancia, mamas, dificultades y apoyo brindado','Estado emocional, sueño, apoyo social y evaluación realizada','Micción, función intestinal, movilidad y recuperación','Anticoncepción, preferencias y salud sexual','Estado referido del recién nacido y vinculación con atención pediátrica','Signos de alarma, conducta, referencia y coordinación de seguimiento')},
 'cardiologia':{'name':'Cardiología','fields':fields('Síntomas y capacidad funcional','Antecedentes y factores de riesgo cardiovascular','Presión arterial, frecuencia, ritmo y examen cardiovascular','ECG, ecocardiograma y pruebas: fechas, resultados e interpretación','Tratamiento, adherencia, tolerancia y evolución')},
 'pediatria':{'name':'Pediatría','fields':fields('Antecedentes perinatales, cuidador e información aportada','Peso, longitud/talla, perímetro cefálico y evaluación del crecimiento según edad','Alimentación y nutrición','Desarrollo, aprendizaje y hallazgos de evaluación','Inmunizaciones: comprobación y pendientes','Examen dirigido, síntomas y orientación a cuidadores')},
 'dermatologia':{'name':'Dermatología','fields':fields('Inicio, evolución y síntomas de las lesiones','Morfología, localización, distribución y extensión','Exposiciones, medicamentos, alergias y antecedentes','Dermatoscopia, biopsia u otras pruebas: indicación y resultados','Tratamientos previos, respuesta y tolerancia','Registro fotográfico: consentimiento y referencia al archivo clínico')},
 'neurologia':{'name':'Neurología','fields':fields('Cronología de síntomas y eventos neurológicos','Estado mental y evaluación cognitiva realizada','Pares craneales, fuerza, tono, reflejos y sensibilidad','Coordinación, marcha, función y autonomía','Estudios neurofisiológicos o imagen: fechas y resultados','Tratamiento, respuesta, eventos adversos y objetivos funcionales')},
 'traumatologia':{'name':'Traumatología','fields':fields('Mecanismo, fecha de lesión y región / lateralidad','Dolor, movilidad, función y limitaciones','Examen musculoesquelético y estado neurovascular','Imágenes: fechas, hallazgos y comparación','Procedimientos, inmovilización, heridas y evolución','Rehabilitación, carga permitida y objetivos indicados por profesional')},
 'lenguaje':{'name':'Terapia de Lenguaje','fields':fields('Motivo, antecedentes del desarrollo y contexto comunicativo','Evaluación de comprensión, expresión, habla, voz y fluidez','Audición, comunicación funcional y deglución cuando corresponda','Instrumentos aplicados, resultados y línea base','Objetivos medibles y actividades de la sesión','Respuesta, ayudas requeridas y progreso respecto al control previo','Orientación a familia/cuidadores y actividades acordadas')},
 'laboratorio':{'name':'Revisión de exámenes de laboratorio','fields':fields('Solicitud e indicación clínica','Muestra, fecha de toma y condiciones relevantes','Pruebas, unidades e intervalos de referencia del laboratorio','Resultados y comparación con estudios previos','Resultados críticos: comunicación, destinatario, fecha y acción','Interpretación por profesional responsable y seguimiento')}
}

def profile_for(specialty):
 s=norm(specialty)
 for part,key in [('gineco','ginecologia'),('obstet','prenatal'),('cardio','cardiologia'),('pediatr','pediatria'),('dermat','dermatologia'),('neuro','neurologia'),('traumat','traumatologia'),('lenguaje','lenguaje'),('laboratorio','laboratorio')]:
  if part in s:return key
 return 'general'

class ClinicalError(ValueError):pass

def append_entry(conn,user,payload):
 from medicg_app import get_json_key,set_json_key,audit,can_save_key
 if user.get('rol') not in ('admin','medico') or not can_save_key(user,'notas'):raise ClinicalError('Solo profesionales autorizados pueden registrar la evolución.')
 pid=str(payload.get('patientId',''))
 patient=next((p for p in get_json_key(conn,'pacientes',[]) if str(p.get('id'))==pid and not p.get('deletedAt')),None)
 if not patient:raise ClinicalError('Paciente no disponible.')
 try:check_patient(conn,user,pid)
 except ValueError as exc:raise ClinicalError(str(exc))
 try:rid=str(uuid.UUID(str(payload.get('requestId'))))
 except (TypeError,ValueError):raise ClinicalError('Identificador de registro inválido.')
 notes=get_json_key(conn,'notas',{}) or {};entries=notes.get(pid,[])
 previous=next((n for n in entries if n.get('clinicalVersion') and n.get('requestId')==rid and n.get('authorId')==user['id']),None)
 if previous:return {'ok':True,'entry':previous,'replayed':True}
 doctor_id=user.get('medicoId') if user['rol']=='medico' else (payload.get('doctorId') or user.get('medicoId'))
 doctor=next((m for m in get_json_key(conn,'medicos',[]) if str(m.get('id'))==str(doctor_id) and m.get('estado')!='inactivo'),None)
 specialty=payload.get('specialty','')
 if not doctor or specialty not in specialties(doctor):raise ClinicalError('Selecciona un profesional y una de sus especialidades.')
 profile=payload.get('profile');base=profile_for(specialty)
 if not isinstance(profile,str) or profile not in ({'ginecologia','prenatal','posparto'} if base in ('ginecologia','prenatal') else {base}):raise ClinicalError('Formulario incompatible con la especialidad.')
 def text(key,required=False,maxlen=4000):
  value=payload.get(key,'')
  if not isinstance(value,str) or len(value)>maxlen or (required and not value.strip()):raise ClinicalError('Completa o revisa el campo '+key+'.')
  return value.strip()
 now=dt.datetime.now(dt.timezone(dt.timedelta(hours=-5)))
 try:
  visit=dt.datetime.fromisoformat(text('date',True)+'T'+text('time',True)).replace(tzinfo=now.tzinfo)
  if visit>now+dt.timedelta(minutes=5):raise ValueError()
  follow=text('nextDate');next_date=dt.date.fromisoformat(follow) if follow else None
  if next_date and next_date<visit.date():raise ValueError()
 except (ValueError,TypeError):raise ClinicalError('Revisa fecha y hora de atención y próximo control. La evolución no puede ser futura.')
 frequency=text('frequency');allowed_freq={'Inicial','Semanal','Mensual','Personalizado','Posparto','Adenda'}
 if frequency not in allowed_freq:raise ClinicalError('Tipo de seguimiento inválido.')
 raw=payload.get('fields',{})
 if not isinstance(raw,dict) or any(k not in {f['id'] for f in PROFILES[profile]['fields']} or not isinstance(v,str) or len(v)>4000 for k,v in raw.items()):raise ClinicalError('Campos clínicos inválidos.')
 correction=text('correctionOf');correction_reason=text('correctionReason')
 if correction and (not correction_reason or not any(str(n.get('id'))==correction for n in entries)):raise ClinicalError('Selecciona el registro original y explica la corrección.')
 if frequency=='Adenda' and not correction:raise ClinicalError('La adenda necesita un registro original.')
 episode=text('episode',True,120)
 fields_data=[{'id':f['id'],'label':f['label'],'value':raw.get(f['id'],'').strip()} for f in PROFILES[profile]['fields']]
 summary='\n\n'.join(f['label']+': '+f['value'] for f in fields_data if f['value'])
 entry={'id':str(uuid.uuid4()),'clinicalVersion':1,'templateVersion':VERSION,'requestId':rid,'authorId':user['id'],'authorName':(user.get('name','')+' '+user.get('last','')).strip(),'recordedAt':now.isoformat(timespec='seconds'),'sequence':max((n.get('sequence',0) for n in entries if n.get('clinicalVersion')),default=0)+1,'episode':episode,'profile':profile,'fields':fields_data,'frequency':frequency,'nextDate':follow,'correctionOf':correction or None,'correctionReason':correction_reason,'formato':'Medic G · Seguimiento por especialidad','tipo':PROFILES[profile]['name'],'fecha':visit.date().isoformat(),'hora':visit.strftime('%H:%M'),'esp':specialty,'med':doctor.get('nombre',''),'medId':doctor['id'],'motivo':text('reason',True),'dx':text('assessment',True),'plan':text('plan',True),'observaciones':summary,'references':SOURCES[:4] if profile in ('prenatal','posparto','ginecologia') else ([SOURCES[0],SOURCES[4]] if profile in ('lenguaje','neurologia','traumatologia') else [SOURCES[0]]),'validationStatus':'Plantilla de registro; requiere validación clínica institucional'}
 entries.insert(0,entry);notes[pid]=entries;set_json_key(conn,'notas',notes)
 audit(conn,user,'clinical_entry_append','notas',{'patientId':pid,'entryId':entry['id'],'sequence':entry['sequence'],'correctionOf':entry['correctionOf'],'templateVersion':VERSION})
 return {'ok':True,'entry':entry,'replayed':False}

def preserve_entries(current,incoming):
 def protected(data):
  result={}
  if not isinstance(data,dict):raise ClinicalError('Formato de historias inválido.')
  for pid,rows in data.items():
   if not isinstance(rows,list):raise ClinicalError('Formato de evoluciones inválido.')
   for n in rows:
    if not isinstance(n,dict):raise ClinicalError('Registro clínico inválido.')
    if n.get('clinicalVersion'):
     key=str(n.get('id'))
     if key in result:raise ClinicalError('Evolución duplicada.')
     result[key]=(str(pid),n)
  return result
 if protected(current or {})!=protected(incoming or {}):raise ClinicalError('Las evoluciones de la bitácora no se editan ni eliminan. Registra una adenda.')
