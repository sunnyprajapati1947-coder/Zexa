package com.zexa.bridge

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ReminderRulesTest {
    @Test
    fun acceptsMinimumAndMaximumSupportedDelay() {
        assertTrue(ReminderRules.isValid("Study", "Start revision", 1L))
        assertTrue(ReminderRules.isValid("Study", "Start revision", ReminderScheduler.MAX_DELAY_MINUTES))
    }

    @Test
    fun rejectsBlankOrOversizedText() {
        assertFalse(ReminderRules.isValid("", "Message", 5L))
        assertFalse(ReminderRules.isValid("Title", "  ", 5L))
        assertFalse(ReminderRules.isValid("x".repeat(ReminderWorker.MAX_TITLE_LENGTH + 1), "Message", 5L))
        assertFalse(ReminderRules.isValid("Title", "x".repeat(ReminderWorker.MAX_MESSAGE_LENGTH + 1), 5L))
    }

    @Test
    fun rejectsOutOfRangeDelay() {
        assertFalse(ReminderRules.isValid("Title", "Message", 0L))
        assertFalse(ReminderRules.isValid("Title", "Message", -1L))
        assertFalse(ReminderRules.isValid("Title", "Message", ReminderScheduler.MAX_DELAY_MINUTES + 1L))
    }
}
