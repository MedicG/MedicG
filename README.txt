Medic G Web con base de datos segura

Uso local con base de datos
1. Ejecuta INICIAR.bat.
2. Abre en el navegador: http://127.0.0.1:8080
3. Ingresa con el usuario administrador configurado.

Uso web / hosting
- El backend debe ejecutarse en un hosting que soporte Python: VPS, Render, Railway u otro.
- GitHub Pages solo debe usarse para mostrar el frontend.
- Comando de inicio del backend:
  python server.py

Uso seguro con GitHub Pages
- GitHub Pages NO ejecuta Python ni SQLite.
- Para guardar todo en base de datos segura, config.js debe apuntar a un backend real.
- El modo local del navegador queda desactivado por seguridad.
- Edita config.js y coloca:
  window.MEDICG_API_BASE = "https://tu-backend.com";
  window.MEDICG_REQUIRE_BACKEND = true;

Variables de entorno recomendadas
- PORT: puerto asignado por el hosting.
- HOST: normalmente 0.0.0.0.
- MEDICG_DB_PATH: ruta donde se guardara la base de datos.
- ADMIN_EMAIL: correo inicial del administrador.
- ADMIN_PASSWORD: contrasena inicial del administrador.
- ALLOWED_ORIGINS: dominios permitidos para conectarse al backend, separados por coma.
  Ejemplo: https://tuusuario.github.io
- PUBLIC_APP_URL: URL publica del sistema para crear enlaces de verificacion.
  Ejemplo: https://tuusuario.github.io/medicg
- SMTP_HOST: servidor SMTP para enviar correos de verificacion.
- SMTP_PORT: puerto SMTP, normalmente 587.
- SMTP_USER: usuario/correo SMTP.
- SMTP_PASSWORD: clave o app password SMTP.
- SMTP_FROM: correo remitente. Si se deja vacio usa SMTP_USER o ADMIN_EMAIL.
- SMTP_TLS: true para STARTTLS en puerto 587.
- SMTP_SSL: true solo si usas puerto 465.

Seguridad incluida
- Los datos se guardan en SQLite en el backend, no en el navegador.
- Las contrasenas se guardan con hash PBKDF2, no en texto plano.
- Los usuarios pueden registrarse con correo y deben verificarlo antes de iniciar sesion.
- Las cuentas registradas quedan sin permisos hasta que el administrador las autorice.
- El administrador tambien puede crear usuarios internos desde Configuracion > Usuarios del sistema.
- Solo el administrador puede abrir y cerrar caja; los movimientos se guardan en la caja abierta.
- Gestion de quirofanos, disponibilidad de equipos especializados y stock quirurgico.
- El backend valida sesion para cada guardado.
- Las sesiones se guardan en SQLite; si el backend se reinicia, el usuario puede seguir guardando mientras el token no expire.
- CORS se puede restringir con ALLOWED_ORIGINS.
- Se agregan cabeceras de seguridad HTTP.
- Se registra auditoria de login, logout, creacion de usuarios y guardado de datos.

Importante
- Usa una ruta persistente para MEDICG_DB_PATH. Si el hosting borra archivos al reiniciar, perderas la base.
- Cambia ADMIN_PASSWORD antes de entregar el sistema a un cliente.
- Si config.js no apunta a un backend real, el login no se habilitara en modo seguro.
- Si no configuras SMTP, el sistema creara la cuenta pero no podra enviar el correo de verificacion.
