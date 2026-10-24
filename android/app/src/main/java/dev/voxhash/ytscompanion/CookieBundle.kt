package dev.voxhash.ytscompanion

import android.content.Context
import android.net.Uri
import java.io.File

/**
 * Netscape cookies.txt for yt-dlp on GrapheneOS / AOSP — no Play Services browser cookie APIs.
 * User exports cookies from a desktop browser (or compatible tool) and picks the file via SAF.
 */
object CookieBundle {
    private const val REL_DIR = "cookies"
    private const val REL_NAME = "cookies.txt"

    fun localFile(context: Context): File {
        val dir = File(context.filesDir, REL_DIR)
        if (!dir.exists()) dir.mkdirs()
        return File(dir, REL_NAME)
    }

    fun existingPath(context: Context): String? {
        val f = localFile(context)
        return if (f.isFile && f.length() > 0L) f.absolutePath else null
    }

    /** Copy SAF document into app-private storage; returns absolute path or null. */
    fun importFromUri(context: Context, uri: Uri): String? {
        val dest = localFile(context)
        dest.parentFile?.mkdirs()
        context.contentResolver.openInputStream(uri)?.use { input ->
            dest.outputStream().use { output -> input.copyTo(output) }
        } ?: return null
        if (!dest.isFile || dest.length() <= 0L) {
            dest.delete()
            return null
        }
        return dest.absolutePath
    }

    fun clear(context: Context) {
        localFile(context).delete()
    }
}
