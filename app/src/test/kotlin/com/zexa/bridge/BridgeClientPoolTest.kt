package com.zexa.bridge

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.net.Socket

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
    fun validatesPositiveCapacity() {
        try {
            BridgeClientPool(0)
            throw AssertionError("Zero capacity must be rejected")
        } catch (_: IllegalArgumentException) {
            // Expected.
        }
    }
}
