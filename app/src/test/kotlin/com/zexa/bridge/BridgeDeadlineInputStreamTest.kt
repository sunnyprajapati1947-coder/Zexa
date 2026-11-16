package com.zexa.bridge

import org.junit.Assert.assertTrue
import org.junit.Test
import java.net.ServerSocket
import java.net.Socket
import java.net.SocketTimeoutException
import kotlin.concurrent.thread

class BridgeDeadlineInputStreamTest {
    @Test
    fun slowTrickleCannotResetTheTotalRequestDeadline() {
        ServerSocket(0).use { listener ->
            val client = thread(isDaemon = true) {
                Socket("127.0.0.1", listener.localPort).use { socket ->
                    repeat(10) {
                        try {
                            Thread.sleep(60)
                            socket.getOutputStream().write('A'.code)
                            socket.getOutputStream().flush()
                        } catch (_: Exception) {
                            return@thread
                        }
                    }
                }
            }
            listener.accept().use { accepted ->
                val input = BridgeDeadlineInputStream(accepted, 180)
                var received = 0
                try {
                    while (input.read() >= 0) received++
                    throw AssertionError("Expected the total request deadline to expire.")
                } catch (_: SocketTimeoutException) {
                    assertTrue("Expected partial trickle data before the shared deadline", received in 1..3)
                }
            }
            client.join(1_000)
        }
    }

    @Test
    fun rejectsInvalidTimeoutConfiguration() {
        try {
            BridgeDeadlineInputStream(Socket(), 0)
            throw AssertionError("Zero timeout must be rejected.")
        } catch (_: IllegalArgumentException) {
            // Expected.
        }
    }
}
