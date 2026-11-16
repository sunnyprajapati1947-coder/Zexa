package com.zexa.bridge

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class MemoryFactRulesTest {
    @Test
    fun trimsValidFactsAndRejectsBlankOrOversizedValues() {
        assertEquals("Remember my study goal", MemoryFactRules.normalize("  Remember my study goal  "))
        assertNull(MemoryFactRules.normalize("   "))
        assertNull(MemoryFactRules.normalize("x".repeat(MemoryFactRules.MAX_FACT_LENGTH + 1)))
    }

    @Test
    fun backupRestoreTrimsAndDeduplicatesFactsCaseInsensitively() {
        assertEquals(listOf("Study goal", "Work preference"),
            MemoryFactRules.normalizeImportFacts(listOf(" Study goal ", "study GOAL", "Work preference")))
    }

    @Test(expected = IllegalArgumentException::class)
    fun backupRestoreRejectsBlankFacts() {
        MemoryFactRules.normalizeImportFacts(listOf("valid", "  "))
    }

    @Test(expected = IllegalArgumentException::class)
    fun backupRestoreRejectsTooManyFacts() {
        MemoryFactRules.normalizeImportFacts((1..(MemoryFactRules.MAX_FACTS + 1)).map { "fact $it" })
    }

    @Test
    fun acceptsMaximumLengthAndDefinesBoundedFactCount() {
        assertEquals(MemoryFactRules.MAX_FACT_LENGTH,
            MemoryFactRules.normalize("x".repeat(MemoryFactRules.MAX_FACT_LENGTH))?.length)
        assertEquals(100, MemoryFactRules.MAX_FACTS)
    }
}
