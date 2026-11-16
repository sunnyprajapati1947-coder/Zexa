package com.zexa.bridge

import org.json.JSONObject
import java.security.MessageDigest
import java.net.URI

/**
 * Pure validation rules shared by the local bridge and JVM unit tests.
 * This class does not perform Android actions or access device state.
 */
internal object BridgeSecurityRules {
    fun validTaskId(taskId: String): Boolean =
        taskId.matches(Regex("^[A-Za-z0-9._:-]{1,64}$"))

    fun validBridgeToken(value: String): Boolean =
        value.matches(Regex("^[0-9a-f]{64}$"))

    fun tokenMatches(expected: String, provided: String): Boolean =
        MessageDigest.isEqual(
            expected.toByteArray(Charsets.UTF_8),
            provided.toByteArray(Charsets.UTF_8),
        )

    fun bearerToken(header: String?): String? {
        val value = header ?: return null
        if (!value.startsWith("Bearer ")) return null
        val token = value.removePrefix("Bearer ")
        return token.takeIf { validBridgeToken(it) }
    }

    fun contentLength(raw: String?): Int? {
        if (raw == null || !raw.matches(Regex("^[0-9]{1,5}$"))) return null
        val length = raw.toIntOrNull() ?: return null
        return length.takeIf { it in 1..16_000 }
    }

    fun screenAccessEnabled(value: Any?): Boolean = value == true

    fun coordinate(value: Double): Boolean =
        value.isFinite() && value in 0.0..10_000.0

    fun gestureDuration(value: Long): Boolean =
        value in 100L..2_000L

    fun packageName(value: String): Boolean =
        value.matches(Regex("^[A-Za-z0-9_]+(\\.[A-Za-z0-9_]+)+$"))

    /** Accept only explicit HTTP(S) URLs without embedded credentials. */
    fun safeWebUrl(value: String): Boolean {
        if (value.isBlank() || value.length > 2_048 || value.any { it.isWhitespace() || it.isISOControl() }) {
            return false
        }
        return try {
            val uri = URI(value)
            val scheme = uri.scheme?.lowercase()
            (scheme == "https" || scheme == "http") &&
                !uri.host.isNullOrBlank() &&
                uri.rawUserInfo == null &&
                (uri.port == -1 || uri.port in 1..65_535)
        } catch (_: Exception) {
            false
        }
    }

    /**
     * Exact allowlisted payload contract. Reject unknown keys and coercible
     * JSON values (for example strings/booleans where numbers are required).
     */
    fun validActionPayload(action: String, payload: JSONObject): Boolean {
        val required: Set<String>
        val optional: Set<String>
        when (action) {
            "tap" -> { required = setOf("x", "y"); optional = emptySet() }
            "swipe", "scroll" -> {
                required = setOf("x1", "y1", "x2", "y2")
                optional = setOf("duration_ms")
            }
            "back", "home" -> { required = emptySet(); optional = emptySet() }
            "input_text" -> { required = setOf("text"); optional = emptySet() }
            "launch_app" -> { required = setOf("package_name"); optional = emptySet() }
            "open_url" -> { required = setOf("url"); optional = emptySet() }
            else -> return false
        }
        val keys = payload.keys().asSequence().toSet()
        if (!keys.containsAll(required) || (keys - required - optional).isNotEmpty()) return false

        val coordinateKeys = when (action) {
            "tap" -> listOf("x", "y")
            "swipe", "scroll" -> listOf("x1", "y1", "x2", "y2")
            else -> emptyList()
        }
        for (key in coordinateKeys) {
            val value = payload.opt(key) as? Number ?: return false
            if (!coordinate(value.toDouble())) return false
        }
        if (payload.has("duration_ms")) {
            val duration = payload.opt("duration_ms") as? Number ?: return false
            if (duration.toDouble() % 1.0 != 0.0 || !gestureDuration(duration.toLong())) return false
        }
        if (action == "input_text") {
            val value = payload.opt("text") as? String ?: return false
            if (value.isBlank() || value.length > 500) return false
        }
        if (action == "launch_app") {
            val value = payload.opt("package_name") as? String ?: return false
            if (!packageName(value)) return false
        }
        if (action == "open_url") {
            val value = payload.opt("url") as? String ?: return false
            if (!safeWebUrl(value)) return false
        }
        return true
    }
}
