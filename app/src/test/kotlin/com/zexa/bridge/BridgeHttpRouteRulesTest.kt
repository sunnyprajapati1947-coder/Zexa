package com.zexa.bridge

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class BridgeHttpRouteRulesTest {
    @Test
    fun exposesOnlyIntendedMethodsForFixedRoutes() {
        assertEquals(setOf("GET"), BridgeHttpRouteRules.allowedMethods("/v1/status"))
        assertEquals(setOf("GET"), BridgeHttpRouteRules.allowedMethods("/v1/grants"))
        assertEquals(setOf("POST"), BridgeHttpRouteRules.allowedMethods("/v1/grants/revoke"))
        assertEquals(setOf("GET"), BridgeHttpRouteRules.allowedMethods("/v1/screen"))
        assertEquals(setOf("POST"), BridgeHttpRouteRules.allowedMethods("/v1/action"))
    }

    @Test
    fun distinguishesWrongMethodFromUnknownRoute() {
        assertEquals(false, BridgeHttpRouteRules.isMethodAllowed("POST", "/v1/status"))
        assertEquals(false, BridgeHttpRouteRules.isMethodAllowed("GET", "/v1/action"))
        assertEquals(true, BridgeHttpRouteRules.isMethodAllowed("POST", "/v1/action"))
        assertNull(BridgeHttpRouteRules.isMethodAllowed("GET", "/v1/not-a-route"))
    }

    @Test
    fun actionResultRouteAllowsOnlyGetAndValidIdentifiers() {
        assertEquals(setOf("GET"), BridgeHttpRouteRules.allowedMethods("/v1/action/request-123"))
        assertNull(BridgeHttpRouteRules.allowedMethods("/v1/action/"))
        assertNull(BridgeHttpRouteRules.allowedMethods("/v1/action/invalid_id"))
        assertNull(BridgeHttpRouteRules.allowedMethods("/v1/unknown"))
    }
}
