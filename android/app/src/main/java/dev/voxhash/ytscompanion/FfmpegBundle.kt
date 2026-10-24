package dev.voxhash.ytscompanion

import android.content.Context
import android.os.Build
import android.system.Os
import android.util.Log
import java.io.File
import java.io.FileOutputStream

/**
 * Unpacks the bundled arm64-v8a ffmpeg asset for yt-dlp merge (slice 3).
 * Binary is LGPL FFmpeg 8.1.1 (no GPL/nonfree); stream-copy mux only.
 */
object FfmpegBundle {
    private const val TAG = "FfmpegBundle"
    private const val ASSET = "ffmpeg/arm64-v8a/ffmpeg"
    private const val BIN_NAME = "ffmpeg"

    @Volatile
    private var cached: File? = null

    /** Absolute path to executable ffmpeg, or null if unavailable on this ABI / missing asset. */
    fun ensure(context: Context): String? {
        cached?.takeIf { it.isFile && it.canExecute() }?.let { return it.absolutePath }
        synchronized(this) {
            cached?.takeIf { it.isFile && it.canExecute() }?.let { return it.absolutePath }
            if (!isArm64()) {
                Log.i(TAG, "bundled ffmpeg is arm64-v8a only (device ABI unsupported)")
                return null
            }
            val dest = File(File(context.applicationContext.filesDir, "bin"), BIN_NAME)
            return try {
                if (!dest.isFile || dest.length() == 0L) {
                    unpackAsset(context, dest)
                }
                markExecutable(dest)
                if (!dest.isFile || !dest.canExecute()) {
                    Log.e(TAG, "ffmpeg not executable at ${dest.absolutePath}")
                    null
                } else {
                    cached = dest
                    dest.absolutePath
                }
            } catch (err: Exception) {
                Log.e(TAG, "failed to prepare bundled ffmpeg", err)
                null
            }
        }
    }

    private fun isArm64(): Boolean {
        val abis = Build.SUPPORTED_ABIS ?: emptyArray()
        return abis.any { it.equals("arm64-v8a", ignoreCase = true) }
    }

    private fun unpackAsset(context: Context, dest: File) {
        dest.parentFile?.mkdirs()
        val tmp = File(dest.parentFile, "$BIN_NAME.tmp")
        context.assets.open(ASSET).use { input ->
            FileOutputStream(tmp).use { output -> input.copyTo(output) }
        }
        if (!tmp.renameTo(dest)) {
            tmp.copyTo(dest, overwrite = true)
            tmp.delete()
        }
    }

    private fun markExecutable(file: File) {
        file.setReadable(true, true)
        file.setExecutable(true, true)
        try {
            Os.chmod(file.absolutePath, 448) // 0700
        } catch (_: Exception) {
            // setExecutable above is enough on most GrapheneOS / Pixel builds
        }
    }
}
