package com.zexa.bridge

import java.io.InputStream
import java.net.Socket
import java.net.SocketTimeoutException
import java.util.concurrent.TimeUnit

/**
 * Applies one deadline to the complete HTTP request read, rather than resetting
 * the socket timeout for every byte. This prevents slow clients from occupying
 * all bounded bridge worker slots by trickling headers indefinitely.
 */
internal class BridgeDeadlineInputStream(
    private val socket: Socket,
    timeoutMs: Int = DEFAULT_TIMEOUT_MS,
) : InputStream() {
    private val deadlineNanos: Long

    init {
        require(timeoutMs in 1..MAX_TIMEOUT_MS) { "Request read timeout is outside the allowed range." }
        deadlineNanos = System.nanoTime() + TimeUnit.MILLISECONDS.toNanos(timeoutMs.toLong())
    }

    private fun updateSocketTimeout() {
        val remainingNanos = deadlineNanos - System.nanoTime()
        if (remainingNanos <= 0L) {
            throw SocketTimeoutException("HTTP request read deadline exceeded.")
        }
        val remainingMs = ((remainingNanos + 999_999L) / 1_000_000L)
            .coerceIn(1L, Int.MAX_VALUE.toLong())
        socket.soTimeout = remainingMs.toInt()
    }

    override fun read(): Int {
        updateSocketTimeout()
        return socket.getInputStream().read()
    }

    override fun read(buffer: ByteArray, offset: Int, length: Int): Int {
        updateSocketTimeout()
        return socket.getInputStream().read(buffer, offset, length)
    }

    companion object {
        const val DEFAULT_TIMEOUT_MS = 10_000
        const val MAX_TIMEOUT_MS = 60_000
    }
}
