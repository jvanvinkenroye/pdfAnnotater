/**
 * Simple modal and toast notification system
 * Replaces browser alert() and confirm() with styled UI elements
 */

(function() {
    'use strict';

    // Inject modal HTML and styles
    var overlay = document.createElement('div');
    overlay.id = 'modal-overlay';
    overlay.className = 'modal-overlay';
    document.body.appendChild(overlay);

    var modal = document.createElement('div');
    modal.id = 'modal-dialog';
    modal.className = 'modal-dialog';
    modal.setAttribute('role', 'dialog');
    modal.setAttribute('aria-modal', 'true');
    modal.innerHTML =
        '<div class="modal-content">' +
            '<p id="modal-message" class="modal-message"></p>' +
            '<div id="modal-actions" class="modal-actions"></div>' +
        '</div>';
    document.body.appendChild(modal);

    var toastContainer = document.createElement('div');
    toastContainer.id = 'toast-container';
    toastContainer.className = 'toast-container';
    document.body.appendChild(toastContainer);

    var resolveCallback = null;

    function closeModal() {
        overlay.classList.remove('active');
        modal.classList.remove('active');
    }

    overlay.addEventListener('click', function() {
        closeModal();
        if (resolveCallback) {
            resolveCallback(false);
            resolveCallback = null;
        }
    });

    // Escape key closes modal
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && modal.classList.contains('active')) {
            closeModal();
            if (resolveCallback) {
                resolveCallback(false);
                resolveCallback = null;
            }
        }
    });

    /**
     * Show an alert-style modal (single OK button)
     * @param {string} message - Message to display
     * @returns {Promise} - Resolves when user clicks OK
     */
    window.showAlert = function(message) {
        return new Promise(function(resolve) {
            var msgEl = document.getElementById('modal-message');
            var actionsEl = document.getElementById('modal-actions');

            msgEl.textContent = message;
            actionsEl.innerHTML = '';

            var okBtn = document.createElement('button');
            okBtn.className = 'btn btn-primary btn-sm';
            okBtn.textContent = 'OK';
            okBtn.addEventListener('click', function() {
                closeModal();
                resolve(true);
            });
            actionsEl.appendChild(okBtn);

            overlay.classList.add('active');
            modal.classList.add('active');
            okBtn.focus();
        });
    };

    /**
     * Show a confirm-style modal (OK/Cancel buttons)
     * @param {string} message - Message to display
     * @returns {Promise<boolean>} - Resolves true for OK, false for Cancel
     */
    window.showConfirm = function(message) {
        return new Promise(function(resolve) {
            resolveCallback = resolve;
            var msgEl = document.getElementById('modal-message');
            var actionsEl = document.getElementById('modal-actions');

            msgEl.textContent = message;
            actionsEl.innerHTML = '';

            var cancelBtn = document.createElement('button');
            cancelBtn.className = 'btn btn-secondary btn-sm';
            cancelBtn.textContent = 'Abbrechen';
            cancelBtn.addEventListener('click', function() {
                closeModal();
                resolveCallback = null;
                resolve(false);
            });

            var okBtn = document.createElement('button');
            okBtn.className = 'btn btn-primary btn-sm';
            okBtn.textContent = 'OK';
            okBtn.addEventListener('click', function() {
                closeModal();
                resolveCallback = null;
                resolve(true);
            });

            actionsEl.appendChild(cancelBtn);
            actionsEl.appendChild(okBtn);

            overlay.classList.add('active');
            modal.classList.add('active');
            okBtn.focus();
        });
    };

    /**
     * Show a toast notification
     * @param {string} message - Message to display
     * @param {string} type - 'success', 'error', or 'info' (default: 'info')
     * @param {number} duration - Duration in ms (default: 3000)
     */
    window.showToast = function(message, type, duration) {
        type = type || 'info';
        duration = duration || 3000;

        var toast = document.createElement('div');
        toast.className = 'toast toast-' + type;
        toast.textContent = message;

        toastContainer.appendChild(toast);

        // Trigger animation
        requestAnimationFrame(function() {
            toast.classList.add('active');
        });

        setTimeout(function() {
            toast.classList.remove('active');
            setTimeout(function() {
                toast.remove();
            }, 300);
        }, duration);
    };
})();
