/**
 * Lógica para actualizar métricas del dashboard vía AJAX.
 */
document.addEventListener('DOMContentLoaded', function () {

    const startUpdateBtn = document.getElementById('btn-refresh-metrics');
    if (startUpdateBtn) {
        startUpdateBtn.addEventListener('click', function (e) {
            e.preventDefault();
            updateDashboardMetrics();
        });
    }

    // Auto-refresh config (opcional, se puede llamar desde el template)
    window.startDashboardAutoRefresh = function (intervalMs = 30000) {
        setInterval(updateDashboardMetrics, intervalMs);
    };
});

async function updateDashboardMetrics() {
    const dashboardContainer = document.querySelector('.dashboard-container');
    // Si queremos mostrar feedback global de "actualizando", pero la idea es skeletons in-place.

    showSkeletons();

    try {
        const response = await fetch('/metrics/');
        if (!response.ok) throw new Error('Network response was not ok');
        const metrics = await response.json();

        // Simular un pequeño delay para que se aprecie el skeleton (opcional, UX)
        // await new Promise(r => setTimeout(r, 500)); 

        updateDOM(metrics);

    } catch (error) {
        console.error('Error updating metrics:', error);
        // Opcional: mostrar error en UI
    }
}

function showSkeletons() {
    // Selectores para métricas de sistema
    setHtml('metric-cpu', Skeleton.create('w-12 h-6'));
    setHtml('metric-ram', Skeleton.create('w-12 h-6'));
    setHtml('metric-temp', Skeleton.create('w-12 h-6'));
    setHtml('metric-uptime', Skeleton.create('w-8 h-6'));

    // Selectores para almacenamiento
    setHtml('metric-storage-used', Skeleton.create('w-16 h-4'));
    setHtml('metric-storage-percent', Skeleton.create('w-10 h-6'));

    // Sesiones
    setHtml('metric-sessions', Skeleton.create('w-6 h-4'));

    // Listas complejas - reemplazamos contenido con un par de items skeleton
    const eventList = document.getElementById('list-events');
    if (eventList) {
        eventList.innerHTML = `
            <div class="p-3">
                <div class="flex items-start gap-3">
                    ${Skeleton.circle('w-6 h-6')}
                    <div class="flex-1 space-y-2">
                        ${Skeleton.create('w-3/4 h-3')}
                        ${Skeleton.create('w-1/2 h-2')}
                    </div>
                </div>
            </div>
            <div class="p-3">
                <div class="flex items-start gap-3">
                    ${Skeleton.circle('w-6 h-6')}
                    <div class="flex-1 space-y-2">
                        ${Skeleton.create('w-2/3 h-3')}
                        ${Skeleton.create('w-1/3 h-2')}
                    </div>
                </div>
            </div>
        `;
    }

    const fileList = document.getElementById('list-files');
    if (fileList) {
        fileList.innerHTML = `
            <div class="p-3">
                <div class="flex items-center gap-3">
                    ${Skeleton.create('w-8 h-8 rounded')}
                    <div class="flex-1 space-y-1">
                        ${Skeleton.create('w-1/2 h-3')}
                        ${Skeleton.create('w-1/3 h-2')}
                    </div>
                </div>
            </div>
            <div class="p-3">
                <div class="flex items-center gap-3">
                    ${Skeleton.create('w-8 h-8 rounded')}
                    <div class="flex-1 space-y-1">
                        ${Skeleton.create('w-2/3 h-3')}
                        ${Skeleton.create('w-1/4 h-2')}
                    </div>
                </div>
            </div>
        `;
    }
}

function updateDOM(metrics) {
    // System
    setText('metric-cpu', metrics.system.cpu_usage);
    setWidth('bar-cpu', metrics.system.cpu_usage + '%');

    setText('metric-ram', metrics.system.memory_usage);
    setWidth('bar-ram', metrics.system.memory_usage + '%');

    setText('metric-temp', metrics.system.temperature);

    setText('metric-uptime', metrics.system.uptime_days);

    // Storage
    setText('metric-storage-used', `${metrics.storage.used} / ${metrics.storage.total}`);
    setText('metric-storage-percent', metrics.storage.percent_used + '%');

    // Bar Color Logic for Storage
    const storageBar = document.getElementById('bar-storage');
    if (storageBar) {
        storageBar.style.width = metrics.storage.percent_used + '%';
        // Reset colors
        storageBar.className = 'h-full transition-all duration-500';
        if (metrics.storage.percent_used >= 90) {
            storageBar.classList.add('bg-red-500');
        } else if (metrics.storage.percent_used >= 75) {
            storageBar.classList.add('bg-yellow-500');
        } else {
            storageBar.classList.add('bg-indigo-600');
        }
    }

    // Update Volumes List (Complex HTML generation)
    const volumesContainer = document.getElementById('grid-volumes');
    if (volumesContainer) {
        if (!metrics.storage.volumes || metrics.storage.volumes.length === 0) {
            volumesContainer.innerHTML = '<div class="col-span-2 py-6 text-center text-gray-400 text-[10px]">No se detectaron volúmenes</div>';
        } else {
            volumesContainer.innerHTML = metrics.storage.volumes.map(vol => `
                <div class="p-2.5 bg-gray-50/50 border border-gray-100 rounded-sm">
                    <div class="flex items-center justify-between mb-1.5">
                        <span class="text-[10px] font-bold text-gray-700">${vol.name}</span>
                        <span class="text-[9px] font-black text-gray-500">${vol.percent}%</span>
                    </div>
                    <div class="w-full bg-gray-200 rounded-full h-1 mb-1.5">
                        <div class="bg-gray-600 h-1 rounded-full" style="width: ${vol.percent}%"></div>
                    </div>
                    <div class="flex justify-between text-[9px] text-gray-400 font-medium">
                        <span>${vol.used} usados</span>
                        <span>${vol.total}</span>
                    </div>
                </div>
            `).join('');
        }
    }

    // Sessions
    setText('metric-sessions', metrics.connections.total);

    // Update Activity Logs
    const eventList = document.getElementById('list-events');
    if (eventList) {
        if (!metrics.activity || metrics.activity.length === 0) {
            eventList.innerHTML = '<div class="p-6 text-center text-gray-400 text-[10px]">Sin eventos recientes</div>';
        } else {
            eventList.innerHTML = metrics.activity.map(log => {
                let icon = '<i class="fas fa-info-circle text-blue-500 text-[10px]"></i>';
                if (log.level === 'err') icon = '<i class="fas fa-exclamation-circle text-red-500 text-[10px]"></i>';
                if (log.level === 'warn') icon = '<i class="fas fa-exclamation-triangle text-yellow-500 text-[10px]"></i>';

                return `
                <div class="p-3 hover:bg-gray-50/50 transition-colors">
                    <div class="flex items-start gap-3">
                        <div class="flex-shrink-0 mt-0.5">
                            ${icon}
                        </div>
                        <div class="flex-1 min-w-0">
                            <p class="text-[10.5px] font-medium text-gray-800 leading-normal">${log.msg}</p>
                            <div class="mt-0.5 flex items-center gap-2 text-[9px] text-gray-400">
                                <span class="font-bold text-gray-500 uppercase">${log.user}</span>
                                <span class="opacity-30">•</span>
                                <span>${log.time}</span>
                            </div>
                        </div>
                    </div>
                </div>`;
            }).join('');
        }
    }

    // Update Recent Files
    const fileList = document.getElementById('list-files');
    if (fileList) {
        if (!metrics.recent_files || metrics.recent_files.length === 0) {
            fileList.innerHTML = '<div class="p-8 text-center text-gray-400 text-[10px]">No hay archivos recientes</div>';
        } else {
            fileList.innerHTML = metrics.recent_files.map(file => {
                let iconClass = 'text-gray-300';
                let iconName = 'fa-file';

                const ext = file.ext;
                if (ext === 'pdf') { iconName = 'fa-file-pdf'; iconClass = 'text-red-500'; }
                else if (['zip', 'rar', '7z'].includes(ext)) { iconName = 'fa-file-archive'; iconClass = 'text-orange-400'; }
                else if (['jpg', 'png', 'gif', 'svg'].includes(ext)) { iconName = 'fa-file-image'; iconClass = 'text-purple-400'; }
                else if (['doc', 'docx'].includes(ext)) { iconName = 'fa-file-word'; iconClass = 'text-blue-500'; }
                else if (['xls', 'xlsx'].includes(ext)) { iconName = 'fa-file-excel'; iconClass = 'text-green-600'; }

                return `
                <div class="p-3 hover:bg-gray-50 transition-colors group">
                    <div class="flex items-center gap-3">
                        <div class="w-8 h-8 rounded bg-gray-50 flex items-center justify-center border border-gray-100 group-hover:bg-white transition-colors">
                            <i class="fas ${iconName} ${iconClass} text-[10px]"></i>
                        </div>
                        <div class="flex-1 min-w-0">
                            <p class="text-[11px] font-bold text-gray-800 truncate">${file.name}</p>
                            <p class="text-[9px] text-gray-400 truncate">${file.path}</p>
                        </div>
                        <div class="text-right">
                            <p class="text-[9px] font-black text-gray-600 tracking-tighter">${file.size}</p>
                            <p class="text-[8px] text-gray-400">${limitStr(file.time, 10)}</p>
                        </div>
                    </div>
                </div>`;
            }).join('');
        }
    }
}

// Helpers
function setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.innerText = value;
}

function setHtml(id, html) {
    const el = document.getElementById(id);
    if (el) el.innerHTML = html;
}

function setWidth(id, width) {
    const el = document.getElementById(id);
    if (el) el.style.width = width;
}

function limitStr(str, max) {
    if (!str) return '';
    return str.length > max ? str.substring(0, max) + '...' : str;
}
