package dev.voxhash.ytscompanion

import android.content.Context
import android.util.Log
import java.io.File
import java.io.FileOutputStream

/**
 * Unpacks the bundled default PNG watermark for on-device overlay (slice 4).
 * Full-frame composite matches desktop Suite semantics (stretch + center).
 */
object WatermarkBundle {
    private const val TAG = "WatermarkBundle"
    private const val ASSET = "watermark/default_watermark.png"
    private const val FILE_NAME = "default_watermark.png"

    @Volatile
    private var cached: File? = null

    /** Absolute path to the PNG, or null if the asset is missing. */
    fun ensure(context: Context): String? {
        cached?.takeIf { it.isFile && it.length() > 0L }?.let { return it.absolutePath }
        synchronized(this) {
            cached?.takeIf { it.isFile && it.length() > 0L }?.let { return it.absolutePath }
            val dest = File(File(context.applicationContext.filesDir, "watermark"), FILE_NAME)
            return try {
                if (!dest.isFile || dest.length() == 0L) {
                    unpackAsset(context, dest)
                }
                if (!dest.isFile || dest.length() == 0L) {
                    Log.e(TAG, "watermark missing at ${dest.absolutePath}")
                    null
                } else {
                    cached = dest
                    dest.absolutePath
                }
            } catch (err: Exception) {
                Log.e(TAG, "failed to prepare watermark", err)
                null
            }
        }
    }

    private fun unpackAsset(context: Context, dest: File) {
        dest.parentFile?.mkdirs()
        val tmp = File(dest.parentFile, "$FILE_NAME.tmp")
        context.assets.open(ASSET).use { input ->
            FileOutputStream(tmp).use { output -> input.copyTo(output) }
        }
        if (!tmp.renameTo(dest)) {
            tmp.copyTo(dest, overwrite = true)
            tmp.delete()
        }
    }
}
