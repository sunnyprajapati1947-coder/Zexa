package com.zexa.bridge

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.fail
import org.junit.Test
import java.io.ByteArrayInputStream

class BridgeHttpLineReaderTest {
    @Test
    fun readsCrLfTerminatedLinesAndEmptyHeaderTerminator() {
        val input = ByteArrayInputStream("GET / HTTP/1.1\r\n\r\n".toByteArray(Charsets.US_ASCII))
        assertEquals("GET / HTTP/1.1", BridgeHttpLineReader.read(input))
        assertEquals("", BridgeHttpLineReader.read(input))
        assertNull(BridgeHttpLineReader.read(input))
    }

    @Test
    fun rejectsBareLineFeedAndIncompleteEndOfStream() {
        assertRejected("GET / HTTP/1.1\n")
        assertRejected("GET / HTTP/1.1")
    }

    @Test
    fun rejectsControlAndNonAsciiBytes() {
        assertRejectedBytes("GET /é HTTP/1.1\r\n".toByteArray(Charsets.UTF_8))
        assertRejectedBytes(byteArrayOf(71, 69, 84, 32, 47, 1, 32, 72, 84, 84, 80, 47, 49, 46, 49, 13, 10))
    }

    @Test
    fun enforcesLineByteLimit() {
        try {
            BridgeHttpLineReader.read(ByteArrayInputStream("12345\r\n".toByteArray()), 4)
            fail("Oversized HTTP line must be rejected")
        } catch (_: IllegalArgumentException) {
            // Expected.
        }
    }

    private fun assertRejected(value: String) {
        assertRejectedBytes(value.toByteArray(Charsets.US_ASCII))
    }

    private fun assertRejectedBytes(bytes: ByteArray) {
        try {
            BridgeHttpLineReader.read(ByteArrayInputStream(bytes))
            fail("Malformed HTTP line must be rejected")
        } catch (_: IllegalArgumentException) {
            // Expected.
        }
    }
}
