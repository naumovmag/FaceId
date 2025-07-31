// Global JavaScript utilities for Face ID System

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});

/**
 * Show loading modal with custom text
 */
function showLoading(text = 'Загрузка...') {
    console.log('Show loading:', text);
    const modal = document.getElementById('loadingModal');
    if (modal) {
        const loadingText = document.getElementById('loadingText');
        if (loadingText) {
            loadingText.textContent = text;
        }
        const modalInstance = new bootstrap.Modal(modal);
        modalInstance.show();
    }
}

/**
 * Hide loading modal - ПРИНУДИТЕЛЬНО
 */
function hideLoading() {
    console.log('Hide loading called');
    setTimeout(() => {
        const modal = document.getElementById('loadingModal');
        if (modal) {
            const modalInstance = bootstrap.Modal.getInstance(modal);
            if (modalInstance) {
                modalInstance.hide();
            }
        }

        // Принудительно убираем все modal backdrop
        document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
            backdrop.remove();
        });

        // Возвращаем scroll
        document.body.classList.remove('modal-open');
        document.body.style.overflow = '';
        document.body.style.paddingRight = '';

        console.log('Loading hidden');
    }, 100);
}

/**
 * Show alert message
 */
function showAlert(message, type = 'info', duration = 5000) {
    const alertHtml = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;

    // Find alert container or create one
    let alertContainer = document.getElementById('alertContainer');
    if (!alertContainer) {
        alertContainer = document.createElement('div');
        alertContainer.id = 'alertContainer';
        alertContainer.className = 'position-fixed top-0 end-0 p-3';
        alertContainer.style.zIndex = '9999';
        document.body.appendChild(alertContainer);
    }

    // Add alert to container
    const alertElement = document.createElement('div');
    alertElement.innerHTML = alertHtml;
    alertContainer.appendChild(alertElement.firstElementChild);

    // Auto-dismiss if duration is set
    if (duration > 0) {
        setTimeout(() => {
            const alert = alertContainer.querySelector('.alert');
            if (alert) {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }
        }, duration);
    }
}

// Export functions for use in other scripts
window.FaceIdUtils = {
    showLoading,
    hideLoading,
    showAlert
};