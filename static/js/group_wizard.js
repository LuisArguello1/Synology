/**
 * GROUP_WIZARD.JS
 * 
 * Controla el wizard modal de creación de grupos (7 pasos).
 * Maneja navegación, validaciones, carga de datos via AJAX,
 * y envío final del formulario.
 */

// Estado global del wizard
let currentStep = 1;
const totalSteps = 7;
const wizardData = {
    name: '',
    description: '',
    members: [],
    folder_permissions: {},
    quotas: {},
    app_permissions: {},
    speed_limits: {}
};

// Datos cargados de las APIs
let availableUsers = [];
let availableFolders = [];
let availableVolumes = [];
let availableApps = [];

// ============================================
// FUNCIONES DE NAVEGACIÓN DEL WIZARD
// ============================================

let wizardMode = 'create'; // 'create' or 'edit'
let selectedGroupName = null;

async function openWizard(mode = 'create', groupName = null) {
    wizardMode = mode;
    selectedGroupName = groupName;
    currentStep = 1;
    resetWizardData();

    if (mode === 'edit') {
        document.getElementById('wizardTitle').textContent = 'Editar Grupo: ' + groupName;
        await loadGroupData(groupName);
    } else {
        document.getElementById('wizardTitle').textContent = 'Crear Nuevo Grupo';
    }

    document.getElementById('wizardModal').classList.remove('hidden');
    renderStep(1);
}

async function loadGroupData(groupName) {
    try {
        const response = await fetch(`/grupos/api/detail/${groupName}/`);
        const result = await response.json();

        if (result.success) {
            const data = result.data;
            wizardData.name = data.name;
            wizardData.description = data.description || data.desc || '';

            // Miembros: asegurar que es una lista de IDs/Nombres
            if (data.members) {
                wizardData.members = Array.isArray(data.members) ? data.members : [];
            }

            // Permisos de carpetas (puede venir en data.perm)
            if (data.perm) {
                // Synology suele devolver perms como array de objetos
                // Pero nuestro wizardData lo usa como dict {id: perm}
                // Si es simulación, ya viene como folder_permissions
                if (data.folder_permissions) {
                    wizardData.folder_permissions = data.folder_permissions;
                }
            }

            // Quotas (puede venir en data.quota)
            if (data.quotas) {
                wizardData.quotas = data.quotas;
            }

            // App permissions
            if (data.app_permissions) {
                wizardData.app_permissions = data.app_permissions;
            }

            // Speed limits
            if (data.speed_limits) {
                wizardData.speed_limits = data.speed_limits;
            }
        } else {
            showMessage(result.message || 'Error al cargar los datos del grupo', 'error');
        }
    } catch (error) {
        console.error('Error cargando datos del grupo:', error);
        showMessage('Error de conexión al cargar datos del grupo', 'error');
    }
}

function closeWizard() {
    if (confirm('¿Estás seguro de que deseas cerrar el asistente? Se perderán todos los datos ingresados.')) {
        document.getElementById('wizardModal').classList.add('hidden');
        resetWizardData();
    }
}

function nextStep() {
    // Validar paso actual
    if (!validateCurrentStep()) {
        return;
    }

    // Guardar datos del paso actual
    saveCurrentStepData();

    // Avanzar al siguiente paso
    currentStep++;
    renderStep(currentStep);
}

function previousStep() {
    // Guardar datos sin validar
    saveCurrentStepData();

    // Retroceder al paso anterior
    currentStep--;
    renderStep(currentStep);
}

function renderStep(step) {
    currentStep = step;

    // Actualizar indicador de paso
    document.getElementById('currentStepNumber').textContent = step;

    // Actualizar barra de progreso
    updateProgressBar(step);

    // Cargar contenido del paso
    const content = document.getElementById('wizardContent');
    const templateId = `step${step}Template`;
    const template = document.getElementById(templateId);

    if (template) {
        content.innerHTML = '';
        const clone = template.content.cloneNode(true);
        content.appendChild(clone);

        // Ejecutar lógica específica del paso
        initializeStep(step);
    }

    // Actualizar botones de navegación
    updateNavigationButtons(step);

    // Limpiar mensajes de error
    hideError();
}

function updateProgressBar(step) {
    // Resetear todos los pasos
    for (let i = 1; i <= totalSteps; i++) {
        const progressStep = document.getElementById(`progress-step-${i}`);
        if (i < step) {
            progressStep.className = 'flex-1 text-center text-xs text-green-600 font-medium';
        } else if (i === step) {
            progressStep.className = 'flex-1 text-center text-xs text-indigo-600 font-medium';
        } else {
            progressStep.className = 'flex-1 text-center text-xs text-gray-400';
        }
    }
}

function updateNavigationButtons(step) {
    const btnPrevious = document.getElementById('btnPrevious');
    const btnNext = document.getElementById('btnNext');
    const btnFinish = document.getElementById('btnFinish');

    // Botón "Anterior"
    if (step === 1) {
        btnPrevious.classList.add('hidden');
    } else {
        btnPrevious.classList.remove('hidden');
    }

    // Botones "Siguiente" y "Finalizar"
    if (step === totalSteps) {
        btnNext.classList.add('hidden');
        btnFinish.classList.remove('hidden');
    } else {
        btnNext.classList.remove('hidden');
        btnFinish.classList.add('hidden');
    }
}

// ============================================
// INICIALIZACIÓN DE CADA PASO
// ============================================

function initializeStep(step) {
    switch (step) {
        case 1:
            initStep1();
            break;
        case 2:
            initStep2();
            break;
        case 3:
            initStep3();
            break;
        case 4:
            initStep4();
            break;
        case 5:
            initStep5();
            break;
        case 6:
            initStep6();
            break;
        case 7:
            initStep7();
            break;
    }
}

// PASO 1: Información básica
function initStep1() {
    document.getElementById('groupName').value = wizardData.name;
    document.getElementById('groupDescription').value = wizardData.description;
}

// PASO 2: Seleccionar miembros
async function initStep2() {
    if (availableUsers.length === 0) {
        await loadUsers();
    }
    renderUsersTable(availableUsers);

    // Búsqueda en tiempo real
    document.getElementById('userSearch').addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase();
        const filtered = availableUsers.filter(user =>
            user.username.toLowerCase().includes(query) ||
            user.email.toLowerCase().includes(query) ||
            user.full_name.toLowerCase().includes(query)
        );
        renderUsersTable(filtered);
    });
}

// PASO 3: Permisos de carpetas
async function initStep3() {
    if (availableFolders.length === 0) {
        await loadFolders();
    }
    renderFoldersTable();
}

// PASO 4: Cuotas
async function initStep4() {
    if (availableVolumes.length === 0) {
        await loadVolumes();
    }
    renderVolumesList();
}

// PASO 5: Permisos de aplicaciones
async function initStep5() {
    if (availableApps.length === 0) {
        await loadApplications();
    }
    renderAppsTable();
}

// PASO 6: Límites de velocidad
function initStep6() {
    // Restaurar valores si existen
    if (wizardData.speed_limits['file_station']) {
        document.getElementById('speedFileStationUp').value = wizardData.speed_limits['file_station'].upload || 0;
        document.getElementById('speedFileStationDown').value = wizardData.speed_limits['file_station'].download || 0;
    }
    if (wizardData.speed_limits['ftp']) {
        document.getElementById('speedFTPUp').value = wizardData.speed_limits['ftp'].upload || 0;
        document.getElementById('speedFTPDown').value = wizardData.speed_limits['ftp'].download || 0;
    }
    if (wizardData.speed_limits['rsync']) {
        document.getElementById('speedRsyncUp').value = wizardData.speed_limits['rsync'].upload || 0;
        document.getElementById('speedRsyncDown').value = wizardData.speed_limits['rsync'].download || 0;
    }
}

// PASO 7: Confirmación
function initStep7() {
    // Mostrar resumen completo
    document.getElementById('summaryName').textContent = wizardData.name;
    document.getElementById('summaryDesc').textContent = wizardData.description || 'Sin descripción';

    // Miembros
    const memberNames = wizardData.members.map(id => {
        const user = availableUsers.find(u => u.id === id);
        return user ? user.username : id;
    });
    document.getElementById('summaryMembers').textContent = memberNames.length > 0
        ? memberNames.join(', ')
        : 'Sin miembros';

    // Permisos de carpetas
    const folderPerms = Object.entries(wizardData.folder_permissions).map(([id, perm]) => {
        const folder = availableFolders.find(f => f.id == id);
        const permLabel = perm === 'rw' ? 'R/W' : perm === 'ro' ? 'Solo lectura' : 'Sin acceso';
        return `${folder ? folder.name : id}: ${permLabel}`;
    });
    document.getElementById('summaryFolders').textContent = folderPerms.length > 0
        ? folderPerms.join(', ')
        : 'Sin configuración';

    // Cuotas
    const quotasList = Object.entries(wizardData.quotas).map(([id, quota]) => {
        const volume = availableVolumes.find(v => v.id == id);
        return `${volume ? volume.name : id}: ${quota.amount} ${quota.unit}`;
    });
    document.getElementById('summaryQuotas').textContent = quotasList.length > 0
        ? quotasList.join(', ')
        : 'Sin cuotas';

    // Aplicaciones
    const appPerms = Object.entries(wizardData.app_permissions).map(([name, perm]) => {
        return `${name}: ${perm === 'allow' ? 'Permitir' : 'Denegar'}`;
    });
    document.getElementById('summaryApps').textContent = appPerms.length > 0
        ? appPerms.join(', ')
        : 'Sin configuración';

    // Límites de velocidad
    const speedLimits = Object.entries(wizardData.speed_limits).map(([service, limits]) => {
        return `${service}: ↑${limits.upload} ↓${limits.download} KB/s`;
    });
    document.getElementById('summarySpeed').textContent = speedLimits.length > 0
        ? speedLimits.join(', ')
        : 'Sin límites';
}

// ============================================
// GUARDAR DATOS DE CADA PASO
// ============================================

function saveCurrentStepData() {
    switch (currentStep) {
        case 1:
            wizardData.name = document.getElementById('groupName').value.trim();
            wizardData.description = document.getElementById('groupDescription').value.trim();
            break;

        case 2:
            // Los miembros ya se guardan en tiempo real al hacer check/uncheck
            break;

        case 3:
            // Los permisos de carpetas ya se guardan en tiempo real
            break;

        case 4:
            // Las cuotas ya se guardan en tiempo real
            break;

        case 5:
            // Los permisos de apps ya se guardan en tiempo real
            break;

        case 6:
            wizardData.speed_limits = {
                'file_station': {
                    upload: parseInt(document.getElementById('speedFileStationUp').value) || 0,
                    download: parseInt(document.getElementById('speedFileStationDown').value) || 0
                },
                'ftp': {
                    upload: parseInt(document.getElementById('speedFTPUp').value) || 0,
                    download: parseInt(document.getElementById('speedFTPDown').value) || 0
                },
                'rsync': {
                    upload: parseInt(document.getElementById('speedRsyncUp').value) || 0,
                    download: parseInt(document.getElementById('speedRsyncDown').value) || 0
                }
            };
            break;
    }
}

// ============================================
// VALIDACIONES
// ============================================

function validateCurrentStep() {
    hideError();

    switch (currentStep) {
        case 1:
            const name = document.getElementById('groupName').value.trim();
            if (!name) {
                Swal.fire({
                    icon: 'error',
                    title: 'Campo requerido',
                    text: 'El nombre del grupo es obligatorio.',
                    confirmButtonColor: '#4f46e5'
                });
                return false;
            }
            return true;

        case 2:
            // Es válido crear un grupo sin miembros 
            return true;

        default:
            return true;
    }
}

function showError(message) {
    const errorDiv = document.getElementById('errorMessage');
    errorDiv.textContent = message;
    errorDiv.classList.remove('hidden');
}

function hideError() {
    const errorDiv = document.getElementById('errorMessage');
    errorDiv.classList.add('hidden');
}

// ============================================
// CARGA DE DATOS VIA AJAX
// ============================================

async function loadUsers() {
    try {
        const response = await fetch('/grupos/api/users/');
        availableUsers = await response.json();
    } catch (error) {
        console.error('Error cargando usuarios:', error);
        showError('Error al cargar usuarios');
    }
}

async function loadFolders() {
    try {
        const response = await fetch('/grupos/api/shares/');
        availableFolders = await response.json();
    } catch (error) {
        console.error('Error cargando carpetas:', error);
        showError('Error al cargar carpetas compartidas');
    }
}

async function loadVolumes() {
    try {
        const response = await fetch('/grupos/api/volumes/');
        availableVolumes = await response.json();
    } catch (error) {
        console.error('Error cargando volúmenes:', error);
        showError('Error al cargar volúmenes');
    }
}

async function loadApplications() {
    try {
        const response = await fetch('/grupos/api/apps/');
        availableApps = await response.json();
    } catch (error) {
        console.error('Error cargando aplicaciones:', error);
        showError('Error al cargar aplicaciones');
    }
}

// ============================================
// RENDERIZADO DE TABLAS
// ============================================

function renderUsersTable(users) {
    const tbody = document.getElementById('usersList');
    if (users.length === 0) {
        tbody.innerHTML = '<tr><td colspan="3" class="px-3 py-4 text-center text-gray-500">No hay usuarios disponibles</td></tr>';
        return;
    }

    tbody.innerHTML = users.map(user => `
        <tr>
            <td class="px-3 py-2">${user.full_name}</td>
            <td class="px-3 py-2 text-gray-600">${user.email || 'Sin email'}</td>
            <td class="px-3 py-2 text-center">
                <input type="checkbox" 
                       value="${user.id}" 
                       ${wizardData.members.includes(user.id) ? 'checked' : ''}
                       onchange="toggleMember('${user.id}', this.checked)"
                       class="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500">
            </td>
        </tr>
    `).join('');

    updateMemberCount();
}

function toggleMember(userId, checked) {
    if (checked) {
        if (!wizardData.members.includes(userId)) {
            wizardData.members.push(userId);
        }
    } else {
        wizardData.members = wizardData.members.filter(id => id !== userId);
    }
    updateMemberCount();
}

function updateMemberCount() {
    const countElem = document.getElementById('selectedUsersCount');
    if (countElem) {
        countElem.textContent = wizardData.members.length;
    }
}

function renderFoldersTable() {
    const tbody = document.getElementById('foldersList');
    if (availableFolders.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="px-3 py-4 text-center text-gray-500">No hay carpetas compartidas</td></tr>';
        return;
    }

    tbody.innerHTML = availableFolders.map(folder => {
        const currentPerm = wizardData.folder_permissions[folder.id] || 'na';
        return `
            <tr>
                <td class="px-3 py-2 font-medium">${folder.name}</td>
                <td class="px-3 py-2 text-center">
                    <input type="radio" name="folder_${folder.id}" value="na" 
                           ${currentPerm === 'na' ? 'checked' : ''}
                           onchange="setFolderPermission('${folder.id}', 'na')"
                           class="text-gray-600 focus:ring-gray-500">
                </td>
                <td class="px-3 py-2 text-center">
                    <input type="radio" name="folder_${folder.id}" value="rw" 
                           ${currentPerm === 'rw' ? 'checked' : ''}
                           onchange="setFolderPermission('${folder.id}', 'rw')"
                           class="text-green-600 focus:ring-green-500">
                </td>
                <td class="px-3 py-2 text-center">
                    <input type="radio" name="folder_${folder.id}" value="ro" 
                           ${currentPerm === 'ro' ? 'checked' : ''}
                           onchange="setFolderPermission('${folder.id}', 'ro')"
                           class="text-blue-600 focus:ring-blue-500">
                </td>
            </tr>
        `;
    }).join('');
}

function setFolderPermission(folderId, permission) {
    wizardData.folder_permissions[folderId] = permission;
}


// ============================================
// LOGICA DE ACORDEÓN PARA CUOTAS (PASO 4)
// ============================================

function renderVolumesList() {
    const volumesDiv = document.getElementById('volumesList');
    if (availableVolumes.length === 0) {
        volumesDiv.innerHTML = '<p class="text-xs text-gray-500 text-center py-4">No hay volúmenes disponibles</p>';
        return;
    }

    volumesDiv.innerHTML = availableVolumes.map(volume => {
        const isSelected = selectedVolumeId === volume.id;
        const currentQuota = wizardData.quotas[volume.id];
        const hasQuota = currentQuota && (currentQuota.amount > 0 || currentQuota.is_unlimited === false); // is_unlimited false implica que se configuró algo

        // Valores para el formulario interno
        const amount = currentQuota ? currentQuota.amount : '';
        const unit = currentQuota ? currentQuota.unit : 'GB';
        // Por defecto es ilimitado si no existe configuración previa
        const isUnlimited = currentQuota ? currentQuota.is_unlimited : true;

        return `
        <div class="border rounded-md mb-3 overflow-hidden transition-all duration-200 ${isSelected ? 'border-indigo-500 ring-1 ring-indigo-500 bg-white shadow-sm' : 'border-gray-200 bg-white hover:bg-gray-50'}">
            
            <!-- HEADER DEL ACORDEÓN -->
            <div class="flex items-center justify-between p-3 cursor-pointer select-none" onclick="toggleVolumeAccordion('${volume.id}')">
                <div class="flex items-center">
                    <div class="bg-indigo-100 p-2 rounded-full mr-3 text-indigo-600">
                        <i class="fas fa-hdd"></i>
                    </div>
                    <div>
                        <h4 class="text-sm font-semibold text-gray-900">${volume.name}</h4>
                        <p class="text-xs text-gray-500 flex items-center gap-2">
                             <span>${volume.available_space} GB libres</span>
                             <span class="text-gray-300">|</span>
                             <span>Total ${volume.total_space} GB</span>
                        </p>
                    </div>
                </div>
                
                <div class="flex items-center">
                    ${hasQuota ? `<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800 mr-2"><i class="fas fa-check mr-1"></i>Configurado</span>` : ''}
                    <i class="fas fa-chevron-down text-gray-400 transform transition-transform duration-200 ${isSelected ? 'rotate-180' : ''}"></i>
                </div>
            </div>
            
            <!-- BODY DEL ACORDEÓN (FORMULARIO) -->
            <div id="volume_body_${volume.id}" class="${isSelected ? 'block' : 'hidden'} bg-gray-50 border-t border-gray-100 p-4">
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4 items-end">
                    
                    <!-- Checkbox Sin Límite -->
                    <div class="flex items-center h-10">
                        <input type="checkbox" id="noLimit_${volume.id}" 
                               class="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded cursor-pointer"
                               ${isUnlimited ? 'checked' : ''}
                               onchange="updateVolumeQuota('${volume.id}')">
                        <label for="noLimit_${volume.id}" class="ml-2 block text-sm text-gray-700 cursor-pointer">
                            Sin límite de cuota
                        </label>
                    </div>

                    <!-- Input de Cantidad -->
                    <div class="flex rounded-md shadow-sm">
                        <input type="number" id="amount_${volume.id}" 
                               class="focus:ring-indigo-500 focus:border-indigo-500 flex-1 block w-full text-sm border-gray-300 rounded-none rounded-l-md disabled:bg-gray-100 disabled:text-gray-400" 
                               placeholder="100"
                               min="0"
                               value="${(!amount && amount !== 0) ? '' : amount}"
                               ${isUnlimited ? 'disabled' : ''}
                               oninput="updateVolumeQuota('${volume.id}')">
                        <select id="unit_${volume.id}" 
                                class="focus:ring-indigo-500 focus:border-indigo-500 inline-flex items-center px-3 py-2 border border-l-0 border-gray-300 bg-gray-50 text-gray-500 text-sm rounded-r-md disabled:bg-gray-100"
                                ${isUnlimited ? 'disabled' : ''}
                                onchange="updateVolumeQuota(${volume.id})">
                            <option value="MB" ${unit === 'MB' ? 'selected' : ''}>MB</option>
                            <option value="GB" ${unit === 'GB' ? 'selected' : ''}>GB</option>
                            <option value="TB" ${unit === 'TB' ? 'selected' : ''}>TB</option>
                        </select>
                    </div>
                    
                </div>
                
                <p class="text-xs text-gray-500 mt-2">
                    <i class="fas fa-info-circle mr-1"></i>
                    La cuota limita el espacio que este grupo puede usar en el volumen <strong>${volume.name}</strong>.
                </p>
            </div>
        </div>
    `}).join('');
}

let selectedVolumeId = null;

function toggleVolumeAccordion(volumeId) {
    if (selectedVolumeId === volumeId) {
        selectedVolumeId = null;
    } else {
        selectedVolumeId = volumeId;
    }
    renderVolumesList();
}

function updateVolumeQuota(volumeId) {
    const noLimitCheck = document.getElementById(`noLimit_${volumeId}`);
    const amountInput = document.getElementById(`amount_${volumeId}`);
    const unitInput = document.getElementById(`unit_${volumeId}`);

    if (!noLimitCheck || !amountInput || !unitInput) return;

    const isUnlimited = noLimitCheck.checked;

    // Actualizar estado de inputs visualmente
    amountInput.disabled = isUnlimited;
    unitInput.disabled = isUnlimited;

    // Guardar en estructura de datos
    if (isUnlimited) {
        amountInput.value = '';
        wizardData.quotas[volumeId] = {
            amount: 0,
            unit: 'GB',
            is_unlimited: true
        };
    } else {
        const val = parseInt(amountInput.value);
        wizardData.quotas[volumeId] = {
            amount: isNaN(val) ? 0 : val,
            unit: unitInput.value,
            is_unlimited: false
        };
    }
}

function renderAppsTable() {
    const tbody = document.getElementById('appsList');
    if (availableApps.length === 0) {
        tbody.innerHTML = '<tr><td colspan="3" class="px-3 py-4 text-center text-gray-500">No hay aplicaciones disponibles</td></tr>';
        return;
    }

    tbody.innerHTML = availableApps.map(app => {
        const currentPerm = wizardData.app_permissions[app.name] || 'allow';
        return `
            <tr>
                <td class="px-3 py-2 font-medium">${app.name}</td>
                <td class="px-3 py-2 text-center">
                    <input type="radio" name="app_${app.id}" value="allow" 
                           ${currentPerm === 'allow' ? 'checked' : ''}
                           onchange="setAppPermission('${app.name}', 'allow')"
                           class="text-green-600 focus:ring-green-500">
                </td>
                <td class="px-3 py-2 text-center">
                    <input type="radio" name="app_${app.id}" value="deny" 
                           ${currentPerm === 'deny' ? 'checked' : ''}
                           onchange="setAppPermission('${app.name}', 'deny')"
                           class="text-red-600 focus:ring-red-500">
                </td>
            </tr>
        `;
    }).join('');
}

function setAppPermission(appName, permission) {
    wizardData.app_permissions[appName] = permission;
}

// ============================================
// ENVÍO FINAL
// ============================================

async function submitWizard() {
    const btnFinish = document.getElementById('btnFinish');
    btnFinish.disabled = true;
    btnFinish.innerHTML = '<i class="fas fa-spinner fa-spin mr-1.5"></i>Creando...';

    try {
        const response = await fetch('/grupos/api/create/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(wizardData)
        });

        const result = await response.json();

        if (response.ok && result.success) {
            // Cerrar modal
            document.getElementById('wizardModal').classList.add('hidden');

            // Mensaje de éxito
            Swal.fire({
                icon: 'success',
                title: '¡Éxito!',
                text: result.message || 'Operación completada correctamente.',
                timer: 1500,
                showConfirmButton: false
            }).then(() => {
                window.location.reload();
            });
        } else {
            showMessage(result.message || 'Error al crear el grupo', 'error');
            btnFinish.disabled = false;
            btnFinish.innerHTML = '<i class="fas fa-check mr-1.5"></i>Finalizar';
        }
    } catch (error) {
        console.error('Error:', error);
        showMessage('Error de conexión al crear el grupo', 'error');
        btnFinish.disabled = false;
        btnFinish.innerHTML = '<i class="fas fa-check mr-1.5"></i>Finalizar';
    }
}

// ============================================
// UTILIDADES
// ============================================

function resetWizardData() {
    currentStep = 1;
    wizardData.name = '';
    wizardData.description = '';
    wizardData.members = [];
    wizardData.folder_permissions = {};
    wizardData.quotas = {};
    wizardData.app_permissions = {};
    wizardData.speed_limits = {};

    availableUsers = [];
    availableFolders = [];
    availableVolumes = [];
    availableApps = [];
}
