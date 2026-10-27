# Medic G: base de producción para una clínica

## Arquitectura actual
- `index.html`: estructura de la interfaz. `assets/js/app.js`: lógica existente extraída sin cambiar el orden de ejecución. `assets/css/`: tema y ajustes adaptables.
- `medicg_app.py`: reglas de negocio y rutas compatibles.
- `medicg/storage.py`: conexiones acotadas, transacciones de lectura y escritura, rollback y liberación de conexiones.
- `medicg/entrypoint.py`: inicialización compartida entre `app.py` y `api/index.py`, con exclusión entre hilos y errores públicos sin detalles internos.

PostgreSQL usa hasta 4 conexiones por proceso, configurable mediante DB_POOL_MAX_SIZE (1–16). Usar la URL agrupada del proveedor. Cada instancia tiene su propio pool: considerar el total al ajustar concurrencia. Documentación de referencia: https://www.psycopg.org/psycopg3/docs/advanced/pool.html

## Integridad y permisos
Los guardados de colecciones requieren baseValue y rechazan una versión obsoleta con 409. Las citas usan su ruta transaccional con validación de disponibilidad. Recepción y secretaría conservan edición de servicios y exámenes. Las fichas guardadas por usuarios sin permiso clínico conservan sus campos clínicos protegidos. Los usuarios se gestionan solo por su ruta administrativa. Respaldo, migraciones y credenciales de certificado no se entregan como datos de aplicación.

El inicio de sesión no crea registros de ejemplo ni guarda contadores. Los registros existentes no se borran por esta actualización.

## Verificación
Ejecutar `python tests/test_storage.py`, `python tests/test_booking_persistence.py` y `node --check assets/js/app.js`. Las pruebas usan SQLite temporal, no credenciales ni pacientes de producción. La suite cubre rollback, solo lectura, concurrencia de reservas, persistencia, conflictos de guardado, roles, preservación clínica y bloqueo de archivos internos. Navegador local: inicio de sesión, servicio creado y conservado tras recarga, escritorio y móvil.

## Publicación y reversión
Crear primero un despliegue con `vercel deploy --prod --skip-domain`. Comprobar /api/health y recursos antes de promover al dominio. La versión publicada anterior identificada en la tarea es dpl_B7z9jxVmV6xhqFA42uo8P41LKVZy; verificar la versión vigente antes de revertir. El respaldo local tests/production-before-frontend.zip tiene manifiesto SHA-256 y tests/before-resume.zip conserva el estado parcial previo a esta continuación. No publicar tests ni respaldos.

## Escalabilidad (octubre 2026)
- **Guardado por registro** (`medicg/merge.py`): el navegador envía solo los registros que cambió (`delta`). El servidor verifica únicamente esos registros; si dos usuarios editan pacientes distintos al mismo tiempo, ambos cambios se conservan. Solo hay conflicto (409, con `conflicts`) cuando se editó el mismo registro. `nextIds` ya no genera conflictos: se conserva el mayor valor. Se mantiene compatibilidad con `value` + `baseValue`.
- **Archivos clínicos fuera del JSON** (`medicg/files.py`, tabla `clinical_files`): el contenido se guarda una sola vez y se descarga al abrirlo (`POST /api/clinical/file`). La migración mueve automáticamente los archivos existentes. Antes, al superar 12 MB en total ya no se podían subir más archivos.
- **Facturas livianas**: los XML (firmado, autorizado, respuestas SRI) no viajan al navegador; se conservan al guardar y se descargan desde su ruta.
- **Bloqueos acotados** (`medicg/storage.py`): sesiones, auditoría y bloqueo de inicio de sesión no usan el bloqueo global; la videoconsulta usa un bloqueo por cita. El envío al SRI y los correos se hacen fuera de la transacción, con una marca temporal que evita envíos dobles.
- **Arranque en frío liviano**: `init_db` consulta `migration_schema_version` en modo lectura y solo ejecuta migraciones cuando cambia `SCHEMA_VERSION`.
- **Otros**: respuestas JSON comprimidas con gzip, lectura parcial `GET /api/data?keys=a,b`, `GET /api/health?deep=1` comprueba la base, límite de intentos de inicio de sesión (`LOGIN_MAX_FAILURES`, `LOGIN_WINDOW_SECONDS`), errores 500 sin detalles internos y registro de solicitudes lentas.
- Pruebas: `python tests/test_scalability.py`.

## Límites pendientes
Las colecciones siguen guardándose como JSON en app_data y las escrituras generales mantienen el bloqueo global (ahora con transacciones más cortas). El siguiente paso para volúmenes grandes (decenas de miles de pacientes o facturas) es normalizar pacientes, citas y facturas en tablas propias con índices y paginación por módulo. `tests/test_cash_payments.py` espera IVA en cobros, pero el código aplica 0 % a servicios médicos: hay que actualizar esa prueba a la regla vigente.
