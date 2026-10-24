package dev.voxhash.ytscompanion

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject

/** Persistent local URL queue (SharedPreferences). No cloud sync. */
class QueueStore(context: Context) {
    private val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    fun load(): MutableList<QueueItem> {
        val raw = prefs.getString(KEY_URLS, "[]") ?: "[]"
        val arr = JSONArray(raw)
        val out = mutableListOf<QueueItem>()
        for (i in 0 until arr.length()) {
            val value = arr.opt(i) ?: continue
            when (value) {
                is String -> {
                    val url = value.trim()
                    if (url.isNotEmpty()) out.add(QueueItem(url))
                }
                is JSONObject -> {
                    val url = value.optString("url").trim()
                    if (url.isEmpty()) continue
                    out.add(
                        QueueItem(
                            url = url,
                            title = value.optString("title").trim(),
                            downloadStatus = DownloadStatus.fromWire(value.optString("downloadStatus")),
                            progress = value.optDouble("progress", 0.0).toFloat(),
                            localPath = value.optString("localPath").trim(),
                            error = value.optString("error").trim(),
                        ),
                    )
                }
            }
        }
        return out
    }

    fun save(items: List<QueueItem>) {
        val arr = JSONArray()
        items.forEach { item ->
            arr.put(
                JSONObject()
                    .put("url", item.url)
                    .put("title", item.title)
                    .put("downloadStatus", item.downloadStatus.name)
                    .put("progress", item.progress.toDouble())
                    .put("localPath", item.localPath)
                    .put("error", item.error),
            )
        }
        prefs.edit().putString(KEY_URLS, arr.toString()).apply()
    }

    fun getExportTreeUri(): String? = prefs.getString(KEY_TREE_URI, null)

    fun setExportTreeUri(uri: String?) {
        prefs.edit().putString(KEY_TREE_URI, uri).apply()
    }

    fun isWatermarkEnabled(): Boolean = prefs.getBoolean(KEY_WATERMARK, false)

    fun setWatermarkEnabled(enabled: Boolean) {
        prefs.edit().putBoolean(KEY_WATERMARK, enabled).apply()
    }

    companion object {
        private const val PREFS = "yts_companion"
        private const val KEY_URLS = "queue_urls"
        private const val KEY_TREE_URI = "export_tree_uri"
        private const val KEY_WATERMARK = "watermark_enabled"
    }
}
