package com.zexa.bridge

import org.junit.Assert.assertEquals
import org.junit.Assert.fail
import org.junit.Test

class BridgeHttpBodyTest {
    @Test
    fun decodesValidUtf8() {
        assertEquals("{\"text\":\"hello €\"}", BridgeHttpBody.decodeUtf8("{\"text\":\"hello €\"}".toByteArray(Charsets.UTF_8)))
    }

    @Test
    fun rejectsMalformedUtf8InsteadOfReplacingBytes() {
        try {
            BridgeHttpBody.decodeUtf8(byteArrayOf(0xC3.toByte(), 0x28))
            fail("Malformed UTF-8 must be rejected")
        } catch (_: java.nio.charset.CharacterCodingException) {
            // Expected: invalid UTF-8 must not be silently normalized.
        }
    }
}
