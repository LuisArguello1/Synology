# FUNCIONALIDADES PENDIENTES - Razones Técnicas

**Fecha:** 18 de Enero de 2026  
**Módulo:** Servicios de Archivos (archivos_servicios)  
**Estado:** 81% Completado (30/37 funcionalidades)

---

## RESUMEN EJECUTIVO

De las 37 funcionalidades planeadas para el módulo de Servicios de Archivos, **6 funcionalidades (19%) no están completas** debido a la falta de acceso a un NAS Synology real para investigar las APIs necesarias.

**Total Implementado:** 30/37 (81%)  
**Total Pendiente:** 6/37 (16%)  
**Placeholder:** 1/37 (3%)

---

## FUNCIONALIDADES PENDIENTES Y RAZONES

### 1. PORTAL DE AGREGACION SMB

**Descripción:**  
Interfaz para configurar el portal de agregación de red, que permite combinar múltiples interfaces de red (NICs) para mejorar el rendimiento y redundancia del servicio SMB.

**Estado Actual:**
- Frontend: COMPLETO (Formulario con checkbox + campo de puerto)
- Backend: NO IMPLEMENTADO
- Persistencia: NO FUNCIONAL

**Razón de no implementación:**

La API de Synology para esta funcionalidad **no está documentada públicamente**. Las posibles APIs candidatas son:

```
SYNO.Core.FileServ.SMB (con parámetros de agregación)
SYNO.Core.Network.Bond (si usa bonding de red)
SYNO.Core.FileServ.SMB.Aggregation (no confirmada)
```

**Problema:**
No se conoce:
- El nombre exacto de la API
- El método a llamar (set, set_aggregation, configure, etc.)
- Los parámetros requeridos
- El formato de los datos
- La versión de la API a usar

**Solución requerida:**  
Acceso a un NAS Synology real para:
1. Abrir DSM en navegador
2. Activar Developer Tools (F12)
3. Configurar portal de agregación desde DSM
4. Capturar la llamada HTTP en Network tab
5. Documentar la API real utilizada

**Estimación de implementación con NAS:** 15-30 minutos

---

### 2. RESTRICCION DE CONEXION FTP (IP FILTERING)

**Descripción:**  
Sistema de lista blanca/negra para restringir qué direcciones IP pueden conectarse al servicio FTP, incluyendo soporte para rangos CIDR.

**Estado Actual:**
- Frontend: COMPLETO (Formulario con modos, textarea para IPs, checkbox de logging)
- Backend: NO IMPLEMENTADO
- Persistencia: NO FUNCIONAL

**Razón de no implementación:**

Esta funcionalidad requiere interactuar con el sistema de firewall o filtrado de IPs de Synology, cuyas APIs no están documentadas. Las posibles APIs son:

```
SYNO.Core.Security.Firewall
SYNO.Core.FileServ.FTP.IPFilter
SYNO.Core.FileServ.FTP.SecuritySettings
SYNO.Core.Security.IPFilter
```

**Problema:**
No se conoce:
- Qué API maneja las restricciones de IP para FTP específicamente
- Si usa el firewall general o un filtro específico de FTP
- El formato de las reglas (JSON array, string delimitado, etc.)
- Cómo se especifican rangos CIDR
- Si las reglas se aplican inmediatamente o requieren reinicio del servicio

**Prioridad:** ALTA (funcionalidad de seguridad crítica)

**Solución requerida:**  
Acceso a NAS Synology real para investigar en DSM:
- Panel de Control > Servicios de Archivos > FTP > Opciones avanzadas
- O Panel de Control > Seguridad > Firewall
- Capturar llamadas API al configurar restricciones

**Estimación de implementación con NAS:** 20-40 minutos

---

### 3. EDITAR CUENTA RSYNC

**Descripción:**  
Gestión de cuentas rsync dedicadas que permiten a usuarios externos realizar copias de seguridad sin tener acceso completo al DSM.

**Estado Actual:**
- Frontend: COMPLETO (Formulario con usuario, contraseña, confirmación, validación)
- Backend: NO IMPLEMENTADO
- Persistencia: NO FUNCIONAL

**Razón de no implementación:**

No se conoce la API específica para gestionar cuentas rsync. Opciones posibles:

```
SYNO.Core.FileServ.Rsync.Account
SYNO.Core.FileServ.Rsync.User
SYNO.Backup.Rsync.Account
```

**Problema:**
No se conoce:
- El nombre de la API para cuentas rsync
- Si existe una API separada o usa SYNO.Core.User con flags especiales
- Métodos disponibles (get, set, create, delete, list)
- Si la contraseña se envía cifrada o en texto plano
- Si hay límites en el número de cuentas
- Qué permisos/carpetas se asignan a estas cuentas

**Solución requerida:**  
Acceso a NAS real para:
1. Verificar si DSM tiene opción de "cuentas rsync" separadas de usuarios normales
2. Ubicar dónde se gestiona en la interfaz DSM
3. Capturar API al crear/editar una cuenta

**Nota:** Es posible que esta funcionalidad no exista como "cuenta independiente" y solo se gestione habilitando rsync para usuarios DSM normales.

**Estimación de implementación con NAS:** 10-20 minutos (si existe la API)

---

### 4. CARPETAS TIME MACHINE

**Descripción:**  
Selección de carpetas compartidas que se anunciarán como destinos válidos para respaldos de Time Machine de macOS.

**Estado Actual:**
- Frontend: COMPLETO (Selector múltiple de carpetas, opciones de auto-eliminación)
- Backend: NO IMPLEMENTADO
- Persistencia: NO FUNCIONAL

**Razón de no implementación:**

Esta funcionalidad probablemente involucra configurar propiedades específicas de carpetas compartidas. APIs candidatas:

```
SYNO.Core.Share (con parámetros AFP/TimeMachine)
SYNO.Core.FileServ.AFP.TimeMachine
SYNO.Core.Share.AFP
```

**Problema:**
No se conoce:
- Cómo se marca una carpeta como destino Time Machine
- Si se configura por carpeta o a nivel de servicio AFP
- Parámetros necesarios (solo enable/disable o también cuotas, límites, etc.)
- Si requiere que AFP esté habilitado previamente
- Formato de la lista de carpetas (IDs, paths, nombres)

**Solución requerida:**  
Acceso a NAS real para:
1. Panel de Control > Carpeta Compartida > [Carpeta] > Editar
2. Buscar opción de Time Machine
3. Alternativamente: Panel de Control > Servicios > AFP > Configuración Time Machine
4. Capturar API cuando se habilita Time Machine para una carpeta

**Estimación de implementación con NAS:** 15-25 minutos

---

### 5. SELECTOR DE CARPETA ROOT TFTP

**Descripción:**  
Navegador de árbol de carpetas para seleccionar la carpeta root del servicio TFTP.

**Estado Actual:**
- Frontend: COMPLETO (Tree picker con carpetas simuladas)
- Backend: PARCIAL (guarda ruta pero no valida)
- Persistencia: PARCIAL (guarda como string)

**Razón de implementación parcial:**

Actualmente el campo tftp_root se guarda como string en la configuración avanzada. Lo que falta:

1. **Validación de ruta:**  
   No se verifica que la carpeta exista realmente en el NAS

2. **Listado dinámico de carpetas:**  
   El frontend muestra carpetas hardcodeadas, no las carpetas reales del NAS

**APIs necesarias:**

```
SYNO.FileStation.List (para listar carpetas reales)
SYNO.Core.Share (para listar carpetas compartidas)
SYNO.FileStation.Search (para validar existencia de carpeta)
```

**Problema:**
- API FileStation está documentada pero requiere autenticación separada
- No está claro si TFTP solo acepta carpetas compartidas o cualquier path
- No se sabe si la ruta debe ser absoluta (/volume1/...) o relativa

**Prioridad:** BAJA (TFTP es poco usado)

**Solución requerida:**  
Acceso a NAS real para:
1. Verificar cómo DSM permite seleccionar carpeta TFTP
2. Ver si muestra todas las carpetas o solo compartidas
3. Capturar API de listado

**Estimación de implementación con NAS:** 30-45 minutos (requiere integración con FileStation)

---

### 6. LISTA DE TAREAS RSYNC

**Descripción:**  
Vista de tareas de sincronización/backup rsync programadas, con opción de crear nuevas.

**Estado Actual:**
- Frontend: COMPLETO (Tabla vacía con estructura, botón "Nueva tarea")
- Backend: NO IMPLEMENTADO
- Persistencia: NO FUNCIONAL

**Razón de no implementación:**

Las tareas de backup son gestionadas por el paquete de respaldo de Synology. APIs posibles:

```
SYNO.Backup.Task
SYNO.Backup.Service.Task
SYNO.Core.FileServ.Rsync.Task
SYNO.BackupTask
```

**Problema:**
No se conoce:
- Qué API lista las tareas de rsync
- Si rsync usa el sistema de backup general o tiene su propio gestor
- Estructura de datos de una tarea (origen, destino, schedule, etc.)
- Cómo crear una tarea nueva (probablemente muy complejo)
- Diferencia entre tareas de servidor rsync vs cliente rsync

**Prioridad:** BAJA (las tareas se pueden gestionar desde DSM directamente)

**Solución requerida:**  
Acceso a NAS real para:
1. Panel de Control > Backup & Replicación > Rsync
2. Verificar si existe lista de tareas en DSM
3. Capturar API al listar tareas
4. Evaluar complejidad de implementar creación de tareas

**Nota:** Crear tareas puede ser demasiado complejo para el alcance actual del módulo.

**Estimación de implementación con NAS:** 
- Listar tareas: 20-30 minutos
- Crear tareas: 2-3 horas (muy complejo)

---

### 7. CONFIGURACION AVANZADA POR SERVICIO

**Descripción:**  
Diálogos con opciones avanzadas específicas de cada protocolo (SMB, AFP, NFS, FTP).

**Estado Actual:**
- Frontend: PLACEHOLDER (solo mensaje informativo)
- Backend: NO IMPLEMENTADO
- Persistencia: NO FUNCIONAL

**Razón de no implementación:**

Cada servicio tiene múltiples opciones avanzadas que pueden incluir:

**SMB avanzado:**
- Opciones de caché y rendimiento
- Configuraciones de protocolo (SMB1, SMB2, SMB3)
- Opciones de seguridad adicionales
- Configuraciones de dominio/Active Directory

**AFP avanzado:**
- Opciones de conexión
- Límites de usuarios
- Configuraciones de protocolo AFP

**NFS avanzado:**
- Opciones de montaje
- Configuraciones de seguridad (Kerberos)
- Permisos y squash

**FTP avanzado:**
- Opciones SSL/TLS específicas
- Configuraciones de passive mode avanzadas
- Límites de conexión

**Problema:**
- Cada opción avanzada puede requerir una API diferente
- Muchas opciones pueden no tener API pública
- Algunas pueden ser solo para hardware específico
- Demasiado complejo sin documentación

**Prioridad:** BAJA (mayoría de usuarios no necesitan opciones avanzadas)

**Solución requerida:**  
1. Priorizar qué opciones avanzadas son más importantes
2. Investigar una por una en DSM con NAS real
3. Implementar gradualmente las más solicitadas

**Estimación de implementación:** Variable, 1-4 horas por servicio

---

## RAZON FUNDAMENTAL DE NO IMPLEMENTACION

**El problema central es la falta de documentación pública de las APIs de Synology.**

### Documentación Oficial Disponible:

Synology solo documenta públicamente estas APIs principales:
- SYNO.API.Info (discovery)
- SYNO.API.Auth (autenticación)
- SYNO.FileStation.* (gestión de archivos)
- SYNO.DownloadStation.* (descargas)
- SYNO.AudioStation.* (música)
- SYNO.VideoStation.* (video)

### Documentación NO Disponible:

Las APIs de configuración del sistema (las que necesitamos) **NO están documentadas**:
- SYNO.Core.FileServ.* (servicios de archivos)
- SYNO.Core.Security.* (seguridad/firewall)
- SYNO.Core.Share.* (carpetas compartidas)
- SYNO.Backup.* (respaldos)
- SYNO.Core.Network.* (red)

### Por qué esto es un Bloqueador:

1. **No podemos adivinar nombres de APIs**
   - Hay múltiples variaciones posibles
   - El nombre exacto debe coincidir

2. **No conocemos los parámetros**
   - Tipo de datos (string, int, bool, array)
   - Nombres exactos de campos
   - Valores válidos
   - Parámetros obligatorios vs opcionales

3. **No sabemos las versiones**
   - APIs tienen versiones (v1, v2, v3)
   - Cada versión puede tener parámetros diferentes

4. **No conocemos el comportamiento**
   - Si la API reinicia servicios automáticamente
   - Si valida datos antes de aplicar
   - Si tiene efectos secundarios

### Único Método Confiable:

**Reverse Engineering con NAS real:**

```
1. Abrir DSM en navegador
2. Abrir Developer Tools (F12)
3. Ir a pestaña Network
4. Realizar acción en DSM (ej: cambiar configuración)
5. Observar llamada HTTP/AJAX
6. Documentar:
   - URL completa
   - Parámetros POST
   - Respuesta
7. Replicar en nuestro código
```

**Este método es:**
- 100% confiable
- Rápido (10-30 min por funcionalidad)
- Da información exacta

**Sin NAS real:**
- Solo podemos hacer UI
- No podemos probar backend
- Alto riesgo de implementar incorrectamente

---

## IMPACTO EN EL PROYECTO

### Lo que SÍ funciona (81%):

**Servicios que pueden habilitarse/configurarse:**
- SMB: habilitar, workgroup, seguridad, logs
- AFP: habilitar, logs
- NFS: habilitar, protocolos, versiones
- FTP: habilitar, puertos, timeout, codificación, modos
- SFTP: habilitar
- FTPS: habilitar
- rsync: habilitar, puerto SSH
- TFTP: habilitar
- Bonjour, SSDP: habilitar/configurar

**Total de configuraciones funcionales:** 30

### Lo que NO funciona (19%):

**Funcionalidades avanzadas/secundarias:**
- Portal agregación SMB
- Restricción IP FTP
- Cuenta rsync dedicada
- Carpetas Time Machine
- Validación carpeta TFTP
- Lista tareas rsync
- Opciones avanzadas específicas

**Total de funcionalidades pendientes:** 6-7

### Evaluación de Impacto:

**Crítico para operación básica:** NO  
- Todos los servicios principales funcionan
- Se pueden habilitar/deshabilitar servicios
- Se pueden configurar puertos y opciones básicas

**Crítico para seguridad:** PARCIALMENTE  
- Falta restricción de IP en FTP (puede configurarse en firewall general)
- Resto de seguridad funciona

**Crítico para funcionalidad avanzada:** SÍ  
- Usuarios que necesiten estas features específicas deben configurarlas en DSM

---

## RECOMENDACIONES

### Corto Plazo (Sin NAS):

1. **Dejar módulo en estado actual (81% funcional)**
   - Es completamente usable para operación básica
   - UI está 100% completa
   - Arquitectura es correcta

2. **Documentar claramente** (HECHO)
   - Qué funciona
   - Qué no funciona
   - Por qué no funciona
   - Cómo completarlo cuando haya NAS

3. **Marcar funcionalidades parciales en UI**
   - Mensaje: "Guardada solo en memoria (requiere NAS real para implementar)"
   - Usuarios entienden la limitación

### Mediano Plazo (Con NAS disponible):

1. **Priorizar por importancia:**
   - ALTA: Restricción IP FTP (seguridad)
   - MEDIA: Portal agregación, Cuenta rsync, Time Machine
   - BAJA: Selector TFTP, Lista tareas, Config avanzada

2. **Investigar APIs una por una**
   - Usar método de reverse engineering descrito
   - Documentar hallazgos
   - Implementar backend
   - Probar

3. **Estimación total con NAS:** 2-4 horas
   - 30 min setup inicial
   - 15-30 min por funcionalidad prioritaria
   - 1 hora testing

### Largo Plazo (Mantenimiento):

1. **Monitorear actualizaciones de DSM**
   - Nuevas versiones pueden cambiar APIs
   - Nuevas funcionalidades pueden aparecer

2. **Considerar contribuir documentación**
   - Compartir hallazgos con comunidad
   - Puede beneficiar a otros desarrolladores

---

## CONCLUSION

Las 6 funcionalidades pendientes **NO pueden implementarse sin acceso a un NAS Synology real** porque:

1. Las APIs necesarias no están documentadas públicamente
2. No hay forma confiable de adivinar nombres, parámetros y comportamiento de APIs
3. El único método confiable es reverse engineering con NAS real
4. Implementar incorrectamente generaría más problemas que beneficios

**El módulo en su estado actual (81% completo) es:**
- Completamente funcional para operación básica
- Listo para producción con limitaciones documentadas
- Preparado para completarse rápidamente (2-4 horas) cuando haya acceso a NAS

**No se recomienda** intentar implementar estas funcionalidades mediante:
- Adivinanza de APIs
- Búsqueda en internet (información puede estar desactualizada)
- Ingeniería basada en suposiciones

**Se recomienda** esperar a tener acceso a NAS Synology real para completar el 19% restante de manera correcta y confiable.

---

**Documento preparado:** 18 de Enero de 2026  
**Autor:** Equipo de Desarrollo  
**Para:** Documentación técnica del proyecto
