---
name: pwa-setup
description: Converts a web app to a Progressive Web App with offline support, install prompts, and push notifications. Use when making a web app installable and offline-capable.
license: Apache-2.0
compatibility: Claude Code, Codex, Gemini CLI
metadata:
  author: ai-skills
  version: "1.0"
  category: web-development
  tags: pwa, service-worker, manifest, offline, push-notifications, web-app-manifest
---

## Overview

Guides the complete conversion of a web app into a Progressive Web App: creating a Web App Manifest, implementing a service worker with caching strategies (Cache First, Network First, Stale-While-Revalidate), offline fallback page, install prompt handling, and push notification setup using the Push API + VAPID keys.

## When to Use This Skill

- The app should feel like a native app (installable from browser).
- Users need to use core features offline (read content, draft forms, view dashboards).
- Adding push notifications for re-engagement.
- The user says "make this a PWA", "add offline support", "installable web app".

## Prerequisites

- HTTPS (required for service workers and push in production; localhost works for dev).
- Modern browser support (all current evergreen browsers).
- For push: a push service (Firebase Cloud Messaging, VAPID + web-push library on server).

## Steps

1. **Create Web App Manifest** (`app/manifest.ts` or `public/manifest.json`):
   - name, short_name, start_url, display ("standalone"), background_color, theme_color, icons (192x192, 512x512, maskable).
   - Screenshots for install prompt (optional but powerful).

2. **Implement Service Worker**:
   - Lifecycle: install → activate → fetch.
   - Caching strategies per asset type:
     - App shell (HTML, CSS, JS critical): Cache First or Stale-While-Revalidate.
     - API/data: Network First with cache fallback.
     - Images: Cache First with long TTL.
   - Use Workbox (recommended) or write a small custom SW.

3. **Offline fallback**:
   - A dedicated offline.html page.
   - In fetch handler, return it when network fails for navigation requests.

4. **Install prompt**:
   - Listen for `beforeinstallprompt`.
   - Show a custom "Install" button.
   - Call `prompt()` on user gesture.
   - Handle `appinstalled` event.

5. **Push notifications**:
   - Request permission.
   - Subscribe to push using VAPID public key.
   - Send subscription to your server.
   - Server sends push using `web-push` library.
   - Handle `push` event in SW and show Notification.

6. **Next.js specific**:
   - Use `next-pwa` plugin or manual setup with `public/sw.js`.
   - Register SW in a client component or layout.

7. **Output**:
   - Full manifest.
   - Service worker code (or Workbox config).
   - React hook or component for install prompt.
   - Push subscription example.
   - VAPID key generation instructions.
   - Testing checklist.

## Examples

Complete `manifest.ts`, a production-ready service worker with multiple strategies, install prompt component, and a minimal push notification flow (client + server) are included.

## Edge Cases & Error Handling

- **Permission denied for notifications**: Graceful UI, never nag.
- **SW update**: Proper skipWaiting + clients.claim, with update UI prompt.
- **Large offline assets**: Be selective about what goes in the cache.
- **Background sync**: For form submissions when offline (using Background Sync API).

## Verification

1. `npm run build && npm run start` — serve over HTTPS (use `serve` or Vercel).
2. Open in Chrome — "Install" button or + icon in address bar appears.
3. Click install — app installs to home screen / apps list.
4. Go offline (DevTools → Network → Offline) — core pages still load.
5. Trigger a push notification from server — it arrives even when app is closed.
6. Lighthouse PWA category = 100.
7. Success: App is installable, works offline for key flows, and can receive push.

## References

- [Web App Manifest](https://developer.mozilla.org/en-US/docs/Web/Manifest)
- [Service Worker API](https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API)
- [Workbox](https://developer.chrome.com/docs/workbox/)
- [Push API + Notifications](https://developer.mozilla.org/en-US/docs/Web/API/Push_API)
- [next-pwa](https://github.com/shadowwalker/next-pwa) or manual setup
