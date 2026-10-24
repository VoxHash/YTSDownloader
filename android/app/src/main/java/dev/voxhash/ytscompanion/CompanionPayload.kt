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

    fun toJsonDocument(items: List<QueueItem>): String {
        val arr = JSONArray()
        for (item in items) {
            val row =
                JSONObject()
                    .put("schema", SCHEMA_VERSION)
                    .put("url", item.url)
                    .put("source", SOURCE)
            if (item.title.isNotBlank()) {
                row.put("title", item.title)
            }
            arr.put(row)
        }
        return JSONObject()
            .put("schema", SCHEMA_VERSION)
            .put("source", SOURCE)
            .put("urls", arr)
            .toString(2)
    }

    fun toJsonl(items: List<QueueItem>): String {
        val sb = StringBuilder()
        for (item in items) {
            val row =
                JSONObject()
                    .put("schema", SCHEMA_VERSION)
                    .put("url", item.url)
                    .put("source", SOURCE)
            if (item.title.isNotBlank()) {
                row.put("title", item.title)
            }
            sb.append(row.toString())
            sb.append('\n')
        }
        return sb.toString()
    }

    fun suggestedFileName(): String {
        val stamp = System.currentTimeMillis()
        return "yts_companion_$stamp.json"
    }
}
