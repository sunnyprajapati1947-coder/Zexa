package com.zexa.bridge

import org.json.JSONObject
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.net.Socket
import java.net.SocketTimeoutException

class BridgeServerSocketIntegrationTest {
    private class FakeService : BridgeServiceApi {
        override fun statusJson() = JSONObject()
            .put("ok", true)
            .put("accessibility_enabled", true)
            .put("bridge_enabled", true)

        override fun activeTaskActionGrants(): List<TaskActionGrant> = emptyList()
        override fun revokeTaskActionGrant(grantId: String): Boolean = false
        override fun screenJson() = JSONObject().put("ok", true).put("nodes", org.json.JSONArray())
        override fun performGrantedAction(
            taskId: String, grantId: String, action: String, payload: JSONObject
        ) = JSONObject().put("ok", false).put("status", "not_used")
        override fun queueActionForApproval(action: String, payload: JSONObject) =
            JSONObject().put("ok", true).put("status", "pending_approval").put("request_id", "test-1")
        override fun actionResult(requestId: String): JSONObject? = null
    }

    @Test
    fun loopbackServerEnforcesAuthenticationRoutesAndShutdown() {
        val token = "a".repeat(64)
        val server = BridgeServer(token, FakeService())
        server.start()
        try {
            awaitReady(server)

            val status = request("GET /v1/status HTTP/1.1", "Bearer $token")
            assertTrue(status.startsWith("HTTP/1.1 200 "))
            assertTrue(status.contains("\"bridge_enabled\":true"))

            val unauthorized = request("GET /v1/status HTTP/1.1", "Bearer " + "b".repeat(64))
            assertTrue(unauthorized.startsWith("HTTP/1.1 401 "))

            val missingAuth = request("GET /v1/status HTTP/1.1", null)
            assertTrue(missingAuth.startsWith("HTTP/1.1 401 "))

            val wrongMethod = request("POST /v1/status HTTP/1.1", "Bearer $token")
            assertTrue(wrongMethod.startsWith("HTTP/1.1 405 "))

            val unknownRoute = request("GET /v1/not-found HTTP/1.1", "Bearer $token")
            assertTrue(unknownRoute.startsWith("HTTP/1.1 404 "))

            val oversizedBody = request(
                "POST /v1/grants/revoke HTTP/1.1",
                "Bearer $token",
                "Content-Length: 16001",
            )
            assertTrue(oversizedBody.startsWith("HTTP/1.1 400 "))

            val malformed = request("INVALID")
            assertTrue(malformed.startsWith("HTTP/1.1 400 "))
        } finally {
            server.stop()
        }
        assertFalse(server.isRunning)
    }

    private fun awaitReady(server: BridgeServer) {
        val deadline = System.nanoTime() + 5_000_000_000L
        while (!server.isRunning && System.nanoTime() < deadline) {
            Thread.sleep(10)
        }
        assertTrue("BridgeServer did not bind its loopback listener in time", server.isRunning)
    }

    private fun request(requestLine: String, authorization: String? = null, extraHeader: String? = null): String {
        Socket("127.0.0.1", 8765).use { socket ->
            socket.soTimeout = 2_000
            val headers = buildString {
                append(requestLine).append("\r\n")
                append("Host: 127.0.0.1\r\n")
                if (authorization != null) append("Authorization: ").append(authorization).append("\r\n")
                if (extraHeader != null) append(extraHeader).append("\r\n")
                append("Connection: close\r\n\r\n")
            }
            socket.getOutputStream().write(headers.toByteArray(Charsets.US_ASCII))
            socket.getOutputStream().flush()
            return try {
                socket.getInputStream().bufferedReader(Charsets.UTF_8).readText()
            } catch (_: SocketTimeoutException) {
                throw AssertionError("Bridge response timed out")
            }
        }
    }
}
