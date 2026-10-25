package com.hacktx.mothertongue.hearth

import android.Manifest
import android.annotation.SuppressLint
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Color
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.KeyEvent
import android.view.View
import android.view.WindowInsets
import android.view.WindowInsetsController
import android.view.WindowManager
import android.webkit.PermissionRequest
import android.webkit.WebChromeClient
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient

class MainActivity : Activity() {

    private lateinit var webView: WebView
    private val handler = Handler(Looper.getMainLooper())
    private var pendingMicRequest: PermissionRequest? = null
    private val retry = Runnable { webView.loadUrl(hearthUrl()) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)

        webView = WebView(this)
        webView.setBackgroundColor(Color.parseColor("#f7f3ec"))
        setContentView(webView)
        configureWebView()

        saveUrlFromIntent(intent)
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(arrayOf(Manifest.permission.RECORD_AUDIO), REQ_MIC)
        }
        webView.loadUrl(hearthUrl())
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        if (saveUrlFromIntent(intent)) {
            handler.removeCallbacks(retry)
            webView.loadUrl(hearthUrl())
        }
    }

    // Intent extra "url" wins and is persisted; then saved pref; then the build default.
    private fun saveUrlFromIntent(intent: Intent?): Boolean {
        val url = intent?.getStringExtra("url")?.trim().orEmpty()
        if (url.isEmpty()) return false
        getSharedPreferences(PREFS, MODE_PRIVATE).edit().putString(KEY_URL, url).apply()
        return true
    }

    private fun hearthUrl(): String =
        getSharedPreferences(PREFS, MODE_PRIVATE).getString(KEY_URL, null) ?: BuildConfig.HEARTH_URL

    @SuppressLint("SetJavaScriptEnabled")
    private fun configureWebView() {
        val s = webView.settings
        s.javaScriptEnabled = true
        s.domStorageEnabled = true
        s.mediaPlaybackRequiresUserGesture = false
        s.mixedContentMode = WebSettings.MIXED_CONTENT_NEVER_ALLOW

        webView.webViewClient = object : WebViewClient() {
            override fun onReceivedError(view: WebView, request: WebResourceRequest, error: WebResourceError) {
                if (request.isForMainFrame) showOffline()
            }

            override fun onPageFinished(view: WebView, url: String?) {
                if (url != null && !url.startsWith(OFFLINE_BASE)) handler.removeCallbacks(retry)
            }
        }

        webView.webChromeClient = object : WebChromeClient() {
            override fun onPermissionRequest(request: PermissionRequest) {
                runOnUiThread {
                    if (!request.resources.contains(PermissionRequest.RESOURCE_AUDIO_CAPTURE)) {
                        request.deny()
                    } else if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED) {
                        request.grant(arrayOf(PermissionRequest.RESOURCE_AUDIO_CAPTURE))
                    } else {
                        pendingMicRequest = request
                        requestPermissions(arrayOf(Manifest.permission.RECORD_AUDIO), REQ_MIC)
                    }
                }
            }
        }
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode != REQ_MIC) return
        val req = pendingMicRequest ?: return
        pendingMicRequest = null
        if (grantResults.firstOrNull() == PackageManager.PERMISSION_GRANTED) {
            req.grant(arrayOf(PermissionRequest.RESOURCE_AUDIO_CAPTURE))
        } else {
            req.deny()
        }
    }

    private fun showOffline() {
        webView.loadDataWithBaseURL(OFFLINE_BASE, OFFLINE_HTML, "text/html", "utf-8", null)
        handler.removeCallbacks(retry)
        handler.postDelayed(retry, RETRY_MS)
    }

    override fun onResume() {
        super.onResume()
        hideSystemBars()
    }

    override fun onPause() {
        super.onPause()
        handler.removeCallbacks(retry)
    }

    override fun onWindowFocusChanged(hasFocus: Boolean) {
        super.onWindowFocusChanged(hasFocus)
        if (hasFocus) hideSystemBars()
    }

    @Suppress("DEPRECATION")
    private fun hideSystemBars() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            window.setDecorFitsSystemWindows(false)
            window.insetsController?.let {
                it.hide(WindowInsets.Type.statusBars() or WindowInsets.Type.navigationBars())
                it.systemBarsBehavior = WindowInsetsController.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
            }
        } else {
            window.decorView.systemUiVisibility = (View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
                or View.SYSTEM_UI_FLAG_FULLSCREEN
                or View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                or View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                or View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                or View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION)
        }
    }

    // Shutter remotes send Enter, Space, DPAD_CENTER or volume keys. All become an
    // "Enter" KeyboardEvent in the page. Volume keys never reach the system mixer.
    override fun dispatchKeyEvent(event: KeyEvent): Boolean {
        when (event.keyCode) {
            KeyEvent.KEYCODE_BACK -> return true
            KeyEvent.KEYCODE_ENTER, KeyEvent.KEYCODE_NUMPAD_ENTER, KeyEvent.KEYCODE_SPACE,
            KeyEvent.KEYCODE_DPAD_CENTER, KeyEvent.KEYCODE_VOLUME_UP, KeyEvent.KEYCODE_VOLUME_DOWN -> {
                if (event.action == KeyEvent.ACTION_DOWN && event.repeatCount == 0) sendEnter()
                return true
            }
        }
        return super.dispatchKeyEvent(event)
    }

    private fun sendEnter() {
        webView.evaluateJavascript(ENTER_JS, null)
    }

    @Deprecated("Kiosk: back does nothing")
    @Suppress("DEPRECATION")
    override fun onBackPressed() {
        // Intentionally empty.
    }

    override fun onDestroy() {
        handler.removeCallbacksAndMessages(null)
        webView.destroy()
        super.onDestroy()
    }

    companion object {
        private const val PREFS = "hearth"
        private const val KEY_URL = "url"
        private const val REQ_MIC = 1
        private const val RETRY_MS = 10_000L
        private const val OFFLINE_BASE = "https://hearth.offline/"

        private const val ENTER_JS = "(function(){" +
            "var o={key:'Enter',code:'Enter',keyCode:13,which:13,bubbles:true,cancelable:true};" +
            "document.dispatchEvent(new KeyboardEvent('keydown',o));" +
            "document.dispatchEvent(new KeyboardEvent('keyup',o));" +
            "})();"

        private const val OFFLINE_HTML = """<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
html,body{margin:0;height:100%;background:#f7f3ec;color:#121212;}
body{display:flex;align-items:center;justify-content:center;
font-family:"Helvetica Neue",Helvetica,Arial,sans-serif;font-size:28px;letter-spacing:-0.01em;}
</style></head>
<body><p>Sin conexion. Reintentando...</p></body></html>"""
    }
}
