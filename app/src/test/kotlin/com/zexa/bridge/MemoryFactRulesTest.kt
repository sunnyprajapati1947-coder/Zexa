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
    fun acceptsMaximumLengthAndDefinesBoundedFactCount() {
        assertEquals(MemoryFactRules.MAX_FACT_LENGTH,
            MemoryFactRules.normalize("x".repeat(MemoryFactRules.MAX_FACT_LENGTH))?.length)
        assertEquals(100, MemoryFactRules.MAX_FACTS)
    }
}
