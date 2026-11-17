package com.zexa.bridge

import org.junit.Assert.assertTrue
import org.junit.Test
import java.net.ServerSocket
import java.net.Socket
import java.net.SocketTimeoutException
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import kotlin.concurrent.thread

class BridgeDeadlineInputStreamTest {
    @Test
    fun slowTrickleCannotResetTheTotalRequestDeadline() {
        ServerSocket(0).use { listener ->
            val firstByteSent = CountDownLatch(1)
            val client = thread(isDaemon = true) {
                Socket("127.0.0.1", listener.localPort).use { socket ->
                    try {
                        val output = socket.getOutputStream()
                        output.write('A'.code)
                        output.flush()
                        firstByteSent.countDown()
                        repeat(10) {
                            Thread.sleep(60)
                            output.write('A'.code)
                            output.flush()
                        }
                    } catch (_: Exception) {
                        // The server closes the connection when the shared deadline expires.
                    }
                }
            }
            listener.accept().use { accepted ->
                assertTrue("Client should send its first byte before the deadline starts", firstByteSent.await(1, TimeUnit.SECONDS))
                val input = BridgeDeadlineInputStream(accepted, 180)
                var received = 0
                try {
                    while (input.read() >= 0) received++
                    throw AssertionError("Expected the total request deadline to expire.")
                } catch (_: SocketTimeoutException) {
                    assertTrue("Expected trickle data before the shared deadline, got $received bytes", received in 1 until 10)
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
