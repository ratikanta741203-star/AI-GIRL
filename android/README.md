# Prity AI for Android

This is a native Android WebView project for the existing FastAPI application.

## Build

1. Open this `android` folder in Android Studio.
2. Let Android Studio install the Android SDK components if prompted.
3. Build **app** or run it on an Android device/emulator.

The default endpoint is `http://10.0.2.2:8000`, which reaches a FastAPI server
running on the development machine from the Android emulator. Start the backend
before launching the app:

```powershell
uvicorn app:app --host 0.0.0.0 --port 8000
```

For a physical phone, use the app menu's **Server** action to set your computer's
LAN URL (for example `http://192.168.1.10:8000`). Ensure the phone and computer
are on the same network and the firewall permits port 8000.
