package dev.voxhash.ytscompanion

/** One queued media page URL with optional on-device resolved title. */
data class QueueItem(
    val url: String,
    val title: String = "",
)
