// Minimal Service Worker for PWA Installability
// No complex caching as requested to avoid latency and stale content issues.

const CACHE_NAME = 'nas-manager-v1';

self.addEventListener('install', (event) => {
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    event.waitUntil(clients.claim());
});

// Simple fetch listener to satisfy PWA criteria (must have a fetch listener)
self.addEventListener('fetch', (event) => {
    // Just let the browser handle the request normally (passthrough)
    return;
});
