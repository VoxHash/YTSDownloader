package dev.voxhash.ytscompanion

import android.content.Context
import org.json.JSONArray

/** Persistent local URL queue (SharedPreferences). No cloud sync. */
class QueueStore(context: Context) {
    private val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    fun load(): MutableList<String> {
        val raw = prefs.getString(KEY_URLS, "[]") ?: "[]"
        val arr = JSONArray(raw)
        val out = mutableListOf<String>()
        for (i in 0 until arr.length()) {
            val url = arr.optString(i).trim()
            if (url.isNotEmpty()) out.add(url)
        }
        return out
    }

    fun save(urls: List<String>) {
        val arr = JSONArray()
        urls.forEach { arr.put(it) }
        prefs.edit().putString(KEY_URLS, arr.toString()).apply()
    }

    fun getExportTreeUri(): String? = prefs.getString(KEY_TREE_URI, null)

    fun setExportTreeUri(uri: String?) {
        prefs.edit().putString(KEY_TREE_URI, uri).apply()
    }

    companion object {
        private const val PREFS = "yts_companion"
        private const val KEY_URLS = "queue_urls"
        private const val KEY_TREE_URI = "export_tree_uri"
    }
}
