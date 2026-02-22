/**
 * Documents page JavaScript for PDF Annotator
 * Handles table sorting, export/import, PDF replacement, and document deletion
 */

(function() {
    'use strict';

    // CSRF token for all POST/DELETE requests
    const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

    const table = document.getElementById('documents-table');
    if (!table) return;

    const headers = table.querySelectorAll('th.sortable');
    let sortDirection = {}; // Track sort direction per column

    // PDF replacement state
    let currentReplacingDocId = null;
    const replacePdfFileInput = document.getElementById('replace-pdf-file-input');

    headers.forEach(header => {
        const columnIndex = parseInt(header.dataset.column);
        sortDirection[columnIndex] = 'asc';

        header.addEventListener('click', function() {
            const tbody = table.querySelector('tbody');
            const rows = Array.from(tbody.querySelectorAll('tr'));

            // Toggle sort direction
            sortDirection[columnIndex] = sortDirection[columnIndex] === 'asc' ? 'desc' : 'asc';

            // Remove active class from all headers
            headers.forEach(h => h.classList.remove('active-sort'));
            header.classList.add('active-sort');

            // Update sort icon
            headers.forEach(h => {
                const icon = h.querySelector('.sort-icon');
                if (icon) icon.textContent = '\u21C5';
            });
            const activeIcon = header.querySelector('.sort-icon');
            if (activeIcon) {
                activeIcon.textContent = sortDirection[columnIndex] === 'asc' ? '\u2191' : '\u2193';
            }

            // Sort rows
            rows.sort((rowA, rowB) => {
                const cellA = rowA.cells[columnIndex].textContent.trim();
                const cellB = rowB.cells[columnIndex].textContent.trim();

                // Handle empty values
                if (cellA === '-') return 1;
                if (cellB === '-') return -1;

                // Handle numeric columns (Seiten)
                if (columnIndex === 6) {
                    const numA = parseInt(cellA) || 0;
                    const numB = parseInt(cellB) || 0;
                    return sortDirection[columnIndex] === 'asc' ? numA - numB : numB - numA;
                }

                // Handle date columns (Hochgeladen, Zuletzt bearbeitet)
                if (columnIndex === 7 || columnIndex === 8) {
                    const dateA = new Date(cellA);
                    const dateB = new Date(cellB);
                    return sortDirection[columnIndex] === 'asc' ? dateA - dateB : dateB - dateA;
                }

                // String comparison for other columns
                const comparison = cellA.localeCompare(cellB, 'de');
                return sortDirection[columnIndex] === 'asc' ? comparison : -comparison;
            });

            // Re-append sorted rows
            rows.forEach(row => tbody.appendChild(row));
        });

    });

    // Download functions for POST requests - using event delegation
    document.querySelectorAll('.btn-export-pdf').forEach(btn => {
        btn.addEventListener('click', function(event) {
            event.preventDefault();
            const docId = this.dataset.docId;
            downloadFile(`/export/pdf/${docId}`, 'POST');
        });
    });

    document.querySelectorAll('.btn-export-md').forEach(btn => {
        btn.addEventListener('click', function(event) {
            event.preventDefault();
            const docId = this.dataset.docId;
            downloadFile(`/export/markdown/${docId}`, 'POST');
        });
    });

    function downloadFile(url, method) {
        fetch(url, {
            method: method,
            headers: { 'X-CSRFToken': csrfToken },
        })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Download failed');
                }

                // Extract filename from Content-Disposition header
                const contentDisposition = response.headers.get('Content-Disposition');
                let filename = 'download';
                if (contentDisposition) {
                    const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
                    if (filenameMatch && filenameMatch[1]) {
                        filename = filenameMatch[1].replace(/['"]/g, '');
                    }
                }

                return response.blob().then(blob => ({ blob, filename }));
            })
            .then(({ blob, filename }) => {
                // Create download link
                const downloadUrl = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.style.display = 'none';
                a.href = downloadUrl;
                a.download = filename;
                document.body.appendChild(a);
                a.click();

                // Cleanup
                window.URL.revokeObjectURL(downloadUrl);
                document.body.removeChild(a);
            })
            .catch(error => {
                console.error('Error downloading file:', error);
                showToast('Fehler beim Herunterladen der Datei', 'error');
            });
    }

    // PDF replacement function - using event delegation
    document.querySelectorAll('.btn-replace').forEach(btn => {
        btn.addEventListener('click', function() {
            currentReplacingDocId = this.dataset.docId;
            replacePdfFileInput.click();
        });
    });

    // Handle file selection for replacement
    replacePdfFileInput.addEventListener('change', function(event) {
        const file = event.target.files[0];
        if (!file || !currentReplacingDocId) {
            return;
        }

        // Validate file type
        if (!file.name.toLowerCase().endsWith('.pdf')) {
            showToast('Bitte waehlen Sie eine PDF-Datei aus.', 'error');
            replacePdfFileInput.value = '';
            currentReplacingDocId = null;
            return;
        }

        // Validate file size (50 MB)
        const maxSize = 50 * 1024 * 1024;
        if (file.size > maxSize) {
            showToast('Die Datei ist zu gross. Maximum: 50 MB', 'error');
            replacePdfFileInput.value = '';
            currentReplacingDocId = null;
            return;
        }

        // Confirm replacement
        var docIdToReplace = currentReplacingDocId;
        showConfirm('Moechten Sie wirklich das PDF ersetzen? Alle Notizen bleiben erhalten.').then(function(confirmed) {
            if (!confirmed) {
                replacePdfFileInput.value = '';
                currentReplacingDocId = null;
                return;
            }

            // Create FormData and upload
            const formData = new FormData();
            formData.append('file', file);

            const replaceUrl = `/viewer/api/replace/${docIdToReplace}`;

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
                })
                .finally(() => {
                    replacePdfFileInput.value = '';
                    currentReplacingDocId = null;
                });
        });
    });

    // Delete document function - using event delegation
    document.querySelectorAll('.btn-delete').forEach(btn => {
        btn.addEventListener('click', function() {
            const docId = this.dataset.docId;
            const filename = this.dataset.filename;

            // Confirm deletion
            showConfirm(`Moechten Sie wirklich "${filename}" und alle zugehoerigen Notizen loeschen?\n\nDiese Aktion kann nicht rueckgaengig gemacht werden.`).then(function(confirmed) {
                if (!confirmed) return;

                // Send DELETE request
                fetch(`/delete/${docId}`, {
                    method: 'DELETE',
                    headers: { 'X-CSRFToken': csrfToken },
                })
                    .then(response => {
                        if (!response.ok) {
                            return response.json().then(data => {
                                throw new Error(data.error || 'Fehler beim Loeschen');
                            });
                        }
                        return response.json();
                    })
                    .then(data => {
                        showToast(data.message || 'Dokument erfolgreich geloescht', 'success');
                        setTimeout(function() { window.location.reload(); }, 1500);
                    })
                    .catch(error => {
                        console.error('Error deleting document:', error);
                        showToast(`Fehler beim Loeschen: ${error.message}`, 'error');
                    });
            });
        });
    });

    // Export data function
    const exportBtn = document.getElementById('btn-export-data');
    if (exportBtn) {
        exportBtn.addEventListener('click', function() {
            // First get export info
            fetch('/export/info')
                .then(response => response.json())
                .then(info => {
                    if (info.document_count === 0) {
                        showToast('Keine Dokumente zum Exportieren vorhanden.', 'info');
                        return;
                    }

                    const msg = `Export enthaelt:\n` +
                        `- ${info.document_count} Dokumente\n` +
                        `- ${info.annotation_count} Notizen\n` +
                        `- ca. ${info.estimated_size_mb} MB\n\n` +
                        `Fortfahren?`;

                    showConfirm(msg).then(function(confirmed) {
                        if (confirmed) {
                            window.location.href = '/export';
                        }
                    });
                })
                .catch(error => {
                    console.error('Error getting export info:', error);
                    showToast('Fehler beim Abrufen der Export-Informationen', 'error');
                });
        });
    }

    // Import data function
    const importBtn = document.getElementById('btn-import-data');
    const importFileInput = document.getElementById('import-file-input');

    if (importBtn && importFileInput) {
        importBtn.addEventListener('click', function() {
            importFileInput.click();
        });

        importFileInput.addEventListener('change', function(event) {
            const file = event.target.files[0];
            if (!file) return;

            if (!file.name.toLowerCase().endsWith('.zip')) {
                showToast('Bitte waehlen Sie eine ZIP-Datei aus.', 'error');
                importFileInput.value = '';
                return;
            }

            showConfirm(`Moechten Sie die Daten aus "${file.name}" importieren?`).then(function(confirmed) {
                if (!confirmed) {
                    importFileInput.value = '';
                    return;
                }

                const formData = new FormData();
                formData.append('file', file);

                // Show loading state
                importBtn.disabled = true;
                importBtn.textContent = 'Importiere...';

                fetch('/import', {
                    method: 'POST',
                    headers: { 'X-CSRFToken': csrfToken },
                    body: formData
                })
                    .then(response => {
                        if (!response.ok) {
                            return response.json().then(data => {
                                throw new Error(data.error || 'Fehler beim Importieren');
                            });
                        }
                        return response.json();
                    })
                    .then(data => {
                        showToast(data.message || 'Import erfolgreich!', 'success');
                        setTimeout(function() { window.location.reload(); }, 1500);
                    })
                    .catch(error => {
                        console.error('Error importing data:', error);
                        showToast(`Fehler beim Importieren: ${error.message}`, 'error');
                    })
                    .finally(() => {
                        importBtn.disabled = false;
                        importBtn.textContent = 'Importieren';
                        importFileInput.value = '';
                    });
            });
        });
    }
})();
