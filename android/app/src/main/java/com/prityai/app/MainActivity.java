package com.prityai.app;

import android.Manifest;
import android.annotation.SuppressLint;
import android.app.Activity;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.view.Gravity;
import android.view.Menu;
import android.view.MenuItem;
import android.view.ViewGroup;
import android.webkit.ConsoleMessage;
import android.webkit.PermissionRequest;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.Toast;

/** Native Android container for the Prity AI FastAPI web client. */
public class MainActivity extends Activity {
    private static final int PICK_FILE = 20;
    private static final int RECORD_AUDIO = 21;
    private WebView webView;
    private ValueCallback<Uri[]> filePickerCallback;
    private SharedPreferences preferences;

    @SuppressLint("SetJavaScriptEnabled")
    @Override public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        preferences = getSharedPreferences("prity", MODE_PRIVATE);
        webView = new WebView(this);
        webView.setBackgroundColor(Color.rgb(243, 248, 255));
        setContentView(webView, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));

        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(false);
        settings.setMediaPlaybackRequiresUserGesture(false);
        webView.setWebViewClient(new WebViewClient());
        webView.setWebChromeClient(new WebChromeClient() {
            @Override public boolean onShowFileChooser(WebView view, ValueCallback<Uri[]> callback,
                    FileChooserParams params) {
                if (filePickerCallback != null) filePickerCallback.onReceiveValue(null);
                filePickerCallback = callback;
                Intent intent = params.createIntent();
                try { startActivityForResult(intent, PICK_FILE); }
                catch (Exception error) { filePickerCallback = null; Toast.makeText(MainActivity.this,
                        "No file picker is available", Toast.LENGTH_SHORT).show(); }
                return true;
            }
            @Override public void onPermissionRequest(PermissionRequest request) {
                if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.M
                        && checkSelfPermission(Manifest.permission.RECORD_AUDIO)
                        != PackageManager.PERMISSION_GRANTED) {
                    requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO}, RECORD_AUDIO);
                } else request.grant(request.getResources());
            }
            @Override public boolean onConsoleMessage(ConsoleMessage message) {
                return true;
            }
        });
        loadAssistant();
    }

    private String serverUrl() {
        return preferences.getString("server_url", "http://10.0.2.2:8000").replaceAll("/+$", "");
    }

    private void loadAssistant() {
        webView.loadUrl(serverUrl() + "/");
    }

    @Override public boolean onCreateOptionsMenu(Menu menu) {
        menu.add("Server").setShowAsAction(MenuItem.SHOW_AS_ACTION_NEVER);
        menu.add("Reload").setShowAsAction(MenuItem.SHOW_AS_ACTION_NEVER);
        return true;
    }

    @Override public boolean onOptionsItemSelected(MenuItem item) {
        if ("Reload".contentEquals(item.getTitle())) { loadAssistant(); return true; }
        if ("Server".contentEquals(item.getTitle())) { showServerEditor(); return true; }
        return super.onOptionsItemSelected(item);
    }

    private void showServerEditor() {
        final EditText input = new EditText(this);
        input.setSingleLine(true);
        input.setText(serverUrl());
        input.setSelectAllOnFocus(true);
        int padding = (int) (24 * getResources().getDisplayMetrics().density);
        FrameLayout holder = new FrameLayout(this);
        holder.setPadding(padding, 0, padding, 0);
        holder.addView(input);
        new android.app.AlertDialog.Builder(this)
                .setTitle("Prity AI server")
                .setMessage("For the Android emulator use http://10.0.2.2:8000. For a phone, enter your computer's LAN address, e.g. http://192.168.1.10:8000.")
                .setView(holder)
                .setPositiveButton("Connect", (dialog, which) -> {
                    String url = input.getText().toString().trim();
                    if (!url.startsWith("http://") && !url.startsWith("https://")) {
                        Toast.makeText(this, "Enter an http:// or https:// address", Toast.LENGTH_LONG).show();
                        return;
                    }
                    preferences.edit().putString("server_url", url).apply();
                    loadAssistant();
                })
                .setNegativeButton("Cancel", null)
                .show();
    }

    @Override protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == PICK_FILE && filePickerCallback != null) {
            filePickerCallback.onReceiveValue(WebChromeClient.FileChooserParams.parseResult(resultCode, data));
            filePickerCallback = null;
        }
    }

    @Override public void onBackPressed() {
        if (webView.canGoBack()) webView.goBack(); else super.onBackPressed();
    }
}
