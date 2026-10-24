package dev.voxhash.ytscompanion

import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URI
import java.net.URL
import java.net.URLEncoder
import java.nio.charset.StandardCharsets
import java.util.Locale
import java.util.concurrent.Executors

/**
 * On-device metadata resolve for the Android Suite path (title only).
 * Uses public oEmbed endpoints — no API keys, no yt-dlp on device yet.
 */
object UrlResolver {
    private val executor = Executors.newSingleThreadExecutor()

    fun resolveTitleAsync(url: String, onResult: (String?) -> Unit) {
        executor.execute {
            val title = runCatching { resolveTitle(url) }.getOrNull()
            onResult(title)
        }
    }

    fun resolveTitle(url: String): String? {
        val trimmed = url.trim()
        if (!CompanionPayload.isHttpUrl(trimmed)) return null
        youtubeOEmbed(trimmed)?.let { return it }
        return noembed(trimmed)
    }

    private fun youtubeOEmbed(pageUrl: String): String? {
        if (!isYoutubeUrl(pageUrl)) return null
        val endpoint =
            "https://www.youtube.com/oembed?format=json&url=" +
                URLEncoder.encode(pageUrl, StandardCharsets.UTF_8.name())
        return fetchOEmbedTitle(endpoint)
    }

    private fun noembed(pageUrl: String): String? {
        val endpoint =
            "https://noembed.com/embed?url=" +
                URLEncoder.encode(pageUrl, StandardCharsets.UTF_8.name())
        return fetchOEmbedTitle(endpoint)
    }

    private fun fetchOEmbedTitle(endpoint: String): String? {
        val conn = (URL(endpoint).openConnection() as HttpURLConnection).apply {
            connectTimeout = 8_000
            readTimeout = 8_000
            requestMethod = "GET"
            setRequestProperty("Accept", "application/json")
            setRequestProperty("User-Agent", "YTSCompanion/0.9 (+https://github.com/VoxHash/YTSDownloader)")
            instanceFollowRedirects = true
        }
        try {
            val code = conn.responseCode
            if (code !in 200..299) return null
            val body = conn.inputStream.bufferedReader(StandardCharsets.UTF_8).use { it.readText() }
            val json = JSONObject(body)
            if (json.has("error")) return null
            val title = json.optString("title").trim()
            return title.ifEmpty { null }
        } finally {
            conn.disconnect()
        }
    }

    private fun isYoutubeUrl(raw: String): Boolean {
        return try {
            val host = URI(raw).host?.lowercase(Locale.US) ?: return false
            host == "youtu.be" ||
                host == "youtube.com" ||
                host.endsWith(".youtube.com") ||
                host == "m.youtube.com" ||
                host == "www.youtube.com" ||
                host == "music.youtube.com"
        } catch (_: Exception) {
            false
        }
    }
}
