package com.zexa.bridge

import org.json.JSONException
import java.nio.charset.CharacterCodingException

/** Keeps malformed client input distinct from unexpected bridge/service failures. */
internal object BridgeHttpErrorMapping {
    fun status(error: Throwable): Int = when (error) {
        is JSONException, is CharacterCodingException, is IllegalArgumentException -> 400
        else -> 500
    }

    fun message(error: Throwable): String = when (error) {
        is JSONException -> "Malformed JSON request"
        is CharacterCodingException -> "Request body must be valid UTF-8"
        is IllegalArgumentException -> error.message ?: "Invalid request"
        else -> "Internal bridge error"
    }
}
