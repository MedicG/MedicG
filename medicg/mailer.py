"""Private outgoing-email configuration and explicit delivery."""
import base64,json,re,ssl,smtplib,urllib.request,urllib.error,socket,ipaddress
from email.message import EmailMessage
from email.utils import formataddr

class MailError(ValueError):pass

def valid_email(value):
 return isinstance(value,str) and len(value)<=254 and bool(re.fullmatch(r'[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+',value)) and not any(c in value for c in '\r\n')

def settings(conn=None):
 import medicg_app as app
 if conn is None:
  with app.db(read_only=True) as c:return settings(c)
 saved=app.get_json_key(conn,'outgoingEmailPrivate',{}) or {}
 if saved:return saved
 if app.RESEND_API_KEY:
  return {'provider':'resend','from':app.RESEND_FROM,'name':app.SMTP_FROM_NAME,'secret':app.RESEND_API_KEY,'source':'environment'}
 return {'provider':'smtp','host':app.SMTP_HOST,'port':app.SMTP_PORT,'security':'ssl' if app.SMTP_SSL else 'starttls','user':app.SMTP_USER,'secret':app.SMTP_PASSWORD,'from':app.SMTP_FROM,'name':app.SMTP_FROM_NAME,'source':'environment'}

def public_settings(conn):
 cfg=settings(conn)
 return {**{k:cfg.get(k,'') for k in ('provider','host','port','security','user','from','name','source','clientId','connectedAt')},'hasSecret':bool(cfg.get('secret')),'connected':bool(cfg.get('refreshToken')),'configured':bool(cfg.get('refreshToken')) or bool(cfg.get('from') and cfg.get('secret') and (cfg.get('provider')=='resend' or cfg.get('host')))}

def save_settings(conn,user,payload):
 import medicg_app as app
 if user.get('rol')!='admin':raise MailError('Solo el administrador configura el correo.')
 old=settings(conn);provider=payload.get('provider')
 if provider not in ('gmail','smtp','resend','microsoft'):raise MailError('Selecciona Gmail, Outlook, SMTP o Resend.')
 cfg={'provider':provider,'source':'configuration'}
 for key in ('host','user','from','name','security'):
  value=payload.get(key,'')
  if not isinstance(value,str) or len(value)>254 or '\r' in value or '\n' in value:raise MailError('Revisa los datos del remitente.')
  cfg[key]=value.strip()
 if not valid_email(cfg['from']):raise MailError('Ingresa un correo remitente válido.')
 if provider=='microsoft':
  import uuid
  try:cfg['clientId']=str(uuid.UUID(str(payload.get('clientId',''))))
  except (TypeError,ValueError):raise MailError('Ingresa el ID de aplicación Microsoft (Application client ID).')
  if old.get('provider')=='microsoft' and old.get('clientId')==cfg['clientId'] and old.get('from')==cfg['from']:
   for k in ('refreshToken','connectedAt'):
    if old.get(k):cfg[k]=old[k]
  app.set_json_key(conn,'outgoingEmailPrivate',cfg)
  app.audit(conn,user,'email_configuration_saved','outgoingEmailPrivate',{'provider':provider,'from':cfg['from']})
  return public_settings(conn)
 if provider=='gmail':
  cfg.update(host='smtp.gmail.com',port=587,security='starttls',user=cfg['from'])
 secret=payload.get('secret','')
 if not isinstance(secret,str) or len(secret)>4096:raise MailError('Credencial inválida.')
 if provider=='gmail':secret=secret.replace(' ','')
 cfg['secret']=secret or (old.get('secret','') if provider==old.get('provider') and (provider!='gmail' or old.get('from')==cfg['from']) else '')
 if provider=='gmail' and (len(cfg['secret'])!=16 or not cfg['secret'].isascii() or not cfg['secret'].isalpha()):raise MailError('Ingresa la contraseña de aplicación de Google de 16 letras, no tu contraseña habitual.')
 if not cfg['secret']:raise MailError('Ingresa la contraseña de aplicación o clave API.')
 if provider=='smtp':
  try:cfg['port']=int(payload.get('port',587))
  except (TypeError,ValueError):raise MailError('Puerto SMTP inválido.')
  if cfg['port'] not in (465,587,2525) or cfg['security'] not in ('ssl','starttls'):raise MailError('Usa SMTP cifrado: puerto 465, 587 o 2525.')
  if not cfg['host'] or not cfg['user'] or not re.fullmatch(r'[A-Za-z0-9.-]+',cfg['host']):raise MailError('Completa servidor y usuario SMTP.')
 app.set_json_key(conn,'outgoingEmailPrivate',cfg)
 app.audit(conn,user,'email_configuration_saved','outgoingEmailPrivate',{'provider':provider,'from':cfg['from']})
 return public_settings(conn)

def public_smtp_host(host,port):
 addresses=socket.getaddrinfo(host,port,type=socket.SOCK_STREAM)
 if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):raise MailError('El servidor SMTP debe ser público.')

def send(to_email,subject,text_body,html_body,attachments=None,config=None,conn=None):
 cfg=config if config is not None else settings()
 if not valid_email(to_email):return False,'El paciente necesita un correo válido.'
 if cfg.get('provider')!='microsoft' and (not cfg.get('secret') or not cfg.get('from')):return False,'Configura el correo saliente en Configuración.'
 if '\r' in subject or '\n' in subject:return False,'Asunto inválido.'
 attachments=attachments or []
 try:
  if cfg.get('provider')=='microsoft':
   from medicg.outlook import send_graph
   return send_graph(cfg,to_email,subject,html_body,attachments,conn)
  sender=formataddr((cfg.get('name') or 'Medic G',cfg['from']))
  if cfg.get('provider')=='resend':
   payload={'from':sender,'to':[to_email],'subject':subject,'text':text_body,'html':html_body}
   if attachments:payload['attachments']=[{'filename':a['filename'],'content':base64.b64encode(a['content']).decode('ascii')} for a in attachments]
   req=urllib.request.Request('https://api.resend.com/emails',data=json.dumps(payload).encode(),headers={'Authorization':'Bearer '+cfg['secret'],'Content-Type':'application/json'},method='POST')
   with urllib.request.urlopen(req,timeout=20) as response:
    if not 200<=response.status<300:return False,'El proveedor no aceptó el correo.'
  else:
   host=cfg.get('host','');port=int(cfg.get('port',587));public_smtp_host(host,port)
   msg=EmailMessage();msg['From']=sender;msg['To']=to_email;msg['Subject']=subject;msg.set_content(text_body);msg.add_alternative(html_body,subtype='html')
   for att in attachments:
    major,minor=(att.get('mime') or 'application/octet-stream').split('/',1)
    msg.add_attachment(att['content'],maintype=major,subtype=minor,filename=att['filename'])
   context=ssl.create_default_context()
   server=smtplib.SMTP_SSL(host,port,timeout=20,context=context) if cfg.get('security')=='ssl' else smtplib.SMTP(host,port,timeout=20)
   with server as smtp:
    if cfg.get('security')!='ssl':smtp.ehlo();smtp.starttls(context=context);smtp.ehlo()
    smtp.login(cfg.get('user',''),cfg['secret'])
    refused=smtp.send_message(msg)
    if refused:return False,'El servidor rechazó al destinatario.'
  return True,''
 except MailError as e:return False,str(e)
 except smtplib.SMTPAuthenticationError:return False,'El proveedor rechazó la autenticación. Revisa usuario y contraseña de aplicación.'
 except urllib.error.HTTPError as e:return False,f'El proveedor rechazó el correo (HTTP {e.code}). Revisa la clave, el remitente y el dominio verificado.'
 except (TimeoutError,socket.timeout):return False,'El proveedor no confirmó el envío a tiempo. Revisa su bandeja de enviados antes de reintentar.'
 except Exception:return False,'No se pudo confirmar el envío. Revisa servidor, puerto, remitente y conexión del proveedor.'
