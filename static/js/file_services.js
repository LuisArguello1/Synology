/**
 * FILE_SERVICES.JS
 * 
 * Gestión de servicios de archivos del NAS Synology.
 * Maneja pestañas, formularios, y comunicación con la API.
 */

// Estado global de configuraciones
let currentConfigs = {
    smb: {},
    afp: {},
    nfs: {},
    ftp: {},
    rsync: {},
    advanced: {}
};

let currentTab = 'smb';

// ============================================
// GESTIÓN DE PESTAÑAS
// ============================================

function switchTab(tabName) {
    // Ocultar todas las pestañas
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });

    // Desactivar todos los botones de pestañas
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.classList.remove('active');
    });

    // Mostrar pestaña seleccionada
    const tabContent = document.getElementById(`tab-${tabName}`);
    if (tabContent) {
        tabContent.classList.add('active');
    }

    // Activar botón correspondiente
    document.querySelectorAll('.tab-button').forEach(btn => {
        if (btn.textContent.toLowerCase().includes(tabName)) {
            btn.classList.add('active');
        }
    });

    currentTab = tabName;
}

// ============================================
// ACORDEONES/COLLAPSIBLES
// ============================================

function toggleCollapsible(headerElement) {
    const section = headerElement.parentElement;
    const body = section.querySelector('.collapsible-body');
    const icon = headerElement.querySelector('i.fa-chevron-down');

    if (body.classList.contains('open')) {
        body.classList.remove('open');
        icon.style.transform = 'rotate(0deg)';
    } else {
        body.classList.add('open');
        icon.style.transform = 'rotate(180deg)';
    }
}

// ============================================
// CARGA INICIAL DE CONFIGURACIONES
// ============================================

async function loadAllConfigs() {
    try {
        const response = await fetch('/servicios-archivos/api/configs/');
        const configs = await response.json();

        if (configs) {
            currentConfigs = configs;
            populateAllForms(configs);
        }
    } catch (error) {
        console.error('Error cargando configuraciones:', error);
        showMessage('Error al cargar las configuraciones', 'error');
    }
}

function populateAllForms(configs) {
    // SMB
    if (configs.smb && configs.smb.success) {
        const data = configs.smb.data;
        setCheckbox('smb_enable', data.enable);
        setValue('smb_workgroup', data.workgroup);
        setCheckbox('smb_hide_dotfiles', data.hide_dotfiles);
        setCheckbox('smb_hide_unreadable', data.hide_unreadable);
        setCheckbox('smb_transfer_log', data.transfer_log);
        setCheckbox('smb_enable_aggregation', data.enable_aggregation);
        setCheckbox('smb_wsdiscovery', data.enable_wsdiscovery);
    }

    // AFP
    if (configs.afp && configs.afp.success) {
        const data = configs.afp.data;
        setCheckbox('afp_enable', data.enable);
        setCheckbox('afp_transfer_log', data.transfer_log);
    }

    // NFS
    if (configs.nfs && configs.nfs.success) {
        const data = configs.nfs.data;
        setCheckbox('nfs_enable', data.enable);
        setValue('nfs_max_protocol', data.nfsv4 ? '4' : '3');
    }

    // FTP
    if (configs.ftp && configs.ftp.success) {
        const data = configs.ftp.data;
        setCheckbox('ftp_enable', data.enable_ftp);
        setCheckbox('ftp_enable_ftps', data.enable_ftps);
        setCheckbox('ftp_enable_sftp', data.enable_sftp);
        setValue('ftp_timeout', data.timeout);
        setValue('ftp_port', data.port);
        setValue('ftp_pasv_min', data.pasv_min_port);
        setValue('ftp_pasv_max', data.pasv_max_port);
        setCheckbox('ftp_enable_fxp', data.enable_fxp);
        setCheckbox('ftp_enable_ascii', data.enable_ascii);
        setValue('ftp_utf8_encoding', data.utf8_encoding);
    }

    // rsync
    if (configs.rsync && configs.rsync.success) {
        const data = configs.rsync.data;
        setCheckbox('rsync_enable', data.enable);
        setValue('rsync_ssh_port', data.ssh_port);
        setCheckbox('rsync_enable_account', data.enable_rsync_account);
    }

    // Advanced
    if (configs.advanced && configs.advanced.success) {
        const data = configs.advanced.data;
        setCheckbox('adv_fast_clone', data.enable_fast_clone);
        setCheckbox('adv_bonjour_enable', data.enable_bonjour);
        setCheckbox('adv_bonjour_printer', data.enable_bonjour_printer);
        setCheckbox('adv_bonjour_tm_smb', data.enable_bonjour_timemachine_smb);
        setCheckbox('adv_bonjour_tm_afp', data.enable_bonjour_timemachine_afp);
        setCheckbox('adv_ssdp_enable', data.enable_ssdp);
        setCheckbox('adv_tftp_enable', data.enable_tftp);
        setValue('adv_tftp_root', data.tftp_root);
        setCheckbox('adv_skip_traversal', data.enable_traversal_check);
    }
}

// ============================================
// GUARDAR CONFIGURACIONES
// ============================================

async function saveAllConfigs() {
    const saveButton = document.querySelector('.action-button.primary');
    saveButton.disabled = true;
    saveButton.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Guardando...';

    try {
        // Recopilar datos de todos los formularios
        const smbData = getFormData('form-smb');
        const afpData = getFormData('form-afp');
        const nfsData = getFormData('form-nfs');
        const ftpData = getFormData('form-ftp');
        const rsyncData = getFormData('form-rsync');
        const advancedData = getFormData('form-advanced');

        // Guardar cada configuración
        const results = await Promise.all([
            saveConfig('/servicios-archivos/api/smb/update/', smbData),
            saveConfig('/servicios-archivos/api/afp/update/', afpData),
            saveConfig('/servicios-archivos/api/nfs/update/', nfsData),
            saveConfig('/servicios-archivos/api/ftp/update/', ftpData),
            saveConfig('/servicios-archivos/api/rsync/update/', rsyncData),
            saveConfig('/servicios-archivos/api/advanced/update/', advancedData)
        ]);

        // Verificar si todos fueron exitosos
        const allSuccess = results.every(r => r.success);

        if (allSuccess) {
            Swal.fire({
                icon: 'success',
                title: '¡Configuraciones guardadas!',
                text: 'Todas las configuraciones se guardaron correctamente.',
                timer: 2000,
                showConfirmButton: false
            });
        } else {
            const errors = results.filter(r => !r.success).map(r => r.message).join('\n');
            Swal.fire({
                icon: 'warning',
                title: 'Algunas configuraciones no se guardaron',
                text: errors,
                confirmButtonColor: '#00bcd4'
            });
        }
    } catch (error) {
        console.error('Error guardando configuraciones:', error);
        Swal.fire({
            icon: 'error',
            title: 'Error',
            text: 'Hubo un error al guardar las configuraciones',
            confirmButtonColor: '#00bcd4'
        });
    } finally {
        saveButton.disabled = false;
        saveButton.innerHTML = '<i class="fas fa-check mr-2"></i>Aplicar';
    }
}

async function saveConfig(url, data) {
    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify(data)
        });

        return await response.json();
    } catch (error) {
        return { success: false, message: error.toString() };
    }
}

function resetForm() {
    if (confirm('¿Desea restablecer todas las configuraciones a los valores originales?')) {
        loadAllConfigs();
    }
}

// ============================================
// UTILIDADES DE FORMULARIO
// ============================================

function getFormData(formId) {
    const form = document.getElementById(formId);
    if (!form) return {};

    const data = {};
    const inputs = form.querySelectorAll('input, select, textarea');

    inputs.forEach(input => {
        if (input.type === 'checkbox') {
            data[input.name] = input.checked;
        } else if (input.type === 'radio') {
            if (input.checked) {
                data[input.name] = input.value;
            }
        } else {
            data[input.name] = input.value;
        }
    });

    return data;
}

function setCheckbox(id, value) {
    const checkbox = document.getElementById(id);
    if (checkbox) {
        checkbox.checked = !!value;
    }
}

function setValue(id, value) {
    const input = document.getElementById(id);
    if (input && value !== undefined && value !== null) {
        input.value = value;
    }
}

// ============================================
// ACCIONES ESPECÍFICAS
// ============================================

function openLogSettings(service) {
    Swal.fire({
        title: `Configuración de registros - ${service.toUpperCase()}`,
        html: `
            <div class="text-left">
                <p class="mb-3">Configure las opciones de registro para el servicio ${service.toUpperCase()}.</p>
                <label class="flex items-center mb-2">
                    <input type="checkbox" class="mr-2" checked> Registrar todas las conexiones
                </label>
                <label class="flex items-center mb-2">
                    <input type="checkbox" class="mr-2"> Registrar solo errores
                </label>
            </div>
        `,
        showCancelButton: true,
        confirmButtonText: 'Guardar',
        cancelButtonText: 'Cancelar',
        confirmButtonColor: '#00bcd4'
    });
}

function viewLogs(service) {
    Swal.fire({
        title: `Registros de ${service.toUpperCase()}`,
        html: `
            <div class="text-left bg-gray-900 text-green-400 p-4 rounded font-mono text-xs max-h-96 overflow-y-auto">
                <div>[2026-01-18 12:00:00] Servicio ${service} iniciado</div>
                <div>[2026-01-18 12:15:32] Conexión desde 192.168.1.100</div>
                <div>[2026-01-18 12:20:45] Transferencia completada: 1024 MB</div>
                <div class="text-gray-500">--- Modo offline: Registros simulados ---</div>
            </div>
        `,
        width: '600px',
        confirmButtonText: 'Cerrar',
        confirmButtonColor: '#00bcd4'
    });
}

function openAdvancedSettings(service) {
    // TODO: Implementar configuraciones avanzadas específicas por servicio
    // Requiere APIs adicionales de Synology para cada servicio
    Swal.fire({
        title: `Configuración avanzada - ${service.toUpperCase()}`,
        html: `
            <div class="text-left">
                <p class="mb-3 text-sm text-gray-700">
                    <i class="fas fa-info-circle text-blue-500 mr-2"></i>
                    Las configuraciones avanzadas de ${service.toUpperCase()} incluyen:
                </p>
                <ul class="text-sm text-gray-600 ml-6 list-disc space-y-1">
                    <li>Opciones de rendimiento y caché</li>
                    <li>Configuración de protocolos específicos</li>
                    <li>Límites y restricciones adicionales</li>
                    <li>Opciones de compatibilidad</li>
                </ul>
                <div class="mt-4 p-3 bg-yellow-50 border-l-4 border-yellow-400 rounded">
                    <p class="text-xs text-yellow-800">
                        <strong>Nota:</strong> Esta funcionalidad requiere conexión al NAS real.
                        Será completamente funcional cuando <code>NAS_OFFLINE_MODE=False</code>.
                    </p>
                </div>
            </div>
        `,
        confirmButtonText: 'Entendido',
        confirmButtonColor: '#00bcd4',
        width: '500px'
    });
}

async function configureAggregationPortal() {
    // Portal de agregación SMB - Mejora rendimiento en redes multi-NIC
    const { value: formValues } = await Swal.fire({
        title: 'Portal de Agregación SMB',
        html: `
            <div class="text-left space-y-4">
                <div class="p-3 bg-blue-50 border-l-4 border-blue-400 rounded mb-4">
                    <p class="text-xs text-blue-800">
                        El portal de agregación permite combinar múltiples interfaces de red
                        para mejorar el rendimiento y la redundancia de SMB.
                    </p>
                </div>
                
                <div>
                    <label class="flex items-center mb-2 cursor-pointer">
                        <input type="checkbox" id="enable_aggregation" class="mr-2">
                        <span class="text-sm font-medium">Habilitar portal de agregación</span>
                    </label>
                </div>
                
                <div>
                    <label class="block text-sm font-medium mb-2">Puerto del portal:</label>
                    <input type="number" id="aggregation_port" value="445" 
                           class="w-full px-3 py-2 border rounded" 
                           placeholder="445">
                    <p class="text-xs text-gray-500 mt-1">Puerto predeterminado: 445 (SMB)</p>
                </div>
                
                <div class="text-xs text-gray-600 mt-3">
                    <i class="fas fa-exclamation-triangle text-yellow-500 mr-1"></i>
                    Requiere múltiples NICs configuradas en el NAS
                </div>
            </div>
        `,
        showCancelButton: true,
        confirmButtonText: 'Guardar',
        cancelButtonText: 'Cancelar',
        confirmButtonColor: '#00bcd4',
        width: '500px',
        preConfirm: () => {
            return {
                enable: document.getElementById('enable_aggregation').checked,
                port: document.getElementById('aggregation_port').value
            };
        }
    });

    if (formValues) {
        // TODO: BACKEND PENDIENTE - Requiere endpoint /servicios-archivos/api/smb/aggregation/update/
        // TODO: Investigar API real: Posible SYNO.Core.FileServ.SMB con parámetros de agregación
        // TODO: Implementar en file_services_service.py: set_aggregation_portal(enable, port)
        // ESTADO: Solo guarda en consola, NO persiste en NAS
        console.log('Configuración de agregación:', formValues);
        showMessage('⚠️ Configuración guardada solo en memoria (requiere implementación de backend)', 'info');
    }
}

async function openConnectionRestriction() {
    // Restricciones de IP/firewall para FTP
    const { value: formValues } = await Swal.fire({
        title: 'Restricción de Conexión FTP',
        html: `
            <div class="text-left space-y-4">
                <div class="p-3 bg-blue-50 border-l-4 border-blue-400 rounded mb-4">
                    <p class="text-xs text-blue-800">
                        Configure qué direcciones IP pueden conectarse al servicio FTP.
                    </p>
                </div>
                
                <div>
                    <label class="block text-sm font-medium mb-2">Modo de restricción:</label>
                    <select id="restriction_mode" class="w-full px-3 py-2 border rounded">
                        <option value="none">Sin restricciones (permitir todas)</option>
                        <option value="whitelist">Lista blanca (solo IPs permitidas)</option>
                        <option value="blacklist">Lista negra (bloquear IPs específicas)</option>
                    </select>
                </div>
                
                <div>
                    <label class="block text-sm font-medium mb-2">
                        Direcciones IP (una por línea):
                    </label>
                    <textarea id="ip_list" rows="5" 
                              class="w-full px-3 py-2 border rounded font-mono text-sm"
                              placeholder="192.168.1.100&#10;192.168.1.0/24&#10;10.0.0.0/8"></textarea>
                    <p class="text-xs text-gray-500 mt-1">
                        Soporta IPs individuales (192.168.1.100) o rangos CIDR (192.168.1.0/24)
                    </p>
                </div>
                
                <div>
                    <label class="flex items-center cursor-pointer">
                        <input type="checkbox" id="log_blocked" class="mr-2">
                        <span class="text-sm">Registrar intentos bloqueados</span>
                    </label>
                </div>
            </div>
        `,
        showCancelButton: true,
        confirmButtonText: 'Aplicar Restricciones',
        cancelButtonText: 'Cancelar',
        confirmButtonColor: '#00bcd4',
        width: '550px',
        preConfirm: () => {
            const ipList = document.getElementById('ip_list').value
                .split('\n')
                .map(ip => ip.trim())
                .filter(ip => ip.length > 0);

            return {
                mode: document.getElementById('restriction_mode').value,
                ip_list: ipList,
                log_blocked: document.getElementById('log_blocked').checked
            };
        }
    });

    if (formValues) {
        // TODO: BACKEND PENDIENTE - Requiere endpoint /servicios-archivos/api/ftp/restrictions/update/
        // TODO: Investigar API real: Posible SYNO.Core.Security.Firewall o SYNO.Core.FileServ.FTP.IPFilter
        // TODO: Implementar en file_services_service.py: set_ftp_restrictions(mode, ip_list, log_blocked)
        // ESTADO: Solo guarda en consola, NO persiste en NAS
        console.log('Restricción de conexión:', formValues);
        showMessage('⚠️ Restricciones guardadas solo en memoria (requiere implementación de backend)', 'info');
    }
}

async function editRsyncAccount() {
    // Cargar datos actuales si estamos conectados al NAS
    let currentData = { username: '', password: '' };

    try {
        const response = await fetch('/servicios-archivos/api/rsync/account/');
        if (response.ok) {
            currentData = await response.json();
        }
    } catch (error) {
        console.log('Modo offline - usando datos vacíos');
    }

    const { value: formValues } = await Swal.fire({
        title: 'Editar Cuenta rsync',
        html: `
            <div class="text-left space-y-4">
                <div class="p-3 bg-blue-50 border-l-4 border-blue-400 rounded mb-4">
                    <p class="text-xs text-blue-800">
                        Las cuentas rsync permiten que usuarios externos realicen copias de
                        seguridad sin necesidad de tener acceso completo al NAS.
                    </p>
                </div>
                
                <div>
                    <label class="block text-sm font-medium mb-2">Usuario rsync:</label>
                    <input type="text" id="rsync_username" 
                           class="w-full px-3 py-2 border rounded" 
                           placeholder="rsync_user"
                           value="${currentData.username || ''}">
                </div>
                
                <div>
                    <label class="block text-sm font-medium mb-2">Contraseña:</label>
                    <input type="password" id="rsync_password" 
                           class="w-full px-3 py-2 border rounded"
                           placeholder="Dejar en blanco para no cambiar">
                </div>
                
                <div>
                    <label class="block text-sm font-medium mb-2">Repetir contraseña:</label>
                    <input type="password" id="rsync_password_confirm" 
                           class="w-full px-3 py-2 border rounded">
                </div>
                
                <div class="text-xs text-gray-600">
                    <i class="fas fa-info-circle mr-1"></i>
                    Esta cuenta es independiente de las cuentas de usuario de DSM
                </div>
            </div>
        `,
        showCancelButton: true,
        confirmButtonText: 'Guardar',
        cancelButtonText: 'Cancelar',
        confirmButtonColor: '#00bcd4',
        width: '500px',
        preConfirm: () => {
            const username = document.getElementById('rsync_username').value;
            const password = document.getElementById('rsync_password').value;
            const passwordConfirm = document.getElementById('rsync_password_confirm').value;

            if (!username) {
                Swal.showValidationMessage('El nombre de usuario es obligatorio');
                return false;
            }

            if (password && password !== passwordConfirm) {
                Swal.showValidationMessage('Las contraseñas no coinciden');
                return false;
            }

            return { username, password };
        }
    });

    if (formValues) {
        try {
            // TODO: BACKEND PENDIENTE - Crear endpoint /servicios-archivos/api/rsync/account/update/
            // TODO: Implementar get_rsync_account() y set_rsync_account() en file_services_service.py
            // TODO: Investigar API: SYNO.Core.FileServ.Rsync.Account
            const response = await fetch('/servicios-archivos/api/rsync/account/update/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify(formValues)
            });

            const result = await response.json();
            showMessage(result.message || 'Cuenta rsync actualizada', 'success');
        } catch (error) {
            // ESTADO ACTUAL: Endpoint no existe, solo guarda en consola
            console.log('⚠️ Modo offline - Cuenta rsync:', formValues);
            showMessage('⚠️ Cuenta guardada solo en memoria (requiere implementación de backend)', 'info');
        }
    }
}

async function configureTimeMachineFolders() {
    // Cargar carpetas compartidas disponibles
    let folders = [];
    try {
        const response = await fetch('/grupos/api/shares/');
        folders = await response.json();
    } catch (error) {
        // Datos simulados si estamos offline
        folders = [
            { id: 1, name: 'Backups', path: '/volume1/backups' },
            { id: 2, name: 'TimeMachine', path: '/volume1/timemachine' },
            { id: 3, name: 'Compartido', path: '/volume1/compartido' }
        ];
    }

    const folderOptions = folders.map(f =>
        `<option value="${f.id}">${f.name} (${f.path || ''})</option>`
    ).join('');

    const { value: formValues } = await Swal.fire({
        title: 'Carpetas de Time Machine',
        html: `
            <div class="text-left space-y-4">
                <div class="p-3 bg-blue-50 border-l-4 border-blue-400 rounded mb-4">
                    <p class="text-xs text-blue-800">
                        <i class="fab fa-apple mr-1"></i>
                        Seleccione las carpetas que los usuarios de Mac podrán usar
                        como destino de Time Machine para sus copias de seguridad.
                    </p>
                </div>
                
                <div>
                    <label class="block text-sm font-medium mb-2">
                        Carpetas disponibles para Time Machine:
                    </label>
                    <select id="tm_folders" multiple size="6" 
                            class="w-full px-3 py-2 border rounded">
                        ${folderOptions}
                    </select>
                    <p class="text-xs text-gray-500 mt-1">
                        Mantén Ctrl/Cmd presionado para seleccionar múltiples carpetas
                    </p>
                </div>
                
                <div>
                    <label class="flex items-center cursor-pointer">
                        <input type="checkbox" id="tm_auto_delete" class="mr-2" checked>
                        <span class="text-sm">Eliminar automáticamente backups antiguos</span>
                    </label>
                </div>
            </div>
        `,
        showCancelButton: true,
        confirmButtonText: 'Aplicar',
        cancelButtonText: 'Cancelar',
        confirmButtonColor: '#00bcd4',
        width: '550px',
        preConfirm: () => {
            const select = document.getElementById('tm_folders');
            const selected = Array.from(select.selectedOptions).map(opt => ({
                id: opt.value,
                name: opt.text
            }));

            return {
                folders: selected,
                auto_delete: document.getElementById('tm_auto_delete').checked
            };
        }
    });

    if (formValues) {
        // TODO: BACKEND PENDIENTE - Requiere endpoint para configurar Time Machine
        // TODO: Investigar API: SYNO.Core.FileServ.AFP.TimeMachine o configuración de carpetas
        // TODO: Implementar set_timemachine_folders(folder_ids, auto_delete)
        // ESTADO: Solo guarda en consola, NO persiste en NAS
        console.log('⚠️ Time Machine folders (no persistente):', formValues);
        showMessage(`⚠️ ${formValues.folders.length} carpeta(s) seleccionada(s) (solo en memoria)`, 'info');
    }
}

async function selectTFTPFolder() {
    // Cargar árbol de carpetas del NAS
    let folderTree = [];
    try {
        const response = await fetch('/grupos/api/shares/');
        folderTree = await response.json();
    } catch (error) {
        // Datos simulados
        folderTree = [
            { name: 'Compartido', path: '/volume1/compartido' },
            { name: 'home', path: '/volume1/home' },
            { name: 'homes', path: '/volume1/homes' },
            { name: 'public', path: '/volume1/public' }
        ];
    }

    const folderList = folderTree.map(f =>
        `<div class="ml-4 mb-1 cursor-pointer hover:bg-gray-100 p-1 rounded" 
              onclick="this.classList.toggle('bg-blue-100')" 
              data-path="${f.path}">
            ▸ ${f.name}
         </div>`
    ).join('');

    const { value: selectedPath } = await Swal.fire({
        title: 'Seleccionar Carpeta Root TFTP',
        html: `
            <div class="text-left">
                <div class="mb-3 flex gap-2">
                    <button class="px-3 py-1 bg-gray-200 hover:bg-gray-300 rounded text-sm" 
                            onclick="alert('Actualizar árbol de carpetas')">
                        <i class="fas fa-sync-alt mr-1"></i>Actualizar
                    </button>
                    <button class="px-3 py-1 bg-gray-200 hover:bg-gray-300 rounded text-sm"
                            onclick="alert('Crear nueva carpeta')">
                        <i class="fas fa-folder-plus mr-1"></i>Crear carpeta
                    </button>
                </div>
                <div class="border rounded p-3 max-h-64 overflow-y-auto bg-white">
                    <div class="mb-2 font-medium">▼ NAS</div>
                    ${folderList}
                </div>
                <p class="text-xs text-gray-500 mt-2">
                    <i class="fas fa-info-circle mr-1"></i>
                    Haga clic en una carpeta para seleccionarla
                </p>
            </div>
        `,
        showCancelButton: true,
        confirmButtonText: 'Seleccionar',
        cancelButtonText: 'Cancelar',
        confirmButtonColor: '#00bcd4',
        width: '500px',
        preConfirm: () => {
            const selected = document.querySelector('.bg-blue-100');
            if (!selected) {
                Swal.showValidationMessage('Por favor seleccione una carpeta');
                return false;
            }
            return selected.getAttribute('data-path');
        }
    });

    if (selectedPath) {
        document.getElementById('adv_tftp_root').value = selectedPath;
        showMessage(`Carpeta TFTP: ${selectedPath}`, 'success');
    }
}

function openTaskList() {
    // Lista de tareas de rsync programadas
    Swal.fire({
        title: 'Lista de Tareas de Sincronización rsync',
        html: `
            <div class="text-left">
                <div class="mb-4">
                    <button class="px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700">
                        <i class="fas fa-plus mr-2"></i>Nueva tarea
                    </button>
                </div>
                
                <div class="border rounded overflow-hidden">
                    <table class="w-full text-sm">
                        <thead class="bg-gray-100">
                            <tr>
                                <th class="px-3 py-2 text-left">Nombre</th>
                                <th class="px-3 py-2 text-left">Origen</th>
                                <th class="px-3 py-2 text-left">Destino</th>
                                <th class="px-3 py-2 text-left">Estado</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr class="border-t">
                                <td colspan="4" class="px-3 py-4 text-center text-gray-500">
                                    <i class="fas fa-info-circle mr-2"></i>
                                    No hay tareas programadas
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                
                <div class="mt-4 p-3 bg-yellow-50 border-l-4 border-yellow-400 rounded">
                    <p class="text-xs text-yellow-800">
                        <strong>Nota:</strong> Las tareas se cargarán del NAS cuando 
                        <code>NAS_OFFLINE_MODE=False</code>
                    </p>
                </div>
            </div>
        `,
        confirmButtonText: 'Cerrar',
        confirmButtonColor: '#00bcd4',
        width: '700px'
    });
}

// ============================================
// UTILIDADES
// ============================================

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function showMessage(message, type = 'info') {
    const icon = type === 'error' ? 'error' : type === 'success' ? 'success' : 'info';
    Swal.fire({
        icon: icon,
        title: message,
        toast: true,
        position: 'top-end',
        showConfirmButton: false,
        timer: 3000
    });
}

// ============================================
// INICIALIZACIÓN
// ============================================

document.addEventListener('DOMContentLoaded', function () {
    // Cargar configuraciones al iniciar
    loadAllConfigs();

    // Abrir todos los acordeones por defecto (opcional)
    document.querySelectorAll('.collapsible-body.open').forEach(body => {
        const header = body.previousElementSibling;
        const icon = header.querySelector('i.fa-chevron-down');
        if (icon) {
            icon.style.transform = 'rotate(180deg)';
        }
    });
});
