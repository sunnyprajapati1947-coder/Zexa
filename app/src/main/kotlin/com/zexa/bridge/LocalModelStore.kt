package com.zexa.bridge

import java.io.BufferedInputStream
import java.io.File
import java.io.FileInputStream
import java.io.FileOutputStream
import java.io.InputStream
import java.security.MessageDigest

data class ImportedModel(
    val file: File,
    val sizeBytes: Long,
    val sha256: String,
)

class LocalModelStore(private val directory: File) {
    companion object {
        const val MAX_MODEL_BYTES = 10L * 1024L * 1024L * 1024L
        private const val MODEL_NAME = "zexa-qwen.gguf"
        private const val TEMP_NAME = "zexa-qwen.gguf.partial"
        private val MAGIC = byteArrayOf('G'.code.toByte(), 'G'.code.toByte(), 'U'.code.toByte(), 'F'.code.toByte())
    }

    fun installedModel(): File? {
        val file = File(directory, MODEL_NAME)
        if (!file.isFile || file.length() < 4L) return null
        FileInputStream(file).use { input ->
            val header = ByteArray(4)
            var offset = 0
            while (offset < header.size) {
                val count = input.read(header, offset, header.size - offset)
                if (count < 0) return null
                offset += count
            }
            if (!header.contentEquals(MAGIC)) return null
        }
        return file
    }

    @Synchronized
    fun importModel(input: InputStream, expectedSize: Long? = null): ImportedModel {
        try {
            return importModelInternal(input, expectedSize)
        } finally {
            try {
                input.close()
            } catch (_: Exception) {
                // Closing an already-closed stream is harmless.
            }
        }
    }

    private fun importModelInternal(input: InputStream, expectedSize: Long?): ImportedModel {
        if (expectedSize != null && expectedSize <= 0L) {
            throw IllegalArgumentException("The selected model has an invalid file size.")
        }
        if (expectedSize != null && expectedSize > MAX_MODEL_BYTES) {
            throw IllegalArgumentException("Model exceeds the 10 GiB import limit.")
        }
        if (!directory.exists() && !directory.mkdirs()) {
            throw IllegalStateException("Could not create the private model directory.")
        }
        if (expectedSize != null && expectedSize > directory.usableSpace) {
            throw IllegalStateException("Not enough free storage for this model.")
        }

        val temporary = File(directory, TEMP_NAME)
        if (temporary.exists() && !temporary.delete()) {
            throw IllegalStateException("Could not clear an incomplete previous import.")
        }

        val digest = MessageDigest.getInstance("SHA-256")
        var total = 0L
        var headerChecked = false
        val buffer = ByteArray(DEFAULT_BUFFER_SIZE)
        try {
            BufferedInputStream(input).use { source ->
                FileOutputStream(temporary).use { output ->
                    val header = ByteArray(4)
                    var headerBytes = 0
                    while (headerBytes < header.size) {
                        val count = source.read(header, headerBytes, header.size - headerBytes)
                        if (count < 0) break
                        headerBytes += count
                    }
                    if (headerBytes != 4 || !header.contentEquals(MAGIC)) {
                        throw IllegalArgumentException("Selected file is not a GGUF model.")
                    }
                    headerChecked = true
                    total = 4L
                    digest.update(header)
                    output.write(header)
                    while (true) {
                        val count = source.read(buffer)
                        if (count < 0) break
                        if (count == 0) continue
                        total += count
                        if (total > MAX_MODEL_BYTES) {
                            throw IllegalArgumentException("Model exceeds the 10 GiB import limit.")
                        }
                        digest.update(buffer, 0, count)
                        output.write(buffer, 0, count)
                    }
                    output.fd.sync()
                }
            }
            if (!headerChecked || total < 4L) {
                throw IllegalArgumentException("Selected file is empty or is not a GGUF model.")
            }
            if (expectedSize != null && total != expectedSize) {
                throw IllegalStateException("Model import ended before the expected file size.")
            }

            val destination = File(directory, MODEL_NAME)
            val backup = File(directory, "$MODEL_NAME.previous")
            if (backup.exists()) {
                if (destination.exists()) {
                    if (!backup.delete()) {
                        throw IllegalStateException("Could not rotate the previous model file.")
                    }
                } else if (!backup.renameTo(destination)) {
                    throw IllegalStateException("Could not recover the previous model file.")
                }
            }
            if (destination.exists() && !destination.renameTo(backup)) {
                throw IllegalStateException("Could not safely replace the previous model.")
            }
            if (!temporary.renameTo(destination)) {
                if (backup.exists()) backup.renameTo(destination)
                throw IllegalStateException("Could not finalize the imported model.")
            }
            if (backup.exists()) backup.delete()
            return ImportedModel(destination, total, digest.digest().joinToString("") { "%02x".format(it) })
        } catch (error: Exception) {
            temporary.delete()
            throw error
        }
    }
}
