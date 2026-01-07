/**
 * Viewer JavaScript for PDF Annotator
 * Handles page navigation, auto-save, and export functionality
 */

(function() {
    'use strict';

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

    // State
    let currentPage = 1;
    let isSaving = false;
    let saveTimeout = null;
    const SAVE_DELAY = 500; // Debounce delay in milliseconds

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
            pageLoading.innerHTML = '<p style="color: #ef4444;">Fehler beim Laden der Seite</p>';
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
     */
    function saveNote(immediate = false) {
        // Clear existing timeout
        if (saveTimeout) {
            clearTimeout(saveTimeout);
            saveTimeout = null;
        }

        // Debounce save
        if (!immediate) {
            saveTimeout = setTimeout(() => saveNote(true), SAVE_DELAY);
            return;
        }

        // Already saving
        if (isSaving) {
            return;
        }

        isSaving = true;
        setSaveStatus('saving');

        const saveUrl = `/viewer/api/annotation/${docId}/${currentPage}`;
        const noteText = noteField.value;

        fetch(saveUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
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

        // Save current page's note before navigating
        if (currentPage !== pageNumber) {
            saveNote(true); // Immediate save
        }

        // Wait a moment for save to complete
        setTimeout(() => {
            currentPage = pageNumber;
            loadPage(currentPage);
        }, 100);
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

    // Event Listeners

    // Navigation buttons
    prevButton.addEventListener('click', function() {
        navigateToPage(currentPage - 1);
    });

    nextButton.addEventListener('click', function() {
        navigateToPage(currentPage + 1);
    });

    // Save progress button
    saveProgressButton.addEventListener('click', saveProgress);

    // Note field auto-save
    noteField.addEventListener('input', function() {
        saveNote(false); // Debounced save
    });

    // Save on blur
    noteField.addEventListener('blur', function() {
        saveNote(true); // Immediate save
    });

    // Save before page unload
    window.addEventListener('beforeunload', function(e) {
        if (noteField.value.trim() !== '') {
            saveNote(true);
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
