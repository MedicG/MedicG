Medic G Web con base de datos SQLite

Uso local
1. Ejecuta INICIAR.bat.
2. Abre en el navegador: http://127.0.0.1:8080
3. Ingresa con:
   Correo: admin@medicg.com
   Contraseña: Admin123

Uso en red local
- Si el computador servidor y el cliente están en la misma red, abre desde el otro equipo:
  http://IP-DEL-SERVIDOR:8080
- Ejemplo: http://192.168.1.20:8080

Uso web / hosting
- El servidor escucha en 0.0.0.0 y toma el puerto desde la variable PORT.
- Puedes subir esta carpeta a un VPS, Render, Railway u otro hosting que ejecute Python.
- Comando de inicio:
  python server.py

Uso con GitHub Pages
- GitHub Pages NO ejecuta Python ni SQLite. Solo sirve archivos estáticos.
- Si config.js queda vacío, el sistema funcionará en modo local del navegador.
- En modo local el login funciona, pero los datos no son compartidos entre equipos.
- Solución recomendada:
  1. Sube server.py a Render, Railway o un VPS.
  2. Copia la URL pública del backend, por ejemplo:
     https://medicg-tu-cliente.onrender.com
  3. Edita config.js y coloca:
     window.MEDICG_API_BASE = "https://medicg-tu-cliente.onrender.com";
  4. Sube index.html y config.js a GitHub Pages.
- Si frontend y backend están juntos en el mismo hosting, deja config.js vacío.
- Revisa PASOS_GITHUB_RENDER.txt para una guía rápida con Render.

Variables de entorno recomendadas
- PORT: puerto asignado por el hosting.
- HOST: normalmente 0.0.0.0.
- MEDICG_DB_PATH: ruta donde se guardará la base de datos.
- ADMIN_EMAIL: correo inicial del administrador.
- ADMIN_PASSWORD: contraseña inicial del administrador.

Cambios incluidos
- Los datos se guardan en medicg.sqlite3 o en la ruta configurada con MEDICG_DB_PATH.
- El registro público está desactivado.
- Solo el administrador puede crear usuarios desde Configuración > Usuarios del sistema.
- Pacientes, citas, facturas, caja, médicos, especialidades, seguros y configuración se persisten en la base.
- Textos corregidos: acentos, eñes y símbolos dañados por codificación.
- Reparación automática de textos dañados en el navegador, por si el hosting sirve una copia con mala codificación.

Importante
- En hosting usa una ruta persistente para MEDICG_DB_PATH. Si el hosting borra archivos al reiniciar, perderás la base.
- Cambia ADMIN_PASSWORD antes de entregar el sistema a un cliente.
- No borres medicg.sqlite3 si quieres conservar los datos.
