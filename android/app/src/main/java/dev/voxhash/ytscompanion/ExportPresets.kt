package dev.voxhash.ytscompanion

/** Desktop Suite export preset ids mirrored on Android (audio / video+audio / watermark). */
object ExportPresets {
    const val AUDIO_ONLY = "audio_only"
    const val VIDEO_AUDIO = "video_audio"
    const val WATERMARK = "watermark"

    val ALL: List<String> = listOf(AUDIO_ONLY, VIDEO_AUDIO, WATERMARK)

    fun normalize(raw: String?): String {
        val key = (raw ?: "").trim().lowercase()
        return if (key in ALL) key else VIDEO_AUDIO
    }

    fun usesWatermark(preset: String): Boolean = normalize(preset) == WATERMARK

    fun isAudio(preset: String): Boolean = normalize(preset) == AUDIO_ONLY

    fun displayName(preset: String): String =
        when (normalize(preset)) {
            AUDIO_ONLY -> "Audio only"
            WATERMARK -> "Watermark"
            else -> "Video + audio"
        }
}
