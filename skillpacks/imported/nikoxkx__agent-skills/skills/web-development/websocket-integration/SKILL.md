---
name: websocket-integration
description: Integrates WebSocket real-time communication into a web application. Use when implementing live features like chat, notifications, collaborative editing, or live dashboards.
license: Apache-2.0
compatibility: Claude Code, Codex, Gemini CLI
metadata:
  author: ai-skills
  version: "1.0"
  category: web-development
  tags: websocket, realtime, chat, notifications, socket.io, native-websocket
---

## Overview

Provides complete guidance and code for integrating native WebSockets or Socket.io into web apps, including reconnection with exponential backoff, message envelope format, React hook for lifecycle management, server-side setup (Node/ws or Socket.io), error handling, and authentication patterns for real-time features.

## When to Use This Skill

- Adding live chat, notifications, presence indicators, collaborative editing, or live data dashboards.
- The user mentions "real-time", "WebSocket", "live updates", "push", or "socket".

## Prerequisites

- Backend that can run a WebSocket server (Node.js, Deno, or cloud service like Pusher, Ably, Supabase Realtime).
- Frontend framework (React, vanilla, etc.).
- For production: load balancer that supports WebSocket upgrade (Nginx, ALB, etc.).

## Steps

1. **Choose transport**: Native WebSocket (lightweight) vs Socket.io (more features, fallback).
2. **Define message protocol** (JSON envelope):
   ```json
   { "type": "chat.message", "payload": {...}, "id": "uuid", "timestamp": "..." }
   ```
3. **Client implementation**:
   - Connection, onopen, onmessage, onerror, onclose.
   - Reconnection logic with backoff (max 5 attempts, then show "reconnecting" UI).
   - Heartbeat / ping-pong for keepalive.
4. **React hook** (`useWebSocket`): manages connection, auto-reconnect, typed message handlers.
5. **Server side**: auth on connection (JWT in query or subprotocol), room management, broadcast.
6. **Security**: validate all incoming messages, rate limit, authenticate every connection.
7. **Output**: full hook, example chat component, server route, deployment notes.

## Examples

Complete `useWebSocket.ts` hook, a simple chat UI, and a minimal Node + ws server example are provided.

## Edge Cases & Error Handling

- Network drops: exponential backoff + user notification.
- Auth expiration: refresh token and reconnect.
- Large messages: chunk or use binary when appropriate.
- Browser tab sleep: handle visibilitychange to pause/reconnect.

## Verification

1. Open two browser tabs — messages appear in real time.
2. Kill the server — client shows reconnecting UI and recovers when server restarts.
3. Check browser console for clean connection lifecycle.
4. Success: Real-time features work reliably with graceful degradation.

## References

- [MDN WebSocket API](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)
- [Socket.io Docs](https://socket.io/docs/v4/)
- [ws library (Node)](https://github.com/websockets/ws)
