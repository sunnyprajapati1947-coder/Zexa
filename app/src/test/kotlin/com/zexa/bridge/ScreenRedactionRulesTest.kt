package com.zexa.bridge

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ScreenRedactionRulesTest {
    private fun check(
        isPassword: Boolean = false,
        isEditable: Boolean = false,
        className: String = "android.widget.TextView",
        viewId: String = "",
        hint: String = "",
        text: String = "",
        description: String = "",
        sensitiveContext: Boolean = false,
    ) = ScreenRedactionRules.shouldRedact(
        isPassword, isEditable, className, viewId, hint, text, description, sensitiveContext
    )

    @Test
    fun passwordFieldsAreAlwaysRedacted() {
        assertTrue(check(isPassword = true, text = "secret-value"))
    }

    @Test
    fun sensitiveLabelsInViewMetadataAreRedacted() {
        assertTrue(check(viewId = "app:id/otp_input", text = "123456"))
        assertTrue(check(hint = "Enter CVV", isEditable = true, text = "123"))
        assertTrue(check(description = "Bank account number"))
        assertTrue(check(text = "UPI PIN"))
    }

    @Test
    fun likelyOneTimeCodesInEditableFieldsAreRedacted() {
        assertTrue(check(isEditable = true, className = "android.widget.EditText", text = "482913"))
        assertFalse(check(isEditable = false, text = "482913"))
        assertFalse(check(isEditable = true, text = "order 482913"))
    }

    @Test
    fun paymentAndIdentityNumbersAreRedacted() {
        assertTrue(check(text = "4111 1111 1111 1111"))
        assertTrue(check(text = "ABCDE1234F"))
    }

    @Test
    fun contactDetailsAreRedacted() {
        assertTrue(check(text = "person@example.com"))
        assertTrue(check(text = "+91 9876543210"))
    }

    @Test
    fun additionalFinancialAndIdentityLabelsAreRedacted() {
        assertTrue(check(hint = "Enter IFSC code", isEditable = true, text = "ABCD0123456"))
        assertTrue(check(viewId = "bank:iban_field", text = "GB82WEST12345698765432"))
        assertTrue(check(description = "Date of birth"))
        assertTrue(check(text = "UPI ID"))
        assertTrue(check(hint = "Card expiry date"))
        assertTrue(check(text = "GSTIN"))
    }

    @Test
    fun valuesInSiblingNodesAreRedactedWhenSensitiveLabelIsPresent() {
        assertTrue(ScreenRedactionRules.isSensitiveLabel(
            className = "android.widget.TextView",
            viewId = "",
            hint = "",
            text = "Date of birth",
            description = "",
        ))
        assertTrue(check(text = "12/03/2009", sensitiveContext = true))
        assertTrue(check(text = "482913", sensitiveContext = true))
    }

    @Test
    fun ordinaryUiTextRemainsAvailable() {
        assertFalse(check(text = "Settings"))
        assertFalse(check(text = "Continue to next page"))
        assertFalse(check(text = "Search products"))
    }
}
