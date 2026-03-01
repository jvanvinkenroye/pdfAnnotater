/**
 * Theme Toggle for PDF Annotator
 * Supports light / dark / brutalist with system preference detection
 * and localStorage persistence.
 */

(function() {
    'use strict';

    var STORAGE_KEY = 'pdf-annotator-theme';
    var THEMES = ['light', 'dark', 'brutalist'];

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

        var sunIcon    = btn.querySelector('.theme-icon-sun');
        var moonIcon   = btn.querySelector('.theme-icon-moon');
        var brutalIcon = btn.querySelector('.theme-icon-brutal');
        var label      = btn.querySelector('.theme-label');

        // Hide all icons first
        if (sunIcon)    sunIcon.style.display    = 'none';
        if (moonIcon)   moonIcon.style.display   = 'none';
        if (brutalIcon) brutalIcon.style.display = 'none';

        if (theme === 'dark') {
            // In dark mode: next theme is brutalist
            if (sunIcon) sunIcon.style.display = 'inline-block';
            if (label) label.textContent = 'Brutal';
            btn.setAttribute('aria-label', 'Zum Brutalist-Modus wechseln');
        } else if (theme === 'brutalist') {
            // In brutalist mode: next theme is light
            if (brutalIcon) brutalIcon.style.display = 'inline-block';
            if (label) label.textContent = 'Hell';
            btn.setAttribute('aria-label', 'Zum hellen Modus wechseln');
        } else {
            // In light mode: next theme is dark
            if (moonIcon) moonIcon.style.display = 'inline-block';
            if (label) label.textContent = 'Dunkel';
            btn.setAttribute('aria-label', 'Zum dunklen Modus wechseln');
        }
    }

    function toggleTheme() {
        var current = document.documentElement.getAttribute('data-theme') || 'light';
        var next = THEMES[(THEMES.indexOf(current) + 1) % THEMES.length];
        localStorage.setItem(STORAGE_KEY, next);
        applyTheme(next);

        if (window.__userAuthenticated) {
            var csrfMeta = document.querySelector('meta[name="csrf-token"]');
            var csrf = csrfMeta ? csrfMeta.getAttribute('content') : '';
            fetch('/auth/theme', {
                method: 'POST',
                headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrf},
                body: JSON.stringify({theme: next})
            });
            // fire-and-forget: localStorage is the immediate fallback
        }
    }

    // Apply theme immediately (before DOM ready) to prevent flash
    // Priority: server DB theme > localStorage > system preference
    var initial;
    if (window.__userAuthenticated && window.__userTheme) {
        initial = window.__userTheme;
    } else {
        initial = getSavedTheme() || getSystemPreference();
    }
    applyTheme(initial);

    // Bind toggle button after DOM is ready
    document.addEventListener('DOMContentLoaded', function() {
        var btn = document.getElementById('theme-toggle');
        if (btn) {
            btn.addEventListener('click', toggleTheme);
            updateToggleButton(initial);
        }
    });

    // Listen for system preference changes (only when no explicit preference is set)
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function(e) {
        if (!getSavedTheme() && !(window.__userAuthenticated && window.__userTheme)) {
            applyTheme(e.matches ? 'dark' : 'light');
        }
    });
})();
