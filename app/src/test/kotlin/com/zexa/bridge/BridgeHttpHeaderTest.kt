package com.zexa.bridge

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class BridgeHttpHeaderTest {
    @Test
    fun parsesAndNormalizesValidHeader() {
        assertEquals(
            BridgeHttpHeader("authorization", "Bearer abc"),
            BridgeHttpHeader.parse("Authorization: Bearer abc")
        )
    }

    @Test
    fun rejectsWhitespaceBeforeColonAndInvalidNames() {
        assertNull(BridgeHttpHeader.parse("Content-Length : 4"))
        assertNull(BridgeHttpHeader.parse("Bad Header: value"))
        assertNull(BridgeHttpHeader.parse(": value"))
    }

    @Test
    fun rejectsControlCharactersAndAllowsHorizontalTabInValue() {
        assertNull(BridgeHttpHeader.parse("X-Test: value\u0000"))
        assertNull(BridgeHttpHeader.parse("X-Test: value\u007f"))
        assertEquals("a\tb", BridgeHttpHeader.parse("X-Test: a\tb")?.value)
    }
}
