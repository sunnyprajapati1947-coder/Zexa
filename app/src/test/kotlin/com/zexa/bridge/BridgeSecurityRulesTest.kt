package com.zexa.bridge

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class BridgeSecurityRulesTest {
    @Test
    fun tokenComparisonRequiresExactMatch() {
        assertTrue(BridgeSecurityRules.tokenMatches("expected-token", "expected-token"))
        assertFalse(BridgeSecurityRules.tokenMatches("expected-token", "other-token"))
    }

    @Test
    fun contentLengthIsStrictlyBounded() {
        assertEquals(1, BridgeSecurityRules.contentLength("1"))
        assertEquals(16_000, BridgeSecurityRules.contentLength("16000"))
        assertEquals(null, BridgeSecurityRules.contentLength(null))
        assertEquals(null, BridgeSecurityRules.contentLength("0"))
        assertEquals(null, BridgeSecurityRules.contentLength("16001"))
        assertEquals(null, BridgeSecurityRules.contentLength("not-a-number"))
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
    fun packageNameMustHaveValidSegments() {
        assertTrue(BridgeSecurityRules.packageName("com.zexa.bridge"))
        assertFalse(BridgeSecurityRules.packageName("com"))
        assertFalse(BridgeSecurityRules.packageName("com..bridge"))
        assertFalse(BridgeSecurityRules.packageName("com.zexa;bad"))
    }
}
