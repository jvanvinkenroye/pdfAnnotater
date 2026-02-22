/**
 * Viewer JavaScript for PDF Annotator
 * Handles page navigation, auto-save, and export functionality
 */

(function() {
    'use strict';

    // CSRF token for all POST requests
    const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

    // Get viewer data from HTML
    const viewerData = document.getElementById('viewer-data');
    const docId = viewerData.dataset.docId;
    const pageCount = parseInt(viewerData.dataset.pageCount);

    // DOM elements
    const pdfPage = document.getElementById('pdf-page');
    const pageLoading = document.getElementById('page-loading');
    const noteField = document.getElementById('note-field');
    const currentPageSpan = document.getElementById('current-page');
    const prevButton = document.getElementById('prev-page');
    const nextButton = document.getElementById('next-page');
    const saveProgressButton = document.getElementById('save-progress');
    const saveStatus = document.getElementById('save-status');

    // Metadata elements
    const editMetadataBtn = document.getElementById('edit-metadata-btn');
    const saveMetadataBtn = document.getElementById('save-metadata-btn');
    const cancelMetadataBtn = document.getElementById('cancel-metadata-btn');
    const metadataDisplay = document.getElementById('metadata-display');
    const metadataForm = document.getElementById('metadata-form');

    // PDF replacement elements
    const replacePdfBtn = document.getElementById('replace-pdf-btn');
    const replacePdfInput = document.getElementById('replace-pdf-input');

    // Zoom elements
    const zoomInBtn = document.getElementById('zoom-in');
    const zoomOutBtn = document.getElementById('zoom-out');
    const zoomFitBtn = document.getElementById('zoom-fit');
    const zoomLevelSpan = document.getElementById('zoom-level');
    const pdfPageWrapper = document.querySelector('.pdf-page-wrapper');

    // State
    let currentPage = 1;
    let isSaving = false;
    let saveTimeout = null;
    const SAVE_DELAY = 500; // Debounce delay in milliseconds

    // Zoom state
    const ZOOM_LEVELS = [50, 75, 100, 125, 150, 200];
    let currentZoomIndex = 2; // 100%
    let fitToWidth = true; // Default: fit to container width

    /**
     * Load PDF page image
     * @param {number} pageNumber - Page number to load (1-indexed)
     */
    function loadPage(pageNumber) {
        // Show loading spinner
        pageLoading.style.display = 'flex';
        pdfPage.style.display = 'none';

        // Build URL
        const pageUrl = `/viewer/api/page/${docId}/${pageNumber}`;

        // Load image
        const img = new Image();
        img.onload = function() {
            pdfPage.src = img.src;
            pdfPage.style.display = 'block';
            pageLoading.style.display = 'none';
        };
        img.onerror = function() {
            pageLoading.textContent = '';
            const errorP = document.createElement('p');
            errorP.classList.add('error-text');
            errorP.textContent = 'Fehler beim Laden der Seite';
            pageLoading.appendChild(errorP);
        };
        img.src = pageUrl;

        // Load annotation
        loadAnnotation(pageNumber);

        // Update UI
        currentPageSpan.textContent = pageNumber;
        updateNavigationButtons();
    }

    /**
     * Load annotation for current page
     * @param {number} pageNumber - Page number (1-indexed)
     */
    function loadAnnotation(pageNumber) {
        const annotationUrl = `/viewer/api/annotation/${docId}/${pageNumber}`;

        fetch(annotationUrl)
            .then(response => response.json())
            .then(data => {
                noteField.value = data.note_text || '';
            })
            .catch(error => {
                console.error('Error loading annotation:', error);
                noteField.value = '';
            });
    }

    /**
     * Save current annotation
     * @param {boolean} immediate - Save immediately without debounce
     * @returns {Promise} - Resolves when save is complete
     */
    function saveNote(immediate = false) {
        // Clear existing timeout
        if (saveTimeout) {
            clearTimeout(saveTimeout);
            saveTimeout = null;
        }

        // Debounce save
        if (!immediate) {
            return new Promise(resolve => {
                saveTimeout = setTimeout(() => saveNote(true).then(resolve), SAVE_DELAY);
            });
        }

        // Already saving
        if (isSaving) {
            return Promise.resolve();
        }

        isSaving = true;
        setSaveStatus('saving');

        const saveUrl = `/viewer/api/annotation/${docId}/${currentPage}`;
        const noteText = noteField.value;

        return fetch(saveUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken,
            },
            body: JSON.stringify({ note_text: noteText })
        })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Save failed');
                }
                return response.json();
            })
            .then(data => {
                setSaveStatus('saved');
                isSaving = false;
            })
            .catch(error => {
                console.error('Error saving annotation:', error);
                setSaveStatus('error');
                isSaving = false;
            });
    }

    /**
     * Set save status display
     * @param {string} status - Status: 'saved', 'saving', 'error'
     */
    function setSaveStatus(status) {
        saveStatus.classList.remove('saving', 'error');

        if (status === 'saving') {
            saveStatus.textContent = 'Wird gespeichert...';
            saveStatus.classList.add('saving');
        } else if (status === 'saved') {
            saveStatus.textContent = 'Gespeichert';
        } else if (status === 'error') {
            saveStatus.textContent = 'Fehler beim Speichern';
            saveStatus.classList.add('error');
        }
    }

    /**
     * Navigate to specific page
     * @param {number} pageNumber - Target page number
     */
    function navigateToPage(pageNumber) {
        if (pageNumber < 1 || pageNumber > pageCount) {
            return;
        }

        // Save current page's note before navigating, then load new page
        if (currentPage !== pageNumber) {
            saveNote(true).then(() => {
                currentPage = pageNumber;
                loadPage(currentPage);
            });
        }
    }

    /**
     * Update navigation button states
     */
    function updateNavigationButtons() {
        prevButton.disabled = currentPage <= 1;
        nextButton.disabled = currentPage >= pageCount;
    }

    /**
     * Manually save progress
     */
    function saveProgress() {
        saveNote(true); // Immediate save

        // Show feedback
        saveProgressButton.disabled = true;
        saveProgressButton.textContent = 'Wird gespeichert...';

        setTimeout(() => {
            saveProgressButton.disabled = false;
            saveProgressButton.textContent = 'Fortschritt speichern';
        }, 1000);
    }

    /**
     * Show metadata edit form
     */
    function showMetadataForm() {
        metadataDisplay.style.display = 'none';
        metadataForm.style.display = 'block';
        editMetadataBtn.style.display = 'none';
    }

    /**
     * Hide metadata edit form
     */
    function hideMetadataForm() {
        metadataDisplay.style.display = 'flex';
        metadataForm.style.display = 'none';
        editMetadataBtn.style.display = 'inline-block';
    }

    /**
     * Save metadata
     */
    function saveMetadata() {
        const firstName = document.getElementById('edit-first-name').value.trim();
        const lastName = document.getElementById('edit-last-name').value.trim();
        const title = document.getElementById('edit-title').value.trim();
        const year = document.getElementById('edit-year').value.trim();
        const subject = document.getElementById('edit-subject').value.trim();

        // Disable button
        saveMetadataBtn.disabled = true;
        saveMetadataBtn.textContent = 'Wird gespeichert...';

        const metadataUrl = `/viewer/api/metadata/${docId}`;

        fetch(metadataUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken,
            },
            body: JSON.stringify({
                first_name: firstName,
                last_name: lastName,
                title: title,
                year: year,
                subject: subject
            })
        })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Save failed');
                }
                return response.json();
            })
            .then(data => {
                // Update display
                document.getElementById('display-first-name').textContent = firstName || '-';
                document.getElementById('display-last-name').textContent = lastName || '-';
                document.getElementById('display-title').textContent = title || '-';
                document.getElementById('display-year').textContent = year || '-';
                document.getElementById('display-subject').textContent = subject || '-';

                // Hide form
                hideMetadataForm();

                // Reset button
                saveMetadataBtn.disabled = false;
                saveMetadataBtn.textContent = 'Speichern';
            })
            .catch(error => {
                console.error('Error saving metadata:', error);
                showToast('Fehler beim Speichern der Metadaten', 'error');
                saveMetadataBtn.disabled = false;
                saveMetadataBtn.textContent = 'Speichern';
            });
    }

    /**
     * Handle PDF replacement file selection
     */
    function handlePdfReplace(event) {
        const file = event.target.files[0];
        if (!file) {
            return;
        }

        // Validate file type
        if (!file.name.toLowerCase().endsWith('.pdf')) {
            showToast('Bitte wählen Sie eine PDF-Datei aus.', 'error');
            replacePdfInput.value = '';
            return;
        }

        // Validate file size (50 MB)
        const maxSize = 50 * 1024 * 1024;
        if (file.size > maxSize) {
            showToast('Die Datei ist zu groß. Maximum: 50 MB', 'error');
            replacePdfInput.value = '';
            return;
        }

        // Confirm replacement
        showConfirm('Möchten Sie wirklich das PDF ersetzen? Alle Notizen bleiben erhalten.').then(function(confirmed) {
            if (!confirmed) {
                replacePdfInput.value = '';
                return;
            }
            doReplacePdf(file);
        });
    }

    /**
     * Perform the actual PDF replacement upload
     * @param {File} file - PDF file to upload
     */
    function doReplacePdf(file) {
        // Disable button and show feedback
        replacePdfBtn.disabled = true;
        replacePdfBtn.textContent = 'PDF wird ersetzt...';

        // Create FormData and upload
        const formData = new FormData();
        formData.append('file', file);

        const replaceUrl = `/viewer/api/replace/${docId}`;

        fetch(replaceUrl, {
            method: 'POST',
            headers: { 'X-CSRFToken': csrfToken },
            body: formData
        })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(data => {
                        throw new Error(data.error || 'Fehler beim Ersetzen');
                    });
                }
                return response.json();
            })
            .then(data => {
                showToast(`PDF erfolgreich ersetzt! Neue Seitenanzahl: ${data.page_count}`, 'success');
                setTimeout(function() { window.location.reload(); }, 1500);
            })
            .catch(error => {
                console.error('Error replacing PDF:', error);
                showToast(`Fehler beim Ersetzen des PDFs: ${error.message}`, 'error');
                replacePdfBtn.disabled = false;
                replacePdfBtn.textContent = 'PDF ersetzen';
                replacePdfInput.value = '';
            });
    }

    /**
     * Apply zoom level to PDF image
     */
    function applyZoom() {
        if (fitToWidth) {
            // Fit to container width: reset to default CSS behavior
            pdfPage.classList.remove('zoomed');
            pdfPageWrapper.classList.remove('zoomed');
            pdfPage.style.transform = '';
            zoomLevelSpan.textContent = 'Anp.';
            zoomFitBtn.classList.add('active');
        } else {
            var scale = ZOOM_LEVELS[currentZoomIndex] / 100;
            pdfPage.classList.add('zoomed');
            pdfPageWrapper.classList.add('zoomed');
            pdfPage.style.transform = 'scale(' + scale + ')';
            zoomLevelSpan.textContent = ZOOM_LEVELS[currentZoomIndex] + '%';
            zoomFitBtn.classList.remove('active');
        }
    }

    /**
     * Zoom in one level
     */
    function zoomIn() {
        fitToWidth = false;
        if (currentZoomIndex < ZOOM_LEVELS.length - 1) {
            currentZoomIndex++;
        }
        applyZoom();
    }

    /**
     * Zoom out one level
     */
    function zoomOut() {
        fitToWidth = false;
        if (currentZoomIndex > 0) {
            currentZoomIndex--;
        }
        applyZoom();
    }

    /**
     * Toggle fit-to-width mode
     */
    function toggleFitToWidth() {
        fitToWidth = !fitToWidth;
        if (!fitToWidth) {
            currentZoomIndex = 2; // Reset to 100%
        }
        applyZoom();
    }

    // Event Listeners

    // Zoom controls
    zoomInBtn.addEventListener('click', zoomIn);
    zoomOutBtn.addEventListener('click', zoomOut);
    zoomFitBtn.addEventListener('click', toggleFitToWidth);

    // Navigation buttons
    prevButton.addEventListener('click', function() {
        navigateToPage(currentPage - 1);
    });

    nextButton.addEventListener('click', function() {
        navigateToPage(currentPage + 1);
    });

    // Save progress button
    saveProgressButton.addEventListener('click', saveProgress);

    // Metadata buttons
    editMetadataBtn.addEventListener('click', showMetadataForm);
    saveMetadataBtn.addEventListener('click', saveMetadata);
    cancelMetadataBtn.addEventListener('click', hideMetadataForm);

    // PDF replacement
    replacePdfBtn.addEventListener('click', function() {
        replacePdfInput.click();
    });
    replacePdfInput.addEventListener('change', handlePdfReplace);

    // Note field auto-save
    noteField.addEventListener('input', function() {
        saveNote(false); // Debounced save
    });

    // Save on blur
    noteField.addEventListener('blur', function() {
        saveNote(true); // Immediate save
    });

    // Save before page unload using sendBeacon for reliability
    window.addEventListener('beforeunload', function(e) {
        if (noteField.value.trim() !== '') {
            const saveUrl = `/viewer/api/annotation/${docId}/${currentPage}`;
            const data = JSON.stringify({ note_text: noteField.value });
            navigator.sendBeacon(saveUrl, new Blob([data], { type: 'application/json' }));
        }
    });

    // Keyboard navigation with Ctrl/Cmd + Arrow keys
    document.addEventListener('keydown', function(e) {
        // Only navigate with Ctrl (Windows/Linux) or Cmd (Mac) + Arrow keys
        if (!(e.ctrlKey || e.metaKey)) {
            return;
        }

        // Arrow key navigation
        if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
            e.preventDefault();
            if (currentPage > 1) {
                navigateToPage(currentPage - 1);
            }
        } else if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
            e.preventDefault();
            if (currentPage < pageCount) {
                navigateToPage(currentPage + 1);
            }
        }
    });

    // Initialize: Load first page
    loadPage(currentPage);

})();
