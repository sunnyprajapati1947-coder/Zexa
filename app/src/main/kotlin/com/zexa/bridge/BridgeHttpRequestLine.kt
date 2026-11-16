package com.zexa.bridge

/**
 * Strict parser for the HTTP/1.x request-line subset accepted by the local bridge.
 * Only origin-form targets are accepted; absolute-form and control characters are rejected.
 */
data class BridgeHttpRequestLine(val method: String, val target: String, val version: String) {
    companion object {
        private val methodPattern = Regex("^[A-Z]{1,16}$")
        private val targetPattern = Regex("^/[A-Za-z0-9._~!$&'()*+,;=:@%/?-]{0,2047}$")

        fun parse(line: String): BridgeHttpRequestLine? {
            if (line.length !in 14..2100 || line.any { it.code < 0x20 || it.code == 0x7f }) return null
            val parts = line.split(' ')
            if (parts.size != 3 || parts.any { it.isEmpty() }) return null
            val (method, target, version) = parts
            if (!methodPattern.matches(method) || !targetPattern.matches(target)) return null
            if (version != "HTTP/1.0" && version != "HTTP/1.1") return null
            return BridgeHttpRequestLine(method, target, version)
        }
    }
}
