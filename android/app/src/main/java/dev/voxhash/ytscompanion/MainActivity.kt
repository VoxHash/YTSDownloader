package dev.voxhash.ytscompanion

import android.content.ContentValues
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Environment
import android.provider.MediaStore
import android.view.LayoutInflater
import android.view.ViewGroup
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.documentfile.provider.DocumentFile
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.google.android.material.button.MaterialButton
import com.google.android.material.textfield.TextInputEditText
import android.widget.TextView
import java.io.File
import java.io.OutputStreamWriter
import java.util.ArrayDeque

open class MainActivity : AppCompatActivity() {
    private lateinit var store: QueueStore
    private lateinit var urlInput: TextInputEditText
    private lateinit var emptyLabel: TextView
    private lateinit var exportFolderLabel: TextView
    private lateinit var adapter: QueueAdapter
    private val items = mutableListOf<QueueItem>()
    private val resolving = mutableSetOf<String>()
    private val downloadQueue = ArrayDeque<String>()
    private var downloadActive = false

    private val createDocument =
        registerForActivityResult(ActivityResultContracts.CreateDocument("application/json")) { uri ->
            if (uri != null) writePayloadToUri(uri)
        }

    private val openTree =
        registerForActivityResult(ActivityResultContracts.OpenDocumentTree()) { uri ->
            if (uri != null) {
                contentResolver.takePersistableUriPermission(
                    uri,
                    Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_GRANT_WRITE_URI_PERMISSION,
                )
                store.setExportTreeUri(uri.toString())
                refreshExportFolderLabel()
            }
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        store = QueueStore(this)
        items.clear()
        items.addAll(store.load())
        // Reset in-flight states after process death.
        for (i in items.indices) {
            val st = items[i].downloadStatus
            if (st == DownloadStatus.DOWNLOADING || st == DownloadStatus.QUEUED) {
                items[i] =
                    items[i].copy(
                        downloadStatus = DownloadStatus.IDLE,
                        progress = 0f,
                        error = "",
                    )
            }
        }

        urlInput = findViewById(R.id.urlInput)
        emptyLabel = findViewById(R.id.emptyLabel)
        exportFolderLabel = findViewById(R.id.exportFolderLabel)
        val queueList = findViewById<RecyclerView>(R.id.queueList)

        adapter =
            QueueAdapter(
                items,
                resolving,
                onRemove = { index ->
                    items.removeAt(index)
                    persistAndRefresh()
                },
                onDownload = { index ->
                    if (index in items.indices) enqueueDownload(items[index].url)
                },
            )
        queueList.layoutManager = LinearLayoutManager(this)
        queueList.adapter = adapter

        findViewById<MaterialButton>(R.id.addButton).setOnClickListener { addFromInput() }
        findViewById<MaterialButton>(R.id.clearButton).setOnClickListener {
            items.clear()
            downloadQueue.clear()
            persistAndRefresh()
        }
        findViewById<MaterialButton>(R.id.pickFolderButton).setOnClickListener {
            openTree.launch(null)
        }
        findViewById<MaterialButton>(R.id.exportButton).setOnClickListener { exportInbox() }
        findViewById<MaterialButton>(R.id.exportDownloadsButton).setOnClickListener {
            exportToDownloads()
        }
        findViewById<MaterialButton>(R.id.shareButton).setOnClickListener { sharePayload() }
        findViewById<MaterialButton>(R.id.downloadQueueButton).setOnClickListener {
            enqueueAllDownloads()
        }

        refreshExportFolderLabel()
        persistAndRefresh()
        items.filter { it.title.isBlank() }.forEach { scheduleResolve(it.url) }
        // Warm Python/yt-dlp off the critical path.
        Thread {
            runCatching {
                YtDlpBridge.ensureStarted(this)
                FfmpegBundle.ensure(this)
            }
        }.start()
        handleIncomingIntent(intent)
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        handleIncomingIntent(intent)
    }

    private fun handleIncomingIntent(intent: Intent?) {
        if (intent == null) return
        when (intent.action) {
            Intent.ACTION_SEND -> {
                if (intent.type?.startsWith("text/") == true) {
                    val shared = intent.getStringExtra(Intent.EXTRA_TEXT).orEmpty()
                    addUrl(CompanionPayload.extractFirstUrl(shared) ?: shared)
                }
            }
            Intent.ACTION_VIEW -> {
                intent.dataString?.let { addUrl(it) }
            }
            ACTION_EXPORT_DOWNLOADS -> {
                exportToDownloads()
            }
            ACTION_DOWNLOAD_QUEUE -> {
                enqueueAllDownloads()
            }
        }
        if (intent.getBooleanExtra(EXTRA_EXPORT_DOWNLOADS, false)) {
            exportToDownloads()
        }
        if (intent.getBooleanExtra(EXTRA_DOWNLOAD_QUEUE, false)) {
            enqueueAllDownloads()
        }
    }

    private fun addFromInput() {
        addUrl(urlInput.text?.toString().orEmpty())
        urlInput.setText("")
    }

    private fun addUrl(raw: String) {
        val url = CompanionPayload.extractFirstUrl(raw) ?: raw.trim()
        if (!CompanionPayload.isHttpUrl(url)) {
            Toast.makeText(this, R.string.invalid_url, Toast.LENGTH_SHORT).show()
            return
        }
        if (items.any { it.url.equals(url, ignoreCase = true) }) {
            Toast.makeText(this, R.string.added, Toast.LENGTH_SHORT).show()
            return
        }
        items.add(0, QueueItem(url = url))
        persistAndRefresh()
        Toast.makeText(this, R.string.added, Toast.LENGTH_SHORT).show()
        scheduleResolve(url)
    }

    private fun scheduleResolve(url: String) {
        if (!resolving.add(url)) return
        adapter.notifyDataSetChanged()
        UrlResolver.resolveTitleAsync(url) { title ->
            runOnUiThread {
                resolving.remove(url)
                val idx = items.indexOfFirst { it.url.equals(url, ignoreCase = true) }
                if (idx < 0) {
                    adapter.notifyDataSetChanged()
                    return@runOnUiThread
                }
                val resolved = title?.takeIf { it.isNotBlank() } ?: ""
                items[idx] = items[idx].copy(title = resolved)
                persistAndRefresh()
                if (resolved.isEmpty()) {
                    Toast.makeText(this, R.string.resolve_failed, Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    private fun enqueueAllDownloads() {
        if (items.isEmpty()) {
            Toast.makeText(this, R.string.empty_queue, Toast.LENGTH_SHORT).show()
            return
        }
        var added = 0
        items.forEach { item ->
            if (item.downloadStatus != DownloadStatus.DONE &&
                item.downloadStatus != DownloadStatus.DOWNLOADING &&
                item.downloadStatus != DownloadStatus.QUEUED
            ) {
                if (enqueueDownload(item.url, toast = false)) added++
            }
        }
        if (added > 0) {
            Toast.makeText(this, R.string.download_started, Toast.LENGTH_SHORT).show()
        } else if (downloadActive || downloadQueue.isNotEmpty()) {
            Toast.makeText(this, R.string.download_busy, Toast.LENGTH_SHORT).show()
        }
    }

    private fun enqueueDownload(url: String, toast: Boolean = true): Boolean {
        val idx = items.indexOfFirst { it.url.equals(url, ignoreCase = true) }
        if (idx < 0) return false
        val cur = items[idx]
        if (cur.downloadStatus == DownloadStatus.DOWNLOADING ||
            cur.downloadStatus == DownloadStatus.QUEUED
        ) {
            if (toast) Toast.makeText(this, R.string.download_busy, Toast.LENGTH_SHORT).show()
            return false
        }
        if (downloadQueue.any { it.equals(url, ignoreCase = true) }) return false
        items[idx] =
            cur.copy(
                downloadStatus = DownloadStatus.QUEUED,
                progress = 0f,
                error = "",
            )
        downloadQueue.addLast(url)
        persistAndRefresh()
        if (toast) Toast.makeText(this, R.string.download_started, Toast.LENGTH_SHORT).show()
        pumpDownloads()
        return true
    }

    private fun pumpDownloads() {
        if (downloadActive) return
        val next = downloadQueue.pollFirst() ?: return
        val idx = items.indexOfFirst { it.url.equals(next, ignoreCase = true) }
        if (idx < 0) {
            pumpDownloads()
            return
        }
        downloadActive = true
        items[idx] =
            items[idx].copy(
                downloadStatus = DownloadStatus.DOWNLOADING,
                progress = 0f,
                error = "",
            )
        persistAndRefresh()
        val url = items[idx].url
        YtDlpBridge.downloadAsync(
            this,
            url,
            onProgress = { pct ->
                runOnUiThread {
                    val i = items.indexOfFirst { it.url.equals(url, ignoreCase = true) }
                    if (i < 0) return@runOnUiThread
                    items[i] =
                        items[i].copy(
                            downloadStatus = DownloadStatus.DOWNLOADING,
                            progress = pct,
                        )
                    adapter.notifyItemChanged(i)
                }
            },
            onDone = { result ->
                runOnUiThread {
                    downloadActive = false
                    val i = items.indexOfFirst { it.url.equals(url, ignoreCase = true) }
                    if (i >= 0) {
                        if (result.ok) {
                            val title =
                                result.title.takeIf { it.isNotBlank() } ?: items[i].title
                            items[i] =
                                items[i].copy(
                                    title = title,
                                    downloadStatus = DownloadStatus.DONE,
                                    progress = 100f,
                                    localPath = result.path,
                                    error = "",
                                )
                            Toast.makeText(
                                this,
                                getString(R.string.download_done, File(result.path).name),
                                Toast.LENGTH_LONG,
                            ).show()
                        } else {
                            val err = result.error.ifBlank { "unknown error" }
                            items[i] =
                                items[i].copy(
                                    downloadStatus = DownloadStatus.ERROR,
                                    error = err,
                                )
                            Toast.makeText(
                                this,
                                getString(R.string.download_failed, err),
                                Toast.LENGTH_LONG,
                            ).show()
                        }
                        persistAndRefresh()
                    }
                    pumpDownloads()
                }
            },
        )
    }

    private fun persistAndRefresh() {
        store.save(items)
        adapter.notifyDataSetChanged()
        emptyLabel.visibility = if (items.isEmpty()) android.view.View.VISIBLE else android.view.View.GONE
    }

    private fun refreshExportFolderLabel() {
        val tree = store.getExportTreeUri()
        exportFolderLabel.text =
            if (tree.isNullOrBlank()) {
                getString(R.string.export_folder_none)
            } else {
                getString(R.string.export_folder_label, tree)
            }
    }

    private fun exportInbox() {
        if (items.isEmpty()) {
            Toast.makeText(this, R.string.empty_queue, Toast.LENGTH_SHORT).show()
            return
        }
        val treeUri = store.getExportTreeUri()
        if (!treeUri.isNullOrBlank()) {
            val tree = DocumentFile.fromTreeUri(this, Uri.parse(treeUri))
            if (tree != null && tree.canWrite()) {
                val name = CompanionPayload.suggestedFileName()
                val file = tree.createFile("application/json", name)
                if (file != null) {
                    writePayloadToUri(file.uri)
                    return
                }
            }
        }
        createDocument.launch(CompanionPayload.suggestedFileName())
    }

    private fun writePayloadToUri(uri: Uri) {
        try {
            contentResolver.openOutputStream(uri)?.use { os ->
                OutputStreamWriter(os, Charsets.UTF_8).use { writer ->
                    writer.write(CompanionPayload.toJsonDocument(items))
                }
            }
            Toast.makeText(this, R.string.exported, Toast.LENGTH_SHORT).show()
        } catch (_: Exception) {
            Toast.makeText(this, R.string.export_failed, Toast.LENGTH_SHORT).show()
        }
    }

    /**
     * Write companion JSON without SAF / share chooser (ADB-friendly).
     * Public Downloads via MediaStore + app-specific external files copy.
     */
    private fun exportToDownloads() {
        if (items.isEmpty()) {
            Toast.makeText(this, R.string.empty_queue, Toast.LENGTH_SHORT).show()
            return
        }
        val name = CompanionPayload.suggestedFileName()
        val body = CompanionPayload.toJsonDocument(items)
        try {
            val appDir =
                getExternalFilesDir(Environment.DIRECTORY_DOWNLOADS)
                    ?: getExternalFilesDir(null)
                    ?: filesDir
            val appFile = File(appDir, name)
            appFile.parentFile?.mkdirs()
            appFile.writeText(body, Charsets.UTF_8)

            var publicOk = false
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                val values =
                    ContentValues().apply {
                        put(MediaStore.MediaColumns.DISPLAY_NAME, name)
                        put(MediaStore.MediaColumns.MIME_TYPE, "application/json")
                        put(
                            MediaStore.MediaColumns.RELATIVE_PATH,
                            Environment.DIRECTORY_DOWNLOADS + "/YTSCompanion",
                        )
                    }
                val uri =
                    contentResolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values)
                if (uri != null) {
                    contentResolver.openOutputStream(uri)?.use { os ->
                        OutputStreamWriter(os, Charsets.UTF_8).use { it.write(body) }
                    }
                    publicOk = true
                }
            } else {
                @Suppress("DEPRECATION")
                val legacy =
                    File(
                        Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS),
                        "YTSCompanion",
                    )
                legacy.mkdirs()
                File(legacy, name).writeText(body, Charsets.UTF_8)
                publicOk = true
            }

            val shown =
                if (publicOk) {
                    "Download/YTSCompanion/$name"
                } else {
                    appFile.absolutePath
                }
            Toast.makeText(this, getString(R.string.exported_downloads, shown), Toast.LENGTH_LONG)
                .show()
        } catch (_: Exception) {
            Toast.makeText(this, R.string.export_failed, Toast.LENGTH_SHORT).show()
        }
    }

    private fun sharePayload() {
        if (items.isEmpty()) {
            Toast.makeText(this, R.string.empty_queue, Toast.LENGTH_SHORT).show()
            return
        }
        val payload = CompanionPayload.toJsonl(items)
        val send = Intent(Intent.ACTION_SEND).apply {
            type = "text/plain"
            putExtra(Intent.EXTRA_TEXT, payload)
            putExtra(Intent.EXTRA_SUBJECT, "YTS companion inbox")
        }
        startActivity(Intent.createChooser(send, getString(R.string.share_payload)))
    }

    private class QueueAdapter(
        private val rows: List<QueueItem>,
        private val resolving: Set<String>,
        private val onRemove: (Int) -> Unit,
        private val onDownload: (Int) -> Unit,
    ) : RecyclerView.Adapter<QueueAdapter.VH>() {
        class VH(val root: android.view.View) : RecyclerView.ViewHolder(root) {
            val title: TextView = root.findViewById(R.id.itemTitle)
            val url: TextView = root.findViewById(R.id.itemUrl)
            val status: TextView = root.findViewById(R.id.itemStatus)
            val download: MaterialButton = root.findViewById(R.id.downloadButton)
            val remove: MaterialButton = root.findViewById(R.id.removeButton)
        }

        override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): VH {
            val view = LayoutInflater.from(parent.context)
                .inflate(R.layout.item_queue, parent, false)
            return VH(view)
        }

        override fun onBindViewHolder(holder: VH, position: Int) {
            val item = rows[position]
            val pending = resolving.any { it.equals(item.url, ignoreCase = true) }
            holder.title.text =
                when {
                    item.title.isNotBlank() -> item.title
                    pending -> holder.root.context.getString(R.string.resolving_title)
                    else -> item.url
                }
            val showUrl = item.title.isNotBlank() || pending
            holder.url.text = item.url
            holder.url.visibility =
                if (showUrl && holder.title.text.toString() != item.url) {
                    android.view.View.VISIBLE
                } else if (pending) {
                    android.view.View.VISIBLE
                } else {
                    android.view.View.GONE
                }

            val ctx = holder.root.context
            val statusText =
                when (item.downloadStatus) {
                    DownloadStatus.IDLE ->
                        if (item.localPath.isNotBlank()) {
                            ctx.getString(R.string.status_done)
                        } else {
                            null
                        }
                    DownloadStatus.QUEUED -> ctx.getString(R.string.status_queued)
                    DownloadStatus.DOWNLOADING ->
                        ctx.getString(R.string.status_downloading, item.progress.toInt())
                    DownloadStatus.DONE ->
                        ctx.getString(R.string.status_done) +
                            if (item.localPath.isNotBlank()) " · ${File(item.localPath).name}" else ""
                    DownloadStatus.ERROR ->
                        ctx.getString(R.string.status_error) +
                            if (item.error.isNotBlank()) ": ${item.error}" else ""
                }
            if (statusText.isNullOrBlank()) {
                holder.status.visibility = android.view.View.GONE
            } else {
                holder.status.visibility = android.view.View.VISIBLE
                holder.status.text = statusText
            }

            val busy =
                item.downloadStatus == DownloadStatus.DOWNLOADING ||
                    item.downloadStatus == DownloadStatus.QUEUED
            holder.download.isEnabled = !busy
            holder.download.setOnClickListener {
                val pos = holder.bindingAdapterPosition
                if (pos != RecyclerView.NO_POSITION) onDownload(pos)
            }
            holder.remove.setOnClickListener {
                val pos = holder.bindingAdapterPosition
                if (pos != RecyclerView.NO_POSITION) onRemove(pos)
            }
        }

        override fun getItemCount(): Int = rows.size
    }

    companion object {
        const val ACTION_EXPORT_DOWNLOADS = "dev.voxhash.ytscompanion.action.EXPORT_DOWNLOADS"
        const val EXTRA_EXPORT_DOWNLOADS = "yts_export_downloads"
        const val ACTION_DOWNLOAD_QUEUE = "dev.voxhash.ytscompanion.action.DOWNLOAD_QUEUE"
        const val EXTRA_DOWNLOAD_QUEUE = "yts_download_queue"
    }
}
