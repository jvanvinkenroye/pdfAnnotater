/**
 * Upload JavaScript for PDF Annotator
 * Handles file upload with drag & drop and validation
 */

(function() {
    'use strict';

    // DOM elements
    const uploadForm = document.getElementById('upload-form');
    const uploadArea = document.getElementById('upload-area');
    const fileInput = document.getElementById('file-input');
    const uploadButton = document.getElementById('upload-button');
    const uploadProgress = document.getElementById('upload-progress');
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');
    const errorMessage = document.getElementById('error-message');

    // Constants
    const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50 MB
    const ALLOWED_TYPES = ['application/pdf'];

    /**
     * Validate selected file
     * @param {File} file - File to validate
     * @returns {Object} - {valid: boolean, error: string}
     */
    function validateFile(file) {
        if (!file) {
            return { valid: false, error: 'Keine Datei ausgewählt' };
        }

        if (!ALLOWED_TYPES.includes(file.type)) {
            return { valid: false, error: 'Nur PDF-Dateien sind erlaubt' };
        }

        if (file.size === 0) {
            return { valid: false, error: 'Die Datei ist leer' };
        }

        if (file.size > MAX_FILE_SIZE) {
            const maxSizeMB = MAX_FILE_SIZE / (1024 * 1024);
            return { valid: false, error: `Datei zu groß (max. ${maxSizeMB} MB)` };
        }

        return { valid: true };
    }

    /**
     * Show error message
     * @param {string} message - Error message to display
     */
    function showError(message) {
        errorMessage.textContent = message;
        errorMessage.style.display = 'block';
        uploadProgress.style.display = 'none';
    }

    /**
     * Hide error message
     */
    function hideError() {
        errorMessage.style.display = 'none';
    }

    /**
     * Update progress bar
     * @param {number} percent - Progress percentage (0-100)
     */
    function updateProgress(percent) {
        progressFill.style.width = `${percent}%`;
    }

    /**
     * Upload file with AJAX
     * @param {File} file - File to upload
     */
    function uploadFile(file) {
        // Validate file
        const validation = validateFile(file);
        if (!validation.valid) {
            showError(validation.error);
            return;
        }

        hideError();

        // Disable form elements
        fileInput.disabled = true;
        uploadButton.disabled = true;
        uploadArea.style.pointerEvents = 'none';

        // Show progress
        uploadProgress.style.display = 'block';
        progressText.textContent = 'Wird hochgeladen...';
        updateProgress(0);

        // Create FormData
        const formData = new FormData();
        formData.append('file', file);

        // Create XMLHttpRequest for progress tracking
        const xhr = new XMLHttpRequest();

        // Progress event
        xhr.upload.addEventListener('progress', function(e) {
            if (e.lengthComputable) {
                const percent = Math.round((e.loaded / e.total) * 100);
                updateProgress(percent);
            }
        });

        // Load event (success)
        xhr.addEventListener('load', function() {
            if (xhr.status >= 200 && xhr.status < 300) {
                try {
                    const response = JSON.parse(xhr.responseText);
                    if (response.success && response.redirect_url) {
                        progressText.textContent = 'Upload erfolgreich! Weiterleitung...';
                        updateProgress(100);
                        // Redirect to viewer
                        setTimeout(() => {
                            window.location.href = response.redirect_url;
                        }, 500);
                    } else {
                        showError('Unerwarteter Serverfehler');
                        resetForm();
                    }
                } catch (e) {
                    showError('Fehler beim Verarbeiten der Antwort');
                    resetForm();
                }
            } else {
                try {
                    const response = JSON.parse(xhr.responseText);
                    showError(response.error || 'Upload fehlgeschlagen');
                } catch (e) {
                    showError('Upload fehlgeschlagen');
                }
                resetForm();
            }
        });

        // Error event
        xhr.addEventListener('error', function() {
            showError('Netzwerkfehler beim Upload');
            resetForm();
        });

        // Abort event
        xhr.addEventListener('abort', function() {
            showError('Upload abgebrochen');
            resetForm();
        });

        // Send request
        xhr.open('POST', uploadForm.action);
        xhr.setRequestHeader('Accept', 'application/json');
        xhr.send(formData);
    }

    /**
     * Reset form to initial state
     */
    function resetForm() {
        fileInput.disabled = false;
        uploadButton.disabled = false;
        uploadArea.style.pointerEvents = 'auto';
        fileInput.value = '';
        uploadProgress.style.display = 'none';
    }

    /**
     * Handle file selection
     */
    function handleFileSelect(file) {
        if (file) {
            uploadFile(file);
        }
    }

    // Event Listeners

    // Form submit
    uploadForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const file = fileInput.files[0];
        handleFileSelect(file);
    });

    // File input change
    fileInput.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            // Update button text
            uploadButton.textContent = `"${file.name}" hochladen`;
        }
    });

    // Drag and drop events
    uploadArea.addEventListener('dragover', function(e) {
        e.preventDefault();
        e.stopPropagation();
        uploadArea.classList.add('dragover');
    });

    uploadArea.addEventListener('dragleave', function(e) {
        e.preventDefault();
        e.stopPropagation();
        uploadArea.classList.remove('dragover');
    });

    uploadArea.addEventListener('drop', function(e) {
        e.preventDefault();
        e.stopPropagation();
        uploadArea.classList.remove('dragover');

        const files = e.dataTransfer.files;
        if (files.length > 0) {
            const file = files[0];
            // Set file to input
            const dataTransfer = new DataTransfer();
            dataTransfer.items.add(file);
            fileInput.files = dataTransfer.files;

            // Update button text
            uploadButton.textContent = `"${file.name}" hochladen`;

            // Optional: Auto-upload on drop
            // handleFileSelect(file);
        }
    });

})();
