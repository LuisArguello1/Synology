// Función para mostrar mensaje programáticamente
function showMessage(text, type = 'info') {
    // Crear contenedor si no existe
    let container = document.getElementById('messagesContainer');
    if (!container) {
        container = document.createElement('div');
        container.id = 'messagesContainer';
        container.className = 'messages-container';
        document.body.appendChild(container);
    }
    
    const messageId = Date.now();
    const icons = {
        'success': 'check',
        'error': 'times', 
        'warning': 'exclamation',
        'info': 'info'
    };
    
    // HTML del mensaje con todos los componentes
    const messageHtml = `
        <div id="message-${messageId}" 
             class="message-alert message-${type}"
             data-message-id="${messageId}" style="opacity: 0">
            <div class="message-decoration"></div>
            <div class="message-content">
                <div class="message-body">
                    <div class="message-icon">
                        <div class="icon-bg icon-${type}">
                            <i class="fas fa-${icons[type] || 'info'}"></i>
                        </div>
                    </div>
                    <div class="message-text">
                        <p>${text}</p>
                    </div>
                </div>
                <button onclick="closeMessage(${messageId})" class="close-btn" aria-label="Cerrar">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="progress-bar"></div>
        </div>
    `;
    
    container.insertAdjacentHTML('beforeend', messageHtml);
    container.style.display = 'block';
    
    // Aplicar aparición con retraso pequeño para que la transición funcione
    setTimeout(() => {
        const messageElement = document.getElementById(`message-${messageId}`);
        if (messageElement) {
            messageElement.style.opacity = '1';
            messageElement.style.animation = 'message-slide-in 0.3s forwards';
            
            // Añadir evento para pausar la barra de progreso al pasar el mouse
            messageElement.addEventListener('mouseenter', function() {
                const progressBar = this.querySelector('.progress-bar::after');
                if (progressBar) progressBar.style.animationPlayState = 'paused';
            });
            
            // Reanudar la barra de progreso al quitar el mouse
            messageElement.addEventListener('mouseleave', function() {
                const progressBar = this.querySelector('.progress-bar::after');
                if (progressBar) progressBar.style.animationPlayState = 'running';
            });
        }
    }, 10);
    
    // Auto-hide después de un tiempo
    setTimeout(() => closeMessage(messageId), 6000);
    
    // Devolver el ID por si se necesita para referencias futuras
    return messageId;
}

function closeMessage(messageId) {
    const message = document.getElementById('message-' + messageId);
    if (message) {
        // Aplicar la animación de salida
        message.classList.add('animate-slideOutRight');
        message.style.opacity = '0';
        
        // Remover del DOM después de la animación
        setTimeout(function() {
            if (message && message.parentNode) {
                message.parentNode.removeChild(message);
            }
            
            // Ocultar el contenedor si no hay más mensajes
            const container = document.getElementById('messagesContainer');
            if (container && container.children.length === 0) {
                container.style.display = 'none';
            }
        }, 400); // Ajustado al tiempo de la animación
    }
}

// Inicializar al cargar la página
document.addEventListener('DOMContentLoaded', function() {
    // Escalonar la aparición de los mensajes existentes
    const messages = document.querySelectorAll('.message-alert');
    
    messages.forEach((message, index) => {
        // Aplicar un retraso progresivo para mensajes múltiples
        setTimeout(() => {
            // Añadir la animación mediante clase o estilo directo
            message.style.opacity = '1';
            message.style.animation = 'message-slide-in 0.3s forwards';
        }, 150 * index); // Reducido ligeramente para mejor fluidez
        
        // Auto-hide messages después de un tiempo
        setTimeout(() => {
            closeMessage(message.dataset.messageId);
        }, 6000 + (index * 800)); // Ajustado para mejor experiencia
        
        // Añadir evento para pausar la barra de progreso al pasar el mouse
        message.addEventListener('mouseenter', function() {
            const progressBar = this.querySelector('.progress-bar::after');
            if (progressBar) progressBar.style.animationPlayState = 'paused';
        });
        
        // Reanudar la barra de progreso al quitar el mouse
        message.addEventListener('mouseleave', function() {
            const progressBar = this.querySelector('.progress-bar::after');
            if (progressBar) progressBar.style.animationPlayState = 'running';
        });
    });
});
