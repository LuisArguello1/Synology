/**
 * Dashboard Premium - Charts and Metrics Logic
 * Especialista en visualización de datos NAS.
 */

class DashboardManager {
    constructor() {
        this.charts = {};
        this.historyLimit = 30; // 30 puntos de datos
        this.dataHistory = {
            cpu: Array(30).fill(0),
            ram: Array(30).fill(0),
            up: Array(30).fill(0),
            down: Array(30).fill(0),
            labels: Array(30).fill('')
        };
        this.refreshInterval = null;
    }

    init() {
        this.setupCharts();
        this.startPolling();

        // Listener para el botón de actualización manual
        const refreshBtn = document.getElementById('btn-refresh-metrics');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.fetchMetrics());
        }
    }

    setupCharts() {
        const commonOptions = {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 800, easing: 'easeOutQuart' },
            plugins: { legend: { display: false } },
            scales: {
                y: {
                    display: true,
                    position: 'right',
                    grid: { color: 'rgba(0,0,0,0.03)', drawBorder: false },
                    ticks: { display: false }
                },
                x: {
                    display: true,
                    grid: { color: 'rgba(0,0,0,0.03)', drawBorder: false },
                    ticks: { display: false }
                }
            },
            elements: {
                line: { tension: 0.3, borderWidth: 1.5, fill: true },
                point: { radius: 0 }
            }
        };

        // Chart CPU
        const cpuCtx = document.getElementById('chart-cpu')?.getContext('2d');
        if (cpuCtx) {
            this.charts.cpu = new Chart(cpuCtx, {
                type: 'line',
                data: {
                    labels: this.dataHistory.labels,
                    datasets: [{
                        data: this.dataHistory.cpu,
                        borderColor: '#3b82f6',
                        backgroundColor: 'rgba(59, 130, 246, 0.05)'
                    }]
                },
                options: commonOptions
            });
        }

        // Chart RAM
        const ramCtx = document.getElementById('chart-ram')?.getContext('2d');
        if (ramCtx) {
            this.charts.ram = new Chart(ramCtx, {
                type: 'line',
                data: {
                    labels: this.dataHistory.labels,
                    datasets: [{
                        data: this.dataHistory.ram,
                        borderColor: '#a855f7',
                        backgroundColor: 'rgba(168, 85, 247, 0.05)'
                    }]
                },
                options: commonOptions
            });
        }

        // Chart Network (Dual)
        const netCtx = document.getElementById('chart-network')?.getContext('2d');
        if (netCtx) {
            this.charts.network = new Chart(netCtx, {
                type: 'line',
                data: {
                    labels: this.dataHistory.labels,
                    datasets: [
                        {
                            label: 'Down',
                            data: this.dataHistory.down,
                            borderColor: '#10b981',
                            backgroundColor: 'rgba(16, 185, 129, 0.05)'
                        },
                        {
                            label: 'Up',
                            data: this.dataHistory.up,
                            borderColor: '#f59e0b',
                            backgroundColor: 'rgba(245, 158, 11, 0.05)'
                        }
                    ]
                },
                options: commonOptions
            });
        }
    }

    async fetchMetrics() {
        const btn = document.getElementById('btn-refresh-metrics');
        if (btn) btn.classList.add('animate-spin-once');

        try {
            // Fix: Correct URL from /api/dashboard/metrics/ to /metrics/
            const response = await fetch('/metrics/');
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const data = await response.json();
            this.updateUI(data);
        } catch (error) {
            console.error('Error fetching dashboard metrics:', error);
            // Handle offline or error gracefully by keeping UI stable
        } finally {
            if (btn) setTimeout(() => btn.classList.remove('animate-spin-once'), 1000);
        }
    }

    updateUI(metrics) {
        // Actualizar valores de texto
        this.setElementText('metric-cpu', metrics.system.cpu_usage);
        this.setElementText('metric-ram', metrics.system.memory_usage);
        this.setElementText('metric-temp', metrics.system.temperature);
        this.setElementText('metric-uptime', metrics.system.uptime_days);

        this.setElementText('network-up', metrics.system.network.upload);
        this.setElementText('network-down', metrics.system.network.download);

        // Almacenamiento
        this.setElementText('metric-storage-used', metrics.storage.used);
        this.setElementText('metric-storage-total', metrics.storage.total);
        this.setElementText('metric-storage-percent', metrics.storage.percent_used);

        const storageBar = document.getElementById('bar-storage');
        if (storageBar) storageBar.style.width = `${metrics.storage.percent_used}%`;

        // Actualizar Historial
        const now = new Date().toLocaleTimeString();
        this.pushData(this.dataHistory.cpu, metrics.system.cpu_usage);
        this.pushData(this.dataHistory.ram, metrics.system.memory_usage);
        this.pushData(this.dataHistory.up, metrics.system.network.up_raw);
        this.pushData(this.dataHistory.down, metrics.system.network.down_raw);
        this.pushData(this.dataHistory.labels, now);

        // Actualizar Gráficos
        if (this.charts.cpu) this.charts.cpu.update('none');
        if (this.charts.ram) this.charts.ram.update('none');
        if (this.charts.network) this.charts.network.update('none');

        // Quitar Skeletons si es la primera carga
        document.querySelectorAll('.skeleton-loading').forEach(el => el.classList.remove('skeleton-loading'));
    }

    setElementText(id, text) {
        const el = document.getElementById(id);
        if (el) el.innerText = text;
    }

    pushData(arr, val) {
        arr.push(val);
        if (arr.length > this.historyLimit) arr.shift();
    }

    startPolling(ms = 5000) {
        this.fetchMetrics();
        this.refreshInterval = setInterval(() => this.fetchMetrics(), ms);
    }
}

// Inicialización
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new DashboardManager();
    window.dashboard.init();
});
