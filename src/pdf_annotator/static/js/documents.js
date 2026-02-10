/**
 * Documents page JavaScript for PDF Annotator
 * Handles table sorting, export/import, PDF replacement, and document deletion
 */

(function() {
    'use strict';

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

        // Add hover effect
        header.style.cursor = 'pointer';
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
                alert('Fehler beim Herunterladen der Datei');
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
            alert('Bitte waehlen Sie eine PDF-Datei aus.');
            replacePdfFileInput.value = '';
            currentReplacingDocId = null;
            return;
        }

        // Validate file size (50 MB)
        const maxSize = 50 * 1024 * 1024;
        if (file.size > maxSize) {
            alert('Die Datei ist zu gross. Maximum: 50 MB');
            replacePdfFileInput.value = '';
            currentReplacingDocId = null;
            return;
        }

        // Confirm replacement
        if (!confirm('Moechten Sie wirklich das PDF ersetzen? Alle Notizen bleiben erhalten.')) {
            replacePdfFileInput.value = '';
            currentReplacingDocId = null;
            return;
        }

        // Create FormData and upload
        const formData = new FormData();
        formData.append('file', file);

        const replaceUrl = `/viewer/api/replace/${currentReplacingDocId}`;

        fetch(replaceUrl, {
            method: 'POST',
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
                alert(`PDF erfolgreich ersetzt! Neue Seitenanzahl: ${data.page_count}`);
                // Reload page to reflect changes
                window.location.reload();
            })
            .catch(error => {
                console.error('Error replacing PDF:', error);
                alert(`Fehler beim Ersetzen des PDFs: ${error.message}`);
            })
            .finally(() => {
                replacePdfFileInput.value = '';
                currentReplacingDocId = null;
            });
    });

    // Delete document function - using event delegation
    document.querySelectorAll('.btn-delete').forEach(btn => {
        btn.addEventListener('click', function() {
            const docId = this.dataset.docId;
            const filename = this.dataset.filename;

            // Confirm deletion
            if (!confirm(`Moechten Sie wirklich "${filename}" und alle zugehoerigen Notizen loeschen?\n\nDiese Aktion kann nicht rueckgaengig gemacht werden.`)) {
                return;
            }

            // Send DELETE request
            fetch(`/delete/${docId}`, {
                method: 'DELETE',
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
                    // Show success message and reload page
                    alert(data.message || 'Dokument erfolgreich geloescht');
                    window.location.reload();
                })
                .catch(error => {
                    console.error('Error deleting document:', error);
                    alert(`Fehler beim Loeschen: ${error.message}`);
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
                    const msg = `Export enthaelt:\n` +
                        `- ${info.document_count} Dokumente\n` +
                        `- ${info.annotation_count} Notizen\n` +
                        `- ca. ${info.estimated_size_mb} MB\n\n` +
                        `Fortfahren?`;

                    if (info.document_count === 0) {
                        alert('Keine Dokumente zum Exportieren vorhanden.');
                        return;
                    }

                    if (confirm(msg)) {
                        // Trigger download
                        window.location.href = '/export';
                    }
                })
                .catch(error => {
                    console.error('Error getting export info:', error);
                    alert('Fehler beim Abrufen der Export-Informationen');
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
                alert('Bitte waehlen Sie eine ZIP-Datei aus.');
                importFileInput.value = '';
                return;
            }

            if (!confirm(`Moechten Sie die Daten aus "${file.name}" importieren?`)) {
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
                    alert(data.message || 'Import erfolgreich!');
                    window.location.reload();
                })
                .catch(error => {
                    console.error('Error importing data:', error);
                    alert(`Fehler beim Importieren: ${error.message}`);
                })
                .finally(() => {
                    importBtn.disabled = false;
                    importBtn.textContent = 'Importieren';
                    importFileInput.value = '';
                });
        });
    }
})();
