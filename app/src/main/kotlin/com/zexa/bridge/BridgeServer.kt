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
            val provided = headers["authorization"]?.removePrefix("Bearer ") ?: ""
            if (!BridgeSecurityRules.tokenMatches(token, provided)) {
                return respond(client, 401, JSONObject().put("error", "Unauthorized"))
            }
            val response = try {
                when {
                    method == "GET" && path == "/v1/status" -> service.statusJson()
                    method == "GET" && path == "/v1/screen" -> service.screenJson()
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
                        val action = json.optString("action", "")
                        val payload = json.optJSONObject("payload") ?: JSONObject()
                        service.perform(action, payload)
                    }
                    else -> return respond(client, 404, JSONObject().put("error", "Not found"))
                }
            } catch (error: Exception) {
                return respond(client, 400, JSONObject().put("error", error.message ?: "Invalid request"))
            }
            respond(client, 200, response)
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
            400 -> "Bad Request"
            401 -> "Unauthorized"
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
