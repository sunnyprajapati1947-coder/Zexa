package com.zexa.bridge

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class BridgeHttpRequestLineTest {
    @Test
    fun parsesValidOriginFormHttp11Request() {
        assertEquals(
            BridgeHttpRequestLine("GET", "/v1/status", "HTTP/1.1"),
            BridgeHttpRequestLine.parse("GET /v1/status HTTP/1.1")
        )
    }

    @Test
    fun acceptsQueryStringsButNotFragmentsOrAbsoluteTargets() {
        assertEquals(
            "/v1/action/id?view=compact",
            BridgeHttpRequestLine.parse("GET /v1/action/id?view=compact HTTP/1.1")?.target
        )
        assertNull(BridgeHttpRequestLine.parse("GET https://example.com/v1/status HTTP/1.1"))
        assertNull(BridgeHttpRequestLine.parse("GET /v1/status#fragment HTTP/1.1"))
    }

    @Test
    fun rejectsMalformedWhitespaceAndUnsupportedHttpVersions() {
        assertNull(BridgeHttpRequestLine.parse("GET  /v1/status HTTP/1.1"))
        assertNull(BridgeHttpRequestLine.parse("GET /v1/status HTTP/1.1 "))
        assertNull(BridgeHttpRequestLine.parse("GET /v1/status HTTP/2"))
        assertNull(BridgeHttpRequestLine.parse("GET\t/v1/status HTTP/1.1"))
        assertNull(BridgeHttpRequestLine.parse("GET /v1/status HTTP/1.1 EXTRA"))
    }

    @Test
    fun rejectsControlCharactersAndOversizedTargets() {
        assertNull(BridgeHttpRequestLine.parse("GET /v1/status\u0000 HTTP/1.1"))
        assertNull(BridgeHttpRequestLine.parse("GET /" + "a".repeat(2100) + " HTTP/1.1"))
    }

    @Test
    fun parsesSyntacticallyValidUnsupportedMethodFor405Handling() {
        assertEquals(
            "DELETE",
            BridgeHttpRequestLine.parse("DELETE /v1/status HTTP/1.1")?.method
        )
    }
}
