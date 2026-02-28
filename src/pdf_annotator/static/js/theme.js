/**
 * Theme Toggle for PDF Annotator
 * Supports light/dark mode with system preference detection and localStorage persistence.
 */

(function() {
    'use strict';

    const STORAGE_KEY = 'pdf-annotator-theme';

    function getSystemPreference() {
        return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }

    function getSavedTheme() {
        return localStorage.getItem(STORAGE_KEY);
    }

    function applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        updateToggleButton(theme);
    }

    function updateToggleButton(theme) {
        var btn = document.getElementById('theme-toggle');
        if (!btn) return;

        var sunIcon = btn.querySelector('.theme-icon-sun');
        var moonIcon = btn.querySelector('.theme-icon-moon');
        var label = btn.querySelector('.theme-label');

        if (theme === 'dark') {
            if (sunIcon) sunIcon.style.display = 'inline-block';
            if (moonIcon) moonIcon.style.display = 'none';
            if (label) label.textContent = 'Hell';
            btn.setAttribute('aria-label', 'Zum hellen Modus wechseln');
        } else {
            if (sunIcon) sunIcon.style.display = 'none';
            if (moonIcon) moonIcon.style.display = 'inline-block';
            if (label) label.textContent = 'Dunkel';
            btn.setAttribute('aria-label', 'Zum dunklen Modus wechseln');
        }
    }

    function toggleTheme() {
        var current = document.documentElement.getAttribute('data-theme') || 'light';
        var next = current === 'dark' ? 'light' : 'dark';
        localStorage.setItem(STORAGE_KEY, next);
        applyTheme(next);
    }

    // Apply theme immediately (before DOM ready) to prevent flash
    var saved = getSavedTheme();
    var initial = saved || getSystemPreference();
    applyTheme(initial);

    // Bind toggle button after DOM is ready
    document.addEventListener('DOMContentLoaded', function() {
        var btn = document.getElementById('theme-toggle');
        if (btn) {
            btn.addEventListener('click', toggleTheme);
            updateToggleButton(initial);
        }
    });

    // Listen for system preference changes (only when no saved preference)
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function(e) {
        if (!getSavedTheme()) {
            applyTheme(e.matches ? 'dark' : 'light');
        }
    });
})();
