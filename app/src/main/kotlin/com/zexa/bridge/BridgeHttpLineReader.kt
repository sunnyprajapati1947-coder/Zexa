package com.zexa.bridge

import java.io.ByteArrayOutputStream
import java.io.InputStream
import java.nio.charset.StandardCharsets

/** Reads exactly one CRLF-terminated HTTP line with a strict byte limit. */
object BridgeHttpLineReader {
    fun read(input: InputStream, maxBytes: Int = 8_192): String? {
        require(maxBytes > 0) { "Maximum HTTP line length must be positive." }
        val output = ByteArrayOutputStream()
        while (true) {
            val value = input.read()
            if (value < 0) {
                if (output.size() == 0) return null
                throw IllegalArgumentException("Incomplete HTTP line.")
            }
            if (value == 10) {
                val bytes = output.toByteArray()
                require(bytes.isNotEmpty() && bytes.last() == 13.toByte()) {
                    "HTTP lines must use CRLF termination."
                }
                return String(bytes, 0, bytes.size - 1, StandardCharsets.US_ASCII)
            }
            output.write(value)
            require(output.size() <= maxBytes) { "HTTP header line is too long." }
        }
    }
}
