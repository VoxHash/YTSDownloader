package dev.voxhash.ytscompanion

import android.content.Context
import android.util.Log
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import org.json.JSONObject
import java.io.File
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicBoolean

/**
 * Chaquopy bridge to on-device yt-dlp (Android Suite path slices 2–4).
 * Uses the Unlicense yt-dlp package via pip — no third-party downloader UI code.
 * Slice 3 passes bundled arm64 ffmpeg for A/V merge; slice 4 optional PNG watermark.
 */
object YtDlpBridge {
    private const val TAG = "YtDlpBridge"
    private val initLock = Any()
    private val started = AtomicBoolean(false)
    private val executor = Executors.newSingleThreadExecutor()

    /** Called from Python progress_hooks (snake_case method name required). */
    interface ProgressCallback {
        fun on_progress(pct: Double, eta: String)
    }

    fun ensureStarted(context: Context) {
        if (started.get()) return
        synchronized(initLock) {
            if (started.get()) return
            if (!Python.isStarted()) {
                Python.start(AndroidPlatform(context.applicationContext))
            }
            started.set(true)
        }
    }

    fun mediaDir(context: Context): File {
        val base =
            context.getExternalFilesDir(android.os.Environment.DIRECTORY_MOVIES)
                ?: context.getExternalFilesDir(null)
                ?: context.filesDir
        val dir = File(base, "YTSCompanion")
        if (!dir.exists()) dir.mkdirs()
        return dir
    }

    fun downloadAsync(
        context: Context,
        url: String,
        applyWatermark: Boolean,
        onProgress: (Float) -> Unit,
        onDone: (Result) -> Unit,
    ) {
        executor.execute {
            val result =
                runCatching {
                    ensureStarted(context)
                    val module = Python.getInstance().getModule("yts_dlp_worker")
                    val outDir = mediaDir(context).absolutePath
                    val ffmpeg = FfmpegBundle.ensure(context)
                    val watermark =
                        if (applyWatermark) WatermarkBundle.ensure(context) else null
                    val callback =
                        object : ProgressCallback {
                            override fun on_progress(pct: Double, eta: String) {
                                onProgress(pct.toFloat())
                            }
                        }
                    val raw =
                        when {
                            !ffmpeg.isNullOrBlank() && !watermark.isNullOrBlank() ->
                                module
                                    .callAttr(
                                        "download",
                                        url,
                                        outDir,
                                        callback,
                                        ffmpeg,
                                        watermark,
                                    ).toString()
                            !ffmpeg.isNullOrBlank() ->
                                module.callAttr("download", url, outDir, callback, ffmpeg).toString()
                            else ->
                                module.callAttr("download", url, outDir, callback).toString()
                        }
                    parseResult(raw)
                }.getOrElse { err ->
                    Log.e(TAG, "download failed", err)
                    Result(ok = false, error = err.message ?: err.toString())
                }
            onDone(result)
        }
    }

    private fun parseResult(raw: String): Result {
        val json = JSONObject(raw)
        return Result(
            ok = json.optBoolean("ok", false),
            path = json.optString("path").trim(),
            title = json.optString("title").trim(),
            error = json.optString("error").trim(),
            watermarked = json.optBoolean("watermarked", false),
        )
    }

    data class Result(
        val ok: Boolean,
        val path: String = "",
        val title: String = "",
        val error: String = "",
        val watermarked: Boolean = false,
    )
}
