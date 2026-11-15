package com.zexa.bridge

import java.io.ByteArrayInputStream
import java.io.File
import java.io.InputStream
import java.security.MessageDigest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder

class LocalModelStoreTest {
    @get:Rule
    val temporaryFolder = TemporaryFolder()

    @Test
    fun importsValidGgufIntoPrivateDirectoryAndReturnsSha256() {
        val bytes = byteArrayOf(0x47, 0x47, 0x55, 0x46, 1, 2, 3, 4)
        val store = LocalModelStore(temporaryFolder.newFolder("models"))

        val result = store.importModel(ByteArrayInputStream(bytes), bytes.size.toLong())

        assertTrue(result.file.isFile)
        assertEquals(bytes.size.toLong(), result.sizeBytes)
        val expected = MessageDigest.getInstance("SHA-256")
            .digest(bytes).joinToString("") { "%02x".format(it) }
        assertEquals(expected, result.sha256)
        assertEquals(result.file, store.installedModel())
    }

    @Test
    fun acceptsStreamsThatReturnShortReads() {
        val bytes = byteArrayOf(0x47, 0x47, 0x55, 0x46, 9, 8, 7)
        val shortReadStream = object : InputStream() {
            private var index = 0
            override fun read(): Int = if (index >= bytes.size) -1 else bytes[index++].toInt() and 0xff
            override fun read(target: ByteArray, offset: Int, length: Int): Int {
                if (index >= bytes.size) return -1
                val count = minOf(2, length, bytes.size - index)
                System.arraycopy(bytes, index, target, offset, count)
                index += count
                return count
            }
        }
        val store = LocalModelStore(temporaryFolder.newFolder("short-read"))

        val result = store.importModel(shortReadStream, bytes.size.toLong())

        assertEquals(bytes.size.toLong(), result.sizeBytes)
        assertTrue(result.file.isFile)
    }

    @Test
    fun rejectsNonGgufAndDoesNotLeavePartialFile() {
        val directory = temporaryFolder.newFolder("invalid")
        val store = LocalModelStore(directory)

        try {
            store.importModel(ByteArrayInputStream("not a model".toByteArray()))
            throw AssertionError("Expected invalid GGUF rejection.")
        } catch (expected: IllegalArgumentException) {
            assertTrue(expected.message!!.contains("GGUF"))
        }

        assertFalse(File(directory, "zexa-qwen.gguf.partial").exists())
        assertEquals(null, store.installedModel())
    }

    @Test
    fun failedReplacementPreservesPreviouslyInstalledModel() {
        val directory = temporaryFolder.newFolder("replace")
        val store = LocalModelStore(directory)
        val original = byteArrayOf(0x47, 0x47, 0x55, 0x46, 1)
        val imported = store.importModel(ByteArrayInputStream(original))
        val previousHash = imported.sha256

        try {
            store.importModel(ByteArrayInputStream(byteArrayOf(0x00, 0x01, 0x02, 0x03)))
            throw AssertionError("Expected invalid replacement rejection.")
        } catch (_: IllegalArgumentException) {
            // The previously installed model must remain intact.
        }

        val installed = store.installedModel()
        assertNotNull(installed)
        assertEquals(previousHash, MessageDigest.getInstance("SHA-256")
            .digest(installed!!.readBytes()).joinToString("") { "%02x".format(it) })
    }

    @Test
    fun rejectsDeclaredFilesLargerThanImportLimit() {
        val store = LocalModelStore(temporaryFolder.newFolder("too-large"))
        try {
            store.importModel(ByteArrayInputStream(byteArrayOf()), LocalModelStore.MAX_MODEL_BYTES + 1)
            throw AssertionError("Expected size limit rejection.")
        } catch (expected: IllegalArgumentException) {
            assertTrue(expected.message!!.contains("10 GiB"))
        }
    }
}
