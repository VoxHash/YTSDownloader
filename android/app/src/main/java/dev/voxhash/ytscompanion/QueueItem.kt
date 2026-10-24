package dev.voxhash.ytscompanion

/** One queued media page URL with optional title + on-device download state. */
data class QueueItem(
    val url: String,
    val title: String = "",
    val downloadStatus: DownloadStatus = DownloadStatus.IDLE,
    val progress: Float = 0f,
    val localPath: String = "",
    val error: String = "",
)

enum class DownloadStatus {
    IDLE,
    QUEUED,
    DOWNLOADING,
    DONE,
    ERROR,
    ;

    companion object {
        fun fromWire(raw: String?): DownloadStatus {
            if (raw.isNullOrBlank()) return IDLE
            return entries.firstOrNull { it.name.equals(raw, ignoreCase = true) } ?: IDLE
        }
    }
}
