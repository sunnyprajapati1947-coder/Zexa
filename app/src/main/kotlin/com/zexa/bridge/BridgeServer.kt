package com.zexa.bridge

import org.json.JSONObject
import java.io.BufferedInputStream
import java.net.InetAddress
import java.net.ServerSocket
import java.net.Socket
import java.net.SocketTimeoutException
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
    private val clientPool = BridgeClientPool(4)

    /** True while startup is in progress or the bound listener is active. */
    val isActive: Boolean
        get() = running

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
        val serverThread = Thread({
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
                    // Register atomically with stop(): an accept racing shutdown must not
                    // escape active-client tracking and process a request after stop().
                    var registered = false
                    var capacityExceeded = false
                    synchronized(this) {
                        if (running && generation == myGeneration && server === ownedServer) {
                            registered = clientPool.register(socket)
                            capacityExceeded = !registered
                        }
                    }
                    if (!registered) {
                        if (capacityExceeded) {
                            try { respond(socket, 503, JSONObject().put("error", "Bridge is busy")) } catch (_: Exception) {}
                            try { socket.close() } catch (_: Exception) {}
                            continue
                        }
                        try { socket.close() } catch (_: Exception) {}
                        break
                    }
                    try {
                        Thread({
                            try { handle(socket) } finally {
                                clientPool.release(socket)
                            }
                        }, "zexa-bridge-client").apply {
                            isDaemon = true
                            start()
                        }
                    } catch (_: Exception) {
                        // A failed worker launch must release the socket ownership slot.
                        clientPool.release(socket)
                        try { socket.close() } catch (_: Exception) {}
                    }
                }
            } catch (_: Exception) {
                // Server is intentionally silent; status is visible in the app.
            } finally {
                synchronized(this) {
                    if (generation == myGeneration && server === socketServer) {
                        // An unexpected accept-loop exit is also a session boundary:
                        // no client worker may outlive the server session.
                        clientPool.closeAll()
                        ready = false
                        running = false
                        server = null
                        thread = null
                    }
                }
                try { socketServer?.close() } catch (_: Exception) {}
            }
        }, "zexa-bridge-server").apply { isDaemon = true }
        thread = serverThread
        try {
            serverThread.start()
        } catch (_: Exception) {
            // A failed server-thread launch must not leave the bridge reporting itself running.
            running = false
            ready = false
            server = null
            thread = null
            generation += 1L
        }
    }

    @Synchronized
    fun stop() {
        generation += 1
        ready = false
        running = false
        try { server?.close() } catch (_: Exception) {}
        server = null
        clientPool.closeAll()
        thread?.interrupt()
        thread = null
    }

    private fun handle(socket: Socket) {
        socket.use { client ->
            val input = BufferedInputStream(
                BridgeDeadlineInputStream(client, BridgeDeadlineInputStream.DEFAULT_TIMEOUT_MS)
            )
            val requestLine = try {
                readHttpLine(input)
            } catch (_: SocketTimeoutException) {
                return respond(client, 408, JSONObject().put("error", "Request timed out"))
            } catch (_: Exception) {
                return respond(client, 400, JSONObject().put("error", "Malformed request line"))
            } ?: return
            val parsedRequest = BridgeHttpRequestLine.parse(requestLine)
                ?: return respond(client, 400, JSONObject().put("error", "Bad request line"))
            val method = parsedRequest.method
            val path = parsedRequest.routePath
            val headers = try {
                val parsedHeaders = mutableMapOf<String, String>()
                var headerCount = 0
                var totalHeaderBytes = 0
                while (true) {
                    val line = readHttpLine(input) ?: error("Incomplete request headers.")
                    totalHeaderBytes += line.length + 2
                    require(totalHeaderBytes <= 16_384) { "Request headers are too large." }
                    if (line.isEmpty()) break
                    headerCount++
                    require(headerCount <= 32) { "Too many request headers." }
                    val header = BridgeHttpHeader.parse(line)
                        ?: error("Malformed request header.")
                    require(!parsedHeaders.containsKey(header.name)) { "Duplicate request header." }
                    parsedHeaders[header.name] = header.value
                }
                parsedHeaders
            } catch (_: SocketTimeoutException) {
                return respond(client, 408, JSONObject().put("error", "Request timed out"))
            } catch (_: Exception) {
                return respond(client, 400, JSONObject().put("error", "Malformed request headers"))
            }
            if (parsedRequest.version == "HTTP/1.1" && headers["host"].isNullOrBlank()) {
                return respond(client, 400, JSONObject().put("error", "HTTP/1.1 requires a Host header"))
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
                            ?: throw IllegalArgumentException("Invalid request body length.")
                        val body = ByteArray(length)
                        var offset = 0
                        while (offset < length) {
                            val read = input.read(body, offset, length - offset)
                            if (read < 0) throw IllegalArgumentException("Incomplete request body.")
                            offset += read
                        }
                        val json = JSONObject(BridgeHttpBody.decodeUtf8(body))
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
                        val snapshot = try {
                            service.screenJson()
                        } catch (error: ActionExecutionUnknownException) {
                            // A service-thread timeout is not a malformed HTTP request.
                            // Preserve the unknown outcome so callers do not treat it
                            // as a validation failure or retry a potentially active read.
                            JSONObject()
                                .put("ok", false)
                                .put("status", "execution_unknown")
                                .put("error", error.message ?: "Screen snapshot result is unknown.")
                        }
                        if (snapshot.optBoolean("screen_access_disabled")) responseStatus = 403
                        snapshot
                    }
                    method == "POST" && path == "/v1/action" -> {
                        val length = BridgeSecurityRules.contentLength(headers["content-length"])
                            ?: throw IllegalArgumentException("Invalid request body length.")
                        val body = ByteArray(length)
                        var offset = 0
                        while (offset < length) {
                            val read = input.read(body, offset, length - offset)
                            if (read < 0) throw IllegalArgumentException("Incomplete request body.")
                            offset += read
                        }
                        val json = JSONObject(BridgeHttpBody.decodeUtf8(body))
                        require(json.keys().asSequence().all { it in setOf("action", "payload", "task_id", "grant_id") }) {
                            "Unexpected action request field."
                        }
                        val action = json.optString("action", "")
                        val payload = json.optJSONObject("payload")
                            ?: throw IllegalArgumentException("Action payload must be a JSON object.")
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
                                .put("status", "expired_or_unknown")
                                .put("request_id", requestId)
                    }
                    BridgeHttpRouteRules.isMethodAllowed(method, path) == false ->
                        return respond(client, 405, JSONObject().put("error", "Method not allowed"))
                    else -> return respond(client, 404, JSONObject().put("error", "Not found"))
                }
            } catch (error: Exception) {
                // Malformed input is a client error; unexpected service/runtime failures
                // are server errors and must not leak internal exception details.
                return respond(
                    client,
                    BridgeHttpErrorMapping.status(error),
                    JSONObject().put("error", BridgeHttpErrorMapping.message(error)),
                )
            }
            respond(client, responseStatus, response)
        }
    }

    private fun readHttpLine(input: java.io.InputStream): String? =
        BridgeHttpLineReader.read(input)

    private fun respond(socket: Socket, status: Int, body: JSONObject) {
        val bytes = body.toString().toByteArray(StandardCharsets.UTF_8)
        val reason = when (status) {
            200 -> "OK"
            202 -> "Accepted"
            400 -> "Bad Request"
            401 -> "Unauthorized"
            403 -> "Forbidden"
            405 -> "Method Not Allowed"
            408 -> "Request Timeout"
            500 -> "Internal Server Error"
            503 -> "Service Unavailable"
            else -> "Not Found"
        }
        val header = "HTTP/1.1 $status $reason\r\n" +
            "Content-Type: application/json; charset=utf-8\r\n" +
            "Content-Length: ${bytes.size}\r\n" +
            "Cache-Control: no-store\r\n" +
            "Pragma: no-cache\r\n" +
            "X-Content-Type-Options: nosniff\r\n" +
            "Connection: close\r\n\r\n"
        socket.getOutputStream().apply {
            write(header.toByteArray(StandardCharsets.US_ASCII))
            write(bytes)
            flush()
        }
    }
}
