package com.zexa.bridge

import java.net.Socket

/**
 * Bounded ownership registry for accepted client sockets.
 * Register/release are idempotent at the socket-identity boundary; shutdown closes
 * every socket still owned by a worker and clears capacity atomically.
 */
internal class BridgeClientPool(private val capacity: Int = 4) {
    private val active = LinkedHashSet<Socket>()

    init {
        require(capacity > 0) { "Client capacity must be positive." }
    }

    @Synchronized
    fun register(socket: Socket): Boolean {
        if (active.size >= capacity || socket.isClosed) return false
        return active.add(socket)
    }

    @Synchronized
    fun release(socket: Socket) {
        active.remove(socket)
    }

    @Synchronized
    fun closeAll() {
        active.toList().forEach { socket ->
            try { socket.close() } catch (_: Exception) {}
        }
        active.clear()
    }

    @Synchronized
    fun activeCount(): Int = active.size
}
