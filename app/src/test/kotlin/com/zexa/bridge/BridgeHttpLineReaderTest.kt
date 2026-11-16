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
        assertRejected("GET /\\u0001 HTTP/1.1\\r\\n")
        assertRejected("GET /é HTTP/1.1\\r\\n")
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
        try {
            BridgeHttpLineReader.read(ByteArrayInputStream(value.toByteArray(Charsets.US_ASCII)))
            fail("Malformed HTTP line must be rejected")
        } catch (_: IllegalArgumentException) {
            // Expected.
        }
    }
}
