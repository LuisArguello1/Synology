/**
 * Componente Skeleton para generar placeholders de carga.
 * Utiliza clases de Tailwind CSS.
 */
class Skeleton {
    /**
     * Genera un skeleton block básico.
     * @param {string} classes - Clases adicionales de Tailwind (e.g., 'w-20 h-4').
     * @returns {string} HTML string del skeleton.
     */
    static create(classes = 'w-full h-4') {
        return `<div class="animate-pulse bg-gray-200 rounded ${classes}"></div>`;
    }

    /**
     * Genera un skeleton circular (e.g., para avatares o iconos).
     * @param {string} sizeClass - Clase de tamaño (e.g., 'w-10 h-10').
     * @returns {string} HTML string.
     */
    static circle(sizeClass = 'w-10 h-10') {
        return `<div class="animate-pulse bg-gray-200 rounded-full ${sizeClass}"></div>`;
    }

    /**
     * Genera un bloque de texto skeleton (varias líneas).
     * @param {number} lines - Número de líneas.
     * @returns {string} HTML string.
     */
    static text(lines = 3) {
        let html = '';
        for (let i = 0; i < lines; i++) {
            const width = Math.floor(Math.random() * (100 - 60 + 1) + 60); // Random width 60-100%
            html += `<div class="animate-pulse bg-gray-200 h-3 rounded mb-2" style="width: ${width}%"></div>`;
        }
        return html;
    }
}

// Exponer globalmente si no se usa módulos ES6 nativos completos en el proyecto
window.Skeleton = Skeleton;
