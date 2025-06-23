/*
 * Enum class to support flags
 * Author: Yekesa Kosuru
 */
enum ErrorRecoveryMode {
    STRICT,      // Fail on any error
    TOLERANT,    // Try to recover and continue
    IGNORE       // Ignore all errors
}
