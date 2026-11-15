package com.zexa.bridge

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ModelLoadCoordinatorTest {
    @Test
    fun interruptionOnlyAppliesToNonTerminalLoadStates() {
        assertTrue(ModelLoadCoordinator.shouldPublishInterrupted("queued"))
        assertTrue(ModelLoadCoordinator.shouldPublishInterrupted("waiting"))
        assertTrue(ModelLoadCoordinator.shouldPublishInterrupted("checking"))
        assertTrue(ModelLoadCoordinator.shouldPublishInterrupted("loading"))

        assertFalse(ModelLoadCoordinator.shouldPublishInterrupted("loaded"))
        assertFalse(ModelLoadCoordinator.shouldPublishInterrupted("failed"))
        assertFalse(ModelLoadCoordinator.shouldPublishInterrupted("interrupted"))
        assertFalse(ModelLoadCoordinator.shouldPublishInterrupted("idle"))
    }
}
