package com.zexa.bridge

/** HTTP methods exposed by each known local bridge endpoint. */
object BridgeHttpRouteRules {
    private val fixedRoutes = mapOf(
        "/v1/status" to setOf("GET"),
        "/v1/grants" to setOf("GET"),
        "/v1/grants/revoke" to setOf("POST"),
        "/v1/screen" to setOf("GET"),
        "/v1/action" to setOf("POST")
    )

    fun allowedMethods(path: String): Set<String>? {
        fixedRoutes[path]?.let { return it }
        if (path.matches(Regex("^/v1/action/[A-Za-z0-9-]{1,64}$"))) return setOf("GET")
        return null
    }
}
