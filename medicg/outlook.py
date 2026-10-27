import json,time,uuid,urllib.request,urllib.error,urllib.parse,base64
from medicg.mailer import MailError
SCOPE='https://graph.microsoft.com/Mail.Send https://graph.microsoft.com/User.Read offline_access'
BASE='https://login.microsoftonline.com/consumers/oauth2/v2.0/'

def microsoft_form(endpoint,data):
 req=urllib.request.Request(BASE+endpoint,data=urllib.parse.urlencode(data).encode(),headers={'Content-Type':'application/x-www-form-urlencoded'})
 try:
  with urllib.request.urlopen(req,timeout=20) as response:return json.load(response)
 except urllib.error.HTTPError as e:
  try:return json.load(e)
  except Exception:raise MailError('Microsoft no pudo completar la conexión.')

def connect(conn,user,action):
 import medicg_app as app
 from medicg.mailer import settings,public_settings
 cfg=settings(conn)
 if cfg.get('provider')!='microsoft' or not cfg.get('clientId'):raise MailError('Guarda primero el identificador de la aplicación Microsoft.')
 if action=='start':
  result=microsoft_form('devicecode',{'client_id':cfg['clientId'],'scope':SCOPE})
  if not result.get('device_code'):raise MailError('Microsoft rechazó la aplicación. Revisa el ID, compatibilidad con cuentas personales y flujos de cliente público.')
  pending={'code':result['device_code'],'userId':user['id'],'expires':time.time()+int(result['expires_in']),'interval':int(result.get('interval',5)),'lastPoll':0,'clientId':cfg['clientId'],'from':cfg['from']}
  app.set_json_key(conn,'outlookPendingPrivate',pending)
  return {'pending':True,'userCode':result['user_code'],'verificationUri':'https://microsoft.com/devicelogin','interval':pending['interval'],'expiresIn':result['expires_in']}
 if action=='disconnect':
  for key in ('refreshToken','connectedAt'):cfg.pop(key,None)
  app.set_json_key(conn,'outgoingEmailPrivate',cfg);app.set_json_key(conn,'outlookPendingPrivate',{})
  app.audit(conn,user,'outlook_disconnected','outgoingEmailPrivate')
  return {'settings':public_settings(conn)}
 pending=app.get_json_key(conn,'outlookPendingPrivate',{}) or {}
 if pending.get('userId')!=user['id'] or pending.get('expires',0)<time.time() or pending.get('clientId')!=cfg['clientId'] or pending.get('from')!=cfg['from']:raise MailError('La conexión venció. Pulsa Conectar Outlook nuevamente.')
 if time.time()-pending.get('lastPoll',0)<pending.get('interval',5):return {'pending':True}
 pending['lastPoll']=time.time();app.set_json_key(conn,'outlookPendingPrivate',pending)
 result=microsoft_form('token',{'grant_type':'urn:ietf:params:oauth:grant-type:device_code','client_id':cfg['clientId'],'device_code':pending['code']})
 if result.get('error') in ('authorization_pending','slow_down'):
  if result['error']=='slow_down':pending['interval']+=5;app.set_json_key(conn,'outlookPendingPrivate',pending)
  return {'pending':True,'interval':pending['interval']}
 if not result.get('access_token') or not result.get('refresh_token'):raise MailError('No se autorizó la conexión. Intenta nuevamente en Microsoft.')
 req=urllib.request.Request('https://graph.microsoft.com/v1.0/me?$select=mail,userPrincipalName',headers={'Authorization':'Bearer '+result['access_token']})
 with urllib.request.urlopen(req,timeout=20) as response:profile=json.load(response)
 addresses=[str(profile.get(k) or '').lower() for k in ('mail','userPrincipalName')]
 if cfg['from'].lower() not in addresses:raise MailError('La cuenta autorizada no coincide con el correo remitente. Conecta '+cfg['from']+'.')
 cfg['refreshToken']=result['refresh_token'];cfg['connectedAt']=app.now_iso()
 app.set_json_key(conn,'outgoingEmailPrivate',cfg);app.set_json_key(conn,'outlookPendingPrivate',{})
 app.audit(conn,user,'outlook_connected','outgoingEmailPrivate',{'from':cfg['from']})
 return {'pending':False,'settings':public_settings(conn)}

def send_graph(cfg,to_email,subject,html_body,attachments,conn=None):
 import medicg_app as app
 if not cfg.get('refreshToken'):raise MailError('Conecta la cuenta Outlook desde Configuración.')
 token=microsoft_form('token',{'client_id':cfg['clientId'],'grant_type':'refresh_token','refresh_token':cfg['refreshToken'],'scope':SCOPE})
 if not token.get('access_token'):raise MailError('Microsoft solicita conectar nuevamente la cuenta Outlook.')
 if token.get('refresh_token'):
  cfg['refreshToken']=token['refresh_token']
  if conn is not None:app.set_json_key(conn,'outgoingEmailPrivate',cfg)
  else:
   with app.db() as write_conn:app.set_json_key(write_conn,'outgoingEmailPrivate',cfg)
 message={'subject':subject,'body':{'contentType':'HTML','content':html_body},'toRecipients':[{'emailAddress':{'address':to_email}}]}
 if attachments:message['attachments']=[{'@odata.type':'#microsoft.graph.fileAttachment','name':a['filename'],'contentType':a.get('mime','application/octet-stream'),'contentBytes':base64.b64encode(a['content']).decode()} for a in attachments]
 req=urllib.request.Request('https://graph.microsoft.com/v1.0/me/sendMail',data=json.dumps({'message':message,'saveToSentItems':True}).encode(),headers={'Authorization':'Bearer '+token['access_token'],'Content-Type':'application/json'},method='POST')
 with urllib.request.urlopen(req,timeout=20) as response:
  if response.status!=202:raise MailError('Microsoft no confirmó la aceptación del correo.')
 return True,''
