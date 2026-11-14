package com.zexa.bridge

import java.security.MessageDigest

/**
 * Pure validation rules shared by the local bridge and JVM unit tests.
 * This class does not perform Android actions or access device state.
 */
internal object BridgeSecurityRules {
    fun tokenMatches(expected: String, provided: String): Boolean =
        MessageDigest.isEqual(
            expected.toByteArray(Charsets.UTF_8),
            provided.toByteArray(Charsets.UTF_8),
        )

    fun contentLength(raw: String?): Int? {
        val length = raw?.toIntOrNull() ?: return null
        return length.takeIf { it in 1..16_000 }
    }

    fun coordinate(value: Double): Boolean =
        value.isFinite() && value in 0.0..10_000.0

    fun gestureDuration(value: Long): Boolean =
        value in 100L..2_000L

    fun packageName(value: String): Boolean =
        value.matches(Regex("^[A-Za-z0-9_]+(\\.[A-Za-z0-9_]+)+$"))
}
