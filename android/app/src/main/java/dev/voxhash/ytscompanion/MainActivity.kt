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

open class MainActivity : AppCompatActivity() {
    private lateinit var store: QueueStore
    private lateinit var urlInput: TextInputEditText
    private lateinit var emptyLabel: TextView
    private lateinit var exportFolderLabel: TextView
    private lateinit var adapter: QueueAdapter
    private val urls = mutableListOf<String>()

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
        urls.clear()
        urls.addAll(store.load())

        urlInput = findViewById(R.id.urlInput)
        emptyLabel = findViewById(R.id.emptyLabel)
        exportFolderLabel = findViewById(R.id.exportFolderLabel)
        val queueList = findViewById<RecyclerView>(R.id.queueList)

        adapter = QueueAdapter(urls) { index ->
            urls.removeAt(index)
            persistAndRefresh()
        }
        queueList.layoutManager = LinearLayoutManager(this)
        queueList.adapter = adapter

        findViewById<MaterialButton>(R.id.addButton).setOnClickListener { addFromInput() }
        findViewById<MaterialButton>(R.id.clearButton).setOnClickListener {
            urls.clear()
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

        refreshExportFolderLabel()
        persistAndRefresh()
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
        }
        if (intent.getBooleanExtra(EXTRA_EXPORT_DOWNLOADS, false)) {
            exportToDownloads()
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
        if (urls.any { it.equals(url, ignoreCase = true) }) {
            Toast.makeText(this, R.string.added, Toast.LENGTH_SHORT).show()
            return
        }
        urls.add(0, url)
        persistAndRefresh()
        Toast.makeText(this, R.string.added, Toast.LENGTH_SHORT).show()
    }

    private fun persistAndRefresh() {
        store.save(urls)
        adapter.notifyDataSetChanged()
        emptyLabel.visibility = if (urls.isEmpty()) android.view.View.VISIBLE else android.view.View.GONE
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
        if (urls.isEmpty()) {
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
                    writer.write(CompanionPayload.toJsonDocument(urls))
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
        if (urls.isEmpty()) {
            Toast.makeText(this, R.string.empty_queue, Toast.LENGTH_SHORT).show()
            return
        }
        val name = CompanionPayload.suggestedFileName()
        val body = CompanionPayload.toJsonDocument(urls)
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
        if (urls.isEmpty()) {
            Toast.makeText(this, R.string.empty_queue, Toast.LENGTH_SHORT).show()
            return
        }
        val payload = CompanionPayload.toJsonl(urls)
        val send = Intent(Intent.ACTION_SEND).apply {
            type = "text/plain"
            putExtra(Intent.EXTRA_TEXT, payload)
            putExtra(Intent.EXTRA_SUBJECT, "YTS companion inbox")
        }
        startActivity(Intent.createChooser(send, getString(R.string.share_payload)))
    }

    private class QueueAdapter(
        private val items: List<String>,
        private val onRemove: (Int) -> Unit,
    ) : RecyclerView.Adapter<QueueAdapter.VH>() {
        class VH(val root: android.view.View) : RecyclerView.ViewHolder(root) {
            val url: TextView = root.findViewById(R.id.itemUrl)
            val remove: MaterialButton = root.findViewById(R.id.removeButton)
        }

        override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): VH {
            val view = LayoutInflater.from(parent.context)
                .inflate(R.layout.item_queue, parent, false)
            return VH(view)
        }

        override fun onBindViewHolder(holder: VH, position: Int) {
            holder.url.text = items[position]
            holder.remove.setOnClickListener {
                val pos = holder.bindingAdapterPosition
                if (pos != RecyclerView.NO_POSITION) onRemove(pos)
            }
        }

        override fun getItemCount(): Int = items.size
    }

    companion object {
        const val ACTION_EXPORT_DOWNLOADS = "dev.voxhash.ytscompanion.action.EXPORT_DOWNLOADS"
        const val EXTRA_EXPORT_DOWNLOADS = "yts_export_downloads"
    }
}
