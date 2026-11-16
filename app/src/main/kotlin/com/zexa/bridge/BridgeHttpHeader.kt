package com.zexa.bridge

/** Strict parser for one HTTP header field used by the local bridge. */
data class BridgeHttpHeader(val name: String, val value: String) {
    companion object {
        private val namePattern = Regex("^[!#$%&'*+.^_`|~0-9A-Za-z-]+$")

        fun parse(line: String): BridgeHttpHeader? {
            val separator = line.indexOf(':')
            if (separator <= 0) return null
            val rawName = line.substring(0, separator)
            if (!namePattern.matches(rawName)) return null
            val rawValue = line.substring(separator + 1)
            if (rawValue.any { it != '\t' && it.code !in 0x20..0x7e }) return null
            return BridgeHttpHeader(rawName.lowercase(), rawValue.trim())
        }
    }
}
