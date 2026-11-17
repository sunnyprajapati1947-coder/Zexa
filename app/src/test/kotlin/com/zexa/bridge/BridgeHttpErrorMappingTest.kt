package com.zexa.bridge

import org.json.JSONException
import org.junit.Assert.assertEquals
import org.junit.Test
import java.nio.charset.CharacterCodingException
import java.net.SocketTimeoutException

class BridgeHttpErrorMappingTest {
    @Test
    fun malformedClientInputMapsToBadRequest() {
        assertEquals(400, BridgeHttpErrorMapping.status(IllegalArgumentException("Invalid payload")))
        assertEquals(400, BridgeHttpErrorMapping.status(JSONException("bad json")))
        assertEquals(400, BridgeHttpErrorMapping.status(CharacterCodingException()))
        assertEquals(408, BridgeHttpErrorMapping.status(SocketTimeoutException()))
        assertEquals("Request timed out", BridgeHttpErrorMapping.message(SocketTimeoutException()))
    }

    @Test
    fun unexpectedFailuresMapToInternalServerErrorWithoutLeakingDetails() {
        val error = IllegalStateException("private service implementation detail")
        assertEquals(500, BridgeHttpErrorMapping.status(error))
        assertEquals("Internal bridge error", BridgeHttpErrorMapping.message(error))
    }

    @Test
    fun validationMessageRemainsUsefulToClient() {
        val error = IllegalArgumentException("Invalid action payload.")
        assertEquals("Invalid action payload.", BridgeHttpErrorMapping.message(error))
    }
}
