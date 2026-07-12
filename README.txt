Medic G - Produccion en Vercel

Este proyecto ya esta preparado para subirlo a GitHub y conectarlo en Vercel.

Como funciona en produccion
- Vercel sirve index.html, config.js y assets.
- Vercel ejecuta la API Python desde api/index.py.
- La base de datos de produccion debe ser PostgreSQL.
- Si no hay DATABASE_URL o POSTGRES_URL, el sistema usa SQLite solo para pruebas locales.

Variables obligatorias en Vercel
- DATABASE_URL o POSTGRES_URL: conexion PostgreSQL. Recomendado: Neon desde Vercel Marketplace.
- ADMIN_EMAIL: correo del administrador inicial.
- ADMIN_PASSWORD: clave inicial del administrador. Cambiala antes de entregar.
- PUBLIC_API_URL: URL publica de Vercel. Ejemplo: https://medicg.vercel.app
- PUBLIC_APP_URL: URL del frontend. Si usas GitHub Pages: https://medicg.github.io/MedicG

Variables para enviar correos de verificacion
- SMTP_HOST: servidor SMTP.
- SMTP_PORT: normalmente 587.
- SMTP_USER: usuario/correo SMTP.
- SMTP_PASSWORD: clave SMTP o app password.
- SMTP_FROM: correo remitente.
- SMTP_TLS: true para puerto 587.
- SMTP_SSL: false para puerto 587, true solo si usas 465.

Variables recomendadas
- ALLOWED_ORIGINS: dominio permitido. Ejemplo: https://medicg.vercel.app
- Si usas GitHub Pages, usa ALLOWED_ORIGINS=https://medicg.github.io
- MAX_BODY_BYTES: limite de archivos adjuntos. Por defecto 12582912.

Pasos rapidos
1. Sube esta carpeta a un repositorio de GitHub.
2. En Vercel, importa el repositorio.
3. En Vercel Marketplace, agrega una base Postgres, por ejemplo Neon.
4. Confirma que Vercel agrego DATABASE_URL o POSTGRES_URL al proyecto.
5. Agrega las variables ADMIN_EMAIL, ADMIN_PASSWORD, PUBLIC_API_URL, PUBLIC_APP_URL y SMTP.
6. Deploy.
7. Abre la URL de Vercel e inicia sesion con el administrador inicial.
8. Crea o autoriza usuarios desde Configuracion > Usuarios del sistema.

Seguridad incluida
- Los datos se guardan en PostgreSQL en produccion.
- Las contrasenas se guardan con hash PBKDF2, no en texto plano.
- Las sesiones se guardan en la base de datos.
- Los usuarios registrados con correo deben verificar su email.
- Los usuarios verificados quedan sin permisos hasta que el administrador los autorice.
- El backend valida permisos antes de guardar cambios.
- El administrador controla usuarios, permisos, servicios y examenes.
- Se registra auditoria de login, logout, registros, permisos y guardados.

Uso local
1. Ejecuta INICIAR.bat.
2. Abre http://127.0.0.1:8080
3. Si no configuras DATABASE_URL, usara medicg.sqlite3 local.
4. El servidor local se ejecuta con local_server.py.

Importante
- No uses SQLite como base final en Vercel.
- Si publicas el frontend en GitHub Pages, revisa config.js y coloca tu dominio Vercel en MEDICG_VERCEL_BACKEND.
- Configura SMTP real; sin SMTP se crea la cuenta, pero no se enviara verificacion.
- Cambia ADMIN_PASSWORD despues del primer acceso.
