package com.zexa.bridge

import org.junit.Assert.assertEquals
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

    @Test
    fun persistedLoadedStateDoesNotClaimNativeRuntimeIsStillLoadedAfterRestart() {
        assertEquals(
            "Loaded",
            ModelLoadCoordinator.stateLabel("loaded", true, null)
        )
        assertEquals(
            "Previously loaded; native runtime restarted",
            ModelLoadCoordinator.stateLabel("loaded", false, null)
        )
    }

    @Test
    fun failureAndInterruptedDetailsRemainVisible() {
        assertEquals(
            "Failed: model hash mismatch",
            ModelLoadCoordinator.stateLabel("failed", false, "model hash mismatch")
        )
        assertEquals(
            "Interrupted: process stopped",
            ModelLoadCoordinator.stateLabel("interrupted", false, "process stopped")
        )
    }
}
