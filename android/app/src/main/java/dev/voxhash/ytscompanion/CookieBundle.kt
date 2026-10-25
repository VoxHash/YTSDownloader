package dev.voxhash.ytscompanion

import android.content.Context
import android.net.Uri
import java.io.File

/**
 * Netscape cookies.txt for yt-dlp on GrapheneOS / AOSP — no Play Services browser cookie APIs.
 * User exports cookies from a desktop browser (or compatible tool) and picks the file via SAF.
 *
 * Slice 6: validate Netscape shape before accepting the import; clearer failure reasons.
 */
object CookieBundle {
    private const val REL_DIR = "cookies"
    private const val REL_NAME = "cookies.txt"
    private const val MAX_BYTES = 8L * 1024L * 1024L

    fun localFile(context: Context): File {
        val dir = File(context.filesDir, REL_DIR)
        if (!dir.exists()) dir.mkdirs()
        return File(dir, REL_NAME)
    }

    fun existingPath(context: Context): String? {
        val f = localFile(context)
        return if (f.isFile && f.length() > 0L) f.absolutePath else null
    }

    /** Summary for UI when a cookie file is present. */
    fun summary(context: Context): String? {
        val path = existingPath(context) ?: return null
        val f = File(path)
        val lines = runCatching { f.readLines() }.getOrDefault(emptyList())
        val cookieRows =
            lines.count { line ->
                val t = line.trim()
                t.isNotEmpty() && !t.startsWith("#")
            }
        return "${f.name} · ${cookieRows} cookie row(s) · ${f.length()} B"
    }

    /**
     * Copy SAF document into app-private storage after Netscape validation.
     * Returns [ImportResult] with path on success or a user-facing reason on failure.
     */
    fun importFromUri(context: Context, uri: Uri): ImportResult {
        val dest = localFile(context)
        dest.parentFile?.mkdirs()
        val tmp = File(dest.parentFile, "$REL_NAME.partial")
        try {
            context.contentResolver.openInputStream(uri)?.use { input ->
                tmp.outputStream().use { output -> input.copyTo(output) }
            } ?: return ImportResult.fail("Could not open selected file (SAF stream null)")
        } catch (e: Exception) {
            tmp.delete()
            return ImportResult.fail("Read failed: ${e.message ?: e.javaClass.simpleName}")
        }
        if (!tmp.isFile || tmp.length() <= 0L) {
            tmp.delete()
            return ImportResult.fail("File is empty — export a Netscape cookies.txt from a desktop browser")
        }
        if (tmp.length() > MAX_BYTES) {
            tmp.delete()
            return ImportResult.fail("File too large (max ${MAX_BYTES / (1024 * 1024)} MiB)")
        }
        val validation = validateNetscape(tmp)
        if (!validation.ok) {
            tmp.delete()
            return ImportResult.fail(validation.reason)
        }
        if (dest.exists()) dest.delete()
        if (!tmp.renameTo(dest)) {
            tmp.copyTo(dest, overwrite = true)
            tmp.delete()
        }
        if (!dest.isFile || dest.length() <= 0L) {
            dest.delete()
            return ImportResult.fail("Could not store cookies in app-private storage")
        }
        return ImportResult.ok(dest.absolutePath, validation.cookieRows)
    }

    fun clear(context: Context) {
        localFile(context).delete()
    }

    /** Host/unit-testable Netscape cookies.txt check. */
    fun validateNetscape(file: File): Validation {
        if (!file.isFile || file.length() <= 0L) {
            return Validation(false, "File is empty", 0)
        }
        val lines =
            try {
                file.readLines()
            } catch (e: Exception) {
                return Validation(false, "Unreadable: ${e.message ?: e.javaClass.simpleName}", 0)
            }
        if (lines.isEmpty()) {
            return Validation(false, "File is empty", 0)
        }
        val joinedHead = lines.take(8).joinToString("\n").lowercase()
        val looksNetscape =
            joinedHead.contains("netscape") ||
                joinedHead.contains("http cookie file") ||
                lines.any { it.trimStart().startsWith("#HttpOnly_", ignoreCase = true) } ||
                lines.any { line ->
                    val parts = line.trim().split('\t')
                    parts.size >= 7 && parts[0].isNotBlank() &&
                        (parts[3].equals("TRUE", true) || parts[3].equals("FALSE", true))
                }
        if (!looksNetscape) {
            return Validation(
                false,
                "Not a Netscape cookies.txt (need # Netscape header or tab-separated cookie rows). " +
                    "GrapheneOS has no cookies-from-browser — export from a desktop browser.",
                0,
            )
        }
        val cookieRows =
            lines.count { line ->
                val t = line.trim()
                if (t.isEmpty() || t.startsWith("#")) return@count false
                val parts = t.split('\t')
                parts.size >= 6
            }
        if (cookieRows == 0) {
            return Validation(
                false,
                "Netscape header found but no cookie rows — re-export while signed in on the site",
                0,
            )
        }
        return Validation(true, "", cookieRows)
    }

    data class Validation(
        val ok: Boolean,
        val reason: String,
        val cookieRows: Int,
    )

    data class ImportResult(
        val ok: Boolean,
        val path: String = "",
        val cookieRows: Int = 0,
        val error: String = "",
    ) {
        companion object {
            fun ok(path: String, cookieRows: Int) =
                ImportResult(ok = true, path = path, cookieRows = cookieRows)

            fun fail(error: String) = ImportResult(ok = false, error = error)
        }
    }
}
