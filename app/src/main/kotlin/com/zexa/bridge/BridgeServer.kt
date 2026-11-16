package com.zexa.bridge

import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.io.InputStream
import java.io.BufferedInputStream
import java.net.InetAddress
import java.net.ServerSocket
import java.net.Socket
import java.util.concurrent.Semaphore
import java.util.concurrent.ConcurrentHashMap
import java.nio.charset.StandardCharsets

class BridgeServer(
    private val token: String,
    private val service: ZexaAccessibilityService,
) {
    init {
        require(BridgeSecurityRules.validBridgeToken(token)) {
            "Bridge token must be a 32-byte lowercase hexadecimal value."
        }
    }

    @Volatile private var running = false
    @Volatile private var ready = false
    @Volatile private var server: ServerSocket? = null
    private val clientSlots = Semaphore(4)
    private val activeClients = ConcurrentHashMap.newKeySet<Socket>()

    val isRunning: Boolean
        get() = running && ready && server?.isClosed == false
    private var thread: Thread? = null
    private var generation = 0L

    @Synchronized
    fun start() {
        if (running) return
        generation += 1
        val myGeneration = generation
        running = true
        thread = Thread({
            var socketServer: ServerSocket? = null
            try {
                val ownedServer = ServerSocket(8765, 8, InetAddress.getByName("127.0.0.1"))
                socketServer = ownedServer
                synchronized(this) {
                    if (generation != myGeneration || !running) {
                        ownedServer.close()
                        return@Thread
                    }
                    server = ownedServer
                    ready = true
                }
                while (running) {
                    val socket = ownedServer.accept()
                    if (!clientSlots.tryAcquire()) {
                        try { respond(socket, 503, JSONObject().put("error", "Bridge is busy")) } catch (_: Exception) {}
                        try { socket.close() } catch (_: Exception) {}
                        continue
                    }
                    activeClients.add(socket)
                    Thread({
                        try { handle(socket) } finally {
                            activeClients.remove(socket)
                            clientSlots.release()
                        }
                    }, "zexa-bridge-client").apply { isDaemon = true; start() }
                }
            } catch (_: Exception) {
                // Server is intentionally silent; status is visible in the app.
            } finally {
                synchronized(this) {
                    if (generation == myGeneration && server === socketServer) {
                        ready = false
                        running = false
                        server = null
                        thread = null
                    }
                }
                try { socketServer?.close() } catch (_: Exception) {}
            }
        }, "zexa-bridge-server").apply { isDaemon = true; start() }
    }

    @Synchronized
    fun stop() {
        generation += 1
        ready = false
        running = false
        try { server?.close() } catch (_: Exception) {}
        server = null
        activeClients.forEach { client -> try { client.close() } catch (_: Exception) {} }
        activeClients.clear()
        thread?.interrupt()
        thread = null
    }

    private fun handle(socket: Socket) {
        socket.use { client ->
            client.soTimeout = 5000
            val input = BufferedInputStream(client.getInputStream())
            val requestLine = readHttpLine(input) ?: return
            val parts = requestLine.split(" ")
            if (parts.size != 3) return respond(client, 400, JSONObject().put("error", "Bad request"))
            val method = parts[0]
            val path = parts[1]
            val headers = mutableMapOf<String, String>()
            var headerCount = 0
            while (true) {
                val line = readHttpLine(input) ?: return
                if (line.isEmpty()) break
                headerCount++
                require(headerCount <= 32) { "Too many request headers." }
                val separator = line.indexOf(':')
                if (separator <= 0) return respond(client, 400, JSONObject().put("error", "Malformed header"))
                val name = line.substring(0, separator).trim().lowercase()
                if (headers.containsKey(name)) {
                    return respond(client, 400, JSONObject().put("error", "Duplicate header"))
                }
                headers[name] = line.substring(separator + 1).trim()
            }
            if (headers.containsKey("transfer-encoding")) {
                return respond(client, 400, JSONObject().put("error", "Transfer-Encoding is not supported"))
            }
            val provided = BridgeSecurityRules.bearerToken(headers["authorization"]) ?: ""
            if (!BridgeSecurityRules.tokenMatches(token, provided)) {
                return respond(client, 401, JSONObject().put("error", "Unauthorized"))
            }
            var responseStatus = 200
            val response = try {
                when {
                    method == "GET" && path == "/v1/status" -> service.statusJson()
                    method == "GET" && path == "/v1/grants" -> {
                        val grants = org.json.JSONArray()
                        service.activeTaskActionGrants().forEach { grant ->
                            grants.put(JSONObject()
                                .put("grant_id", grant.grantId)
                                .put("task_id", grant.taskId)
                                .put("allowed_actions", org.json.JSONArray(grant.allowedActions.toList()))
                                .put("expires_at_epoch_ms", grant.expiresAtEpochMs)
                                .put("remaining_actions", grant.remainingActions))
                        }
                        JSONObject().put("ok", true).put("grants", grants)
                    }
                    method == "POST" && path == "/v1/grants/revoke" -> {
                        val length = BridgeSecurityRules.contentLength(headers["content-length"])
                            ?: error("Invalid request body length.")
                        val body = ByteArray(length)
                        var offset = 0
                        while (offset < length) {
                            val read = input.read(body, offset, length - offset)
                            if (read < 0) error("Incomplete request body.")
                            offset += read
                        }
                        val json = JSONObject(String(body, StandardCharsets.UTF_8))
                        require(json.keys().asSequence().toSet() == setOf("grant_id")) {
                            "Grant revoke request must contain only grant_id."
                        }
                        val grantId = json.optString("grant_id", "")
                        require(grantId.matches(Regex("^[A-Za-z0-9-]{1,64}$"))) {
                            "Invalid task grant identifier."
                        }
                        val revoked = service.revokeTaskActionGrant(grantId)
                        JSONObject()
                            .put("ok", revoked)
                            .put("status", if (revoked) "revoked" else "not_found")
                            .put("grant_id", grantId)
                    }
                    method == "GET" && path == "/v1/screen" -> {
                        if (!service.isScreenAccessEnabled()) {
                            responseStatus = 403
                            JSONObject().put("ok", false).put("error", "Screen access is disabled in Zexa settings.")
                        } else service.screenJson()
                    }
                    method == "POST" && path == "/v1/action" -> {
                        val length = BridgeSecurityRules.contentLength(headers["content-length"])
                            ?: error("Invalid request body length.")
                        val body = ByteArray(length)
                        var offset = 0
                        while (offset < length) {
                            val read = input.read(body, offset, length - offset)
                            if (read < 0) error("Incomplete request body.")
                            offset += read
                        }
                        val json = JSONObject(String(body, StandardCharsets.UTF_8))
                        require(json.keys().asSequence().all { it in setOf("action", "payload", "task_id", "grant_id") }) {
                            "Unexpected action request field."
                        }
                        val action = json.optString("action", "")
                        val payload = json.optJSONObject("payload")
                            ?: error("Action payload must be a JSON object.")
                        val hasTaskId = json.has("task_id")
                        val hasGrantId = json.has("grant_id")
                        require(hasTaskId == hasGrantId) { "Task and grant identifiers must be supplied together." }
                        if (hasTaskId) {
                            val taskId = json.optString("task_id", "")
                            val grantId = json.optString("grant_id", "")
                            require(BridgeSecurityRules.validTaskId(taskId)) { "Invalid task identifier." }
                            require(grantId.matches(Regex("^[A-Za-z0-9-]{1,64}$"))) { "Invalid grant identifier." }
                            val granted = service.performGrantedAction(taskId, grantId, action, payload)
                            if (granted.optString("status") == "grant_scope_mismatch_or_expired" ||
                                granted.optString("status") == "grant_unavailable"
                            ) responseStatus = 403
                            granted
                        } else {
                            responseStatus = 202
                            service.queueActionForApproval(action, payload)
                        }
                    }
                    method == "GET" && path.startsWith("/v1/action/") -> {
                        val requestId = path.removePrefix("/v1/action/")
                        require(requestId.matches(Regex("^[A-Za-z0-9-]{1,64}$"))) { "Invalid action request ID." }
                        service.actionResult(requestId)
                            ?: JSONObject()
                                .put("ok", true)
                                .put("status", if (service.isActionPending(requestId)) "pending_approval" else "expired_or_unknown")
                                .put("request_id", requestId)
                    }
                    else -> return respond(client, 404, JSONObject().put("error", "Not found"))
                }
            } catch (error: Exception) {
                return respond(client, 400, JSONObject().put("error", error.message ?: "Invalid request"))
            }
            respond(client, responseStatus, response)
        }
    }

    private fun readHttpLine(input: InputStream): String? {
        val output = ByteArrayOutputStream()
        while (true) {
            val value = input.read()
            if (value < 0) {
                if (output.size() == 0) return null
                break
            }
            if (value == 10) break
            output.write(value)
            require(output.size() <= 8192) { "HTTP header line is too long." }
        }
        val bytes = output.toByteArray()
        val length = if (bytes.isNotEmpty() && bytes.last() == 13.toByte()) bytes.size - 1 else bytes.size
        return String(bytes, 0, length, StandardCharsets.US_ASCII)
    }

    private fun respond(socket: Socket, status: Int, body: JSONObject) {
        val bytes = body.toString().toByteArray(StandardCharsets.UTF_8)
        val reason = when (status) {
            200 -> "OK"
            202 -> "Accepted"
            400 -> "Bad Request"
            401 -> "Unauthorized"
            403 -> "Forbidden"
            503 -> "Service Unavailable"
            else -> "Not Found"
        }
        val header = "HTTP/1.1 $status $reason\r\n" +
            "Content-Type: application/json; charset=utf-8\r\n" +
            "Content-Length: ${bytes.size}\r\n" +
            "Connection: close\r\n\r\n"
        socket.getOutputStream().apply {
            write(header.toByteArray(StandardCharsets.US_ASCII))
            write(bytes)
            flush()
        }
    }
}
