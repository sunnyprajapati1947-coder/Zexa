package com.zexa.bridge

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class BridgeSecurityRulesTest {
    @Test
    fun bridgeTokenMustBeAFullRandomHexToken() {
        assertTrue(BridgeSecurityRules.validBridgeToken("a".repeat(64)))
        assertFalse(BridgeSecurityRules.validBridgeToken(""))
        assertFalse(BridgeSecurityRules.validBridgeToken("short"))
        assertFalse(BridgeSecurityRules.validBridgeToken("g".repeat(64)))
        assertFalse(BridgeSecurityRules.validBridgeToken("A".repeat(64)))
    }

    @Test
    fun taskIdentifiersUseARestrictedBoundedFormat() {
        assertTrue(BridgeSecurityRules.validTaskId("research-session-1"))
        assertTrue(BridgeSecurityRules.validTaskId("task_1.alpha"))
        assertFalse(BridgeSecurityRules.validTaskId(""))
        assertFalse(BridgeSecurityRules.validTaskId("../escape"))
        assertFalse(BridgeSecurityRules.validTaskId("task with spaces"))
        assertFalse(BridgeSecurityRules.validTaskId("x".repeat(65)))
    }

    @Test
    fun tokenComparisonRequiresExactMatch() {
        assertTrue(BridgeSecurityRules.tokenMatches("expected-token", "expected-token"))
        assertFalse(BridgeSecurityRules.tokenMatches("expected-token", "other-token"))
    }

    @Test
    fun authorizationRequiresAnExactBearerSchemeAndValidToken() {
        val token = "a".repeat(64)
        assertEquals(token, BridgeSecurityRules.bearerToken("Bearer $token"))
        assertEquals(null, BridgeSecurityRules.bearerToken(token))
        assertEquals(null, BridgeSecurityRules.bearerToken("Basic $token"))
        assertEquals(null, BridgeSecurityRules.bearerToken("bearer $token"))
        assertEquals(null, BridgeSecurityRules.bearerToken("Bearer $token extra"))
        assertEquals(null, BridgeSecurityRules.bearerToken(null))
    }

    @Test
    fun contentLengthIsStrictlyBounded() {
        assertEquals(1, BridgeSecurityRules.contentLength("1"))
        assertEquals(16_000, BridgeSecurityRules.contentLength("16000"))
        assertEquals(null, BridgeSecurityRules.contentLength(null))
        assertEquals(null, BridgeSecurityRules.contentLength("0"))
        assertEquals(null, BridgeSecurityRules.contentLength("16001"))
        assertEquals(null, BridgeSecurityRules.contentLength("not-a-number"))
        assertEquals(null, BridgeSecurityRules.contentLength("+1"))
        assertEquals(1, BridgeSecurityRules.contentLength("01"))
        assertEquals(null, BridgeSecurityRules.contentLength(" 1"))
        assertEquals(null, BridgeSecurityRules.contentLength("1.0"))
        assertEquals(null, BridgeSecurityRules.contentLength("99999"))
    }

    @Test
    fun screenAccessRequiresExplicitBooleanOptIn() {
        assertFalse(BridgeSecurityRules.screenAccessEnabled(null))
        assertFalse(BridgeSecurityRules.screenAccessEnabled(false))
        assertTrue(BridgeSecurityRules.screenAccessEnabled(true))
        assertFalse(BridgeSecurityRules.screenAccessEnabled("true"))
        assertFalse(BridgeSecurityRules.screenAccessEnabled(1))
    }

    @Test
    fun coordinatesRejectNonFiniteAndOutOfRangeValues() {
        assertTrue(BridgeSecurityRules.coordinate(0.0))
        assertTrue(BridgeSecurityRules.coordinate(10_000.0))
        assertFalse(BridgeSecurityRules.coordinate(-0.1))
        assertFalse(BridgeSecurityRules.coordinate(10_000.1))
        assertFalse(BridgeSecurityRules.coordinate(Double.NaN))
        assertFalse(BridgeSecurityRules.coordinate(Double.POSITIVE_INFINITY))
    }

    @Test
    fun gestureDurationIsBounded() {
        assertFalse(BridgeSecurityRules.gestureDuration(99))
        assertTrue(BridgeSecurityRules.gestureDuration(100))
        assertTrue(BridgeSecurityRules.gestureDuration(2_000))
        assertFalse(BridgeSecurityRules.gestureDuration(2_001))
    }


    @Test
    fun actionPayloadsRequireExactFieldsAndTypes() {
        assertTrue(BridgeSecurityRules.validActionPayload("tap", org.json.JSONObject("""{"x":1,"y":2}""")))
        assertTrue(BridgeSecurityRules.validActionPayload("swipe", org.json.JSONObject("""{"x1":1,"y1":2,"x2":3,"y2":4,"duration_ms":450}""")))
        assertTrue(BridgeSecurityRules.validActionPayload("back", org.json.JSONObject()))
        assertTrue(BridgeSecurityRules.validActionPayload("input_text", org.json.JSONObject("""{"text":"hello"}""")))
        assertTrue(BridgeSecurityRules.validActionPayload("launch_app", org.json.JSONObject("""{"package_name":"com.example.app"}""")))
        assertTrue(BridgeSecurityRules.validActionPayload("open_url", org.json.JSONObject("""{"url":"https://example.com/path?q=1"}""")))
        assertFalse(BridgeSecurityRules.validActionPayload("open_url", org.json.JSONObject("""{"url":"javascript:alert(1)"}""")))
        assertFalse(BridgeSecurityRules.validActionPayload("open_url", org.json.JSONObject("""{"url":"https://user:pass@example.com"}""")))
        assertFalse(BridgeSecurityRules.validActionPayload("open_url", org.json.JSONObject("""{"url":"https://example.com","extra":true}""")))
        assertFalse(BridgeSecurityRules.validActionPayload("open_url", org.json.JSONObject("""{"url":"https://exa mple.com"}""")))
        assertFalse(BridgeSecurityRules.validActionPayload("tap", org.json.JSONObject("""{"x":1,"y":2,"extra":true}""")))
        assertFalse(BridgeSecurityRules.validActionPayload("tap", org.json.JSONObject("""{"x":"1","y":2}""")))
        assertFalse(BridgeSecurityRules.validActionPayload("tap", org.json.JSONObject("""{"x":true,"y":2}""")))
        assertFalse(BridgeSecurityRules.validActionPayload("back", org.json.JSONObject("""{"extra":1}""")))
        assertFalse(BridgeSecurityRules.validActionPayload("swipe", org.json.JSONObject("""{"x1":1,"y1":2,"x2":3,"y2":4,"duration_ms":450.5}""")))
        assertFalse(BridgeSecurityRules.validActionPayload("input_text", org.json.JSONObject("""{"text":"   "}""")))
        assertFalse(BridgeSecurityRules.validActionPayload("launch_app", org.json.JSONObject("""{"package_name":"../../bad"}""")))
        assertFalse(BridgeSecurityRules.validActionPayload("run_shell", org.json.JSONObject()))
    }

    @Test
    fun webUrlsRequireHttpSchemeHostAndNoEmbeddedCredentials() {
        assertTrue(BridgeSecurityRules.safeWebUrl("https://example.com"))
        assertTrue(BridgeSecurityRules.safeWebUrl("http://example.com/path"))
        assertFalse(BridgeSecurityRules.safeWebUrl("javascript:alert(1)"))
        assertFalse(BridgeSecurityRules.safeWebUrl("file:///etc/passwd"))
        assertFalse(BridgeSecurityRules.safeWebUrl("https://user:pass@example.com"))
        assertFalse(BridgeSecurityRules.safeWebUrl("https://"))
        assertFalse(BridgeSecurityRules.safeWebUrl("https://example.com/has space"))
        assertFalse(BridgeSecurityRules.safeWebUrl("https://example.com:0/path"))
        assertFalse(BridgeSecurityRules.safeWebUrl("https://example.com:65536/path"))
        assertTrue(BridgeSecurityRules.safeWebUrl("https://example.com:443/path"))
        assertFalse(BridgeSecurityRules.safeWebUrl("https://example.com/" + "a".repeat(2_050)))
    }

    @Test
    fun packageNameMustHaveValidSegments() {
        assertTrue(BridgeSecurityRules.packageName("com.zexa.bridge"))
        assertFalse(BridgeSecurityRules.packageName("com"))
        assertFalse(BridgeSecurityRules.packageName("com..bridge"))
        assertFalse(BridgeSecurityRules.packageName("com.zexa;bad"))
    }
}
