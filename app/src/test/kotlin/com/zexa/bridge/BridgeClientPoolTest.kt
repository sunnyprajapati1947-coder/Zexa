package com.zexa.bridge

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.net.Socket
import java.util.concurrent.CountDownLatch
import java.util.concurrent.atomic.AtomicInteger

class BridgeClientPoolTest {
    @Test
    fun enforcesCapacityAndReleasesSlotsExactlyOnce() {
        val pool = BridgeClientPool(2)
        val first = Socket()
        val second = Socket()
        val third = Socket()

        assertTrue(pool.register(first))
        assertTrue(pool.register(second))
        assertFalse(pool.register(third))
        assertEquals(2, pool.activeCount())

        pool.release(first)
        pool.release(first)
        assertEquals(1, pool.activeCount())
        assertTrue(pool.register(third))

        pool.closeAll()
        assertEquals(0, pool.activeCount())
        assertTrue(first.isClosed)
        assertTrue(second.isClosed)
        assertTrue(third.isClosed)
    }

    @Test
    fun rejectsClosedSocketsAndDuplicateRegistration() {
        val pool = BridgeClientPool()
        val socket = Socket()
        assertTrue(pool.register(socket))
        assertFalse(pool.register(socket))
        pool.release(socket)
        socket.close()
        assertFalse(pool.register(socket))
    }


    @Test
    fun concurrentRegistrationsNeverExceedCapacity() {
        val pool = BridgeClientPool(3)
        val start = CountDownLatch(1)
        val finished = CountDownLatch(12)
        val accepted = AtomicInteger(0)
        val sockets = (1..12).map { Socket() }

        sockets.forEach { socket ->
            Thread {
                start.await()
                if (pool.register(socket)) accepted.incrementAndGet()
                finished.countDown()
            }.start()
        }
        start.countDown()
        finished.await()

        assertEquals(3, accepted.get())
        assertEquals(3, pool.activeCount())
        pool.closeAll()
        assertEquals(0, pool.activeCount())
        assertTrue(sockets.all { it.isClosed })
    }

    @Test
    fun validatesPositiveCapacity() {
        try {
            BridgeClientPool(0)
            throw AssertionError("Zero capacity must be rejected")
        } catch (_: IllegalArgumentException) {
            // Expected.
        }
    }
}
