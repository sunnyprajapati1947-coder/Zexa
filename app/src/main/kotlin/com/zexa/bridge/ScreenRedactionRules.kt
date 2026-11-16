package com.zexa.bridge

/**
 * Conservative redaction for accessibility snapshots before they leave the
 * Android service. Flagged values are omitted using heuristic checks for
 * credentials, financial/identity labels, common ID patterns, email addresses,
 * and Indian mobile numbers. Detection is not guaranteed.
 */
internal object ScreenRedactionRules {
    private val sensitiveLabel = Regex(
        "(?i)\\b(?:password|passcode|passphrase|pin|otp|one[- ]?time(?: password| code)?|" +
            "verification code|security code|cvv|cvc|card number|credit card|debit card|" +
            "account number|bank account|routing number|iban|ifsc(?: code)?|swift(?: code)?|bic|" +
            "upi pin|upi id|card expiry|expiry date|security answer|date of birth|dob|" +
            "tax identification number|gstin|aadhaar|aadhar|pan number|passport number|" +
            "social security|ssn)\\b"
    )
    private val paymentNumber = Regex("(?<!\\d)(?:\\d[ -]?){12,19}(?!\\d)")
    private val oneTimeCode = Regex("^\\s*\\d{4,8}\\s*$")
    private val emailAddress = Regex("(?i)\\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\\.[A-Z]{2,}\\b")
    private val indianMobile = Regex("(?<!\\d)(?:\\+?91[ -]?)?[6-9]\\d{9}(?!\\d)")
    private val panIdentifier = Regex("(?i)\\b[A-Z]{5}\\d{4}[A-Z]\\b")

    fun shouldRedact(
        isPassword: Boolean,
        isEditable: Boolean,
        className: String,
        viewId: String,
        hint: String,
        text: String,
        description: String,
        sensitiveContext: Boolean = false,
    ): Boolean {
        if (isPassword) return true
        val metadata = listOf(className, viewId, hint, text, description).joinToString(" ")
        val normalizedMetadata = metadata.replace(Regex("[^A-Za-z0-9]+"), " ")
        if (sensitiveLabel.containsMatchIn(normalizedMetadata)) return true

        val values = listOf(text, description, hint)
        if (values.any { paymentNumber.containsMatchIn(it) || emailAddress.containsMatchIn(it) ||
                indianMobile.containsMatchIn(it) || panIdentifier.containsMatchIn(it) }) return true

        return (isEditable && oneTimeCode.matches(text)) ||
            (sensitiveContext && values.any { it.isNotBlank() })
    }

    fun isSensitiveLabel(
        className: String,
        viewId: String,
        hint: String,
        text: String,
        description: String,
    ): Boolean {
        val metadata = listOf(className, viewId, hint, text, description).joinToString(" ")
            .replace(Regex("[^A-Za-z0-9]+"), " ")
        return sensitiveLabel.containsMatchIn(metadata)
    }

}
