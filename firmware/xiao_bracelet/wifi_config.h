#pragma once

// Replace these placeholders with your current hackathon network and backend values.
static const char* WIFI_SSID = "eduroam";
static const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// Backend host information. Use your laptop's LAN IP while developing.
static const char* API_HOST = "192.168.1.10";
static const uint16_t API_PORT = 8000;
static const bool API_USE_TLS = false;

// Existing backend user/device IDs. These must already exist in the API store.
static const char* USER_ID = "user_replace_me";
static const char* DEVICE_ID = "device_replace_me";
static const char* FIRMWARE_VERSION = "wifi-upload-v1";

// Update these pin values to match your current XIAO + recorder wiring.
static const int BUTTON_PIN = 2;
static const int SD_CS_PIN = 21;

// Transport rollout controls.
static const bool ENABLE_TEST_POST = true;
static const bool ENABLE_REAL_UPLOAD = true;
static const bool DELETE_FILE_AFTER_UPLOAD = false;

// Set to false after wiring your proven local recorder into the hook functions.
static const bool BRACELET_FAKE_RECORDER = true;

// Fake WAV generation uses this format. Match your real recorder if possible.
static const uint32_t WAV_SAMPLE_RATE = 16000;
static const uint16_t WAV_BITS_PER_SAMPLE = 16;
static const uint16_t WAV_CHANNEL_COUNT = 1;
