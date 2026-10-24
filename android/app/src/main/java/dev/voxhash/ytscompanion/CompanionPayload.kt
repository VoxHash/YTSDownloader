package dev.voxhash.ytscompanion

import org.json.JSONArray
import org.json.JSONObject
import java.net.URI
import java.util.Locale

/**
 * Builds desktop Suite companion inbox payloads (schema v1).
 * See docs/architecture.md — Browser companion handoff contract.
 */
object CompanionPayload {
    const val SCHEMA_VERSION = 1

    /** Flavor-specific: phone → android-companion, quest → quest-companion. */
    val SOURCE: String
        get() = BuildConfig.COMPANION_SOURCE

    fun isHttpUrl(raw: String): Boolean {
        val trimmed = raw.trim()
        if (trimmed.isEmpty()) return false
        return try {
            val uri = URI(trimmed)
            val scheme = uri.scheme?.lowercase(Locale.US)
            (scheme == "http" || scheme == "https") && !uri.host.isNullOrBlank()
        } catch (_: Exception) {
            false
        }
    }

    fun extractFirstUrl(text: String): String? {
        val pattern = Regex("""https?://[^\s<>"')\]]+""", RegexOption.IGNORE_CASE)
        val match = pattern.find(text.trim()) ?: return null
        var url = match.value.trimEnd('.', ',', ';', ')', ']', '"', '\'')
        return if (isHttpUrl(url)) url else null
    }

    fun toJsonDocument(urls: List<String>): String {
        val arr = JSONArray()
        for (url in urls) {
            arr.put(
                JSONObject()
                    .put("schema", SCHEMA_VERSION)
                    .put("url", url)
                    .put("source", SOURCE),
            )
        }
        return JSONObject()
            .put("schema", SCHEMA_VERSION)
            .put("source", SOURCE)
            .put("urls", arr)
            .toString(2)
    }

    fun toJsonl(urls: List<String>): String {
        val sb = StringBuilder()
        for (url in urls) {
            sb.append(
                JSONObject()
                    .put("schema", SCHEMA_VERSION)
                    .put("url", url)
                    .put("source", SOURCE)
                    .toString(),
            )
            sb.append('\n')
        }
        return sb.toString()
    }

    fun suggestedFileName(): String {
        val stamp = System.currentTimeMillis()
        return "yts_companion_$stamp.json"
    }
}
