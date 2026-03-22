#pragma once

// Replace these placeholders with your current hackathon network and backend values.
static const char* WIFI_SSID = "kphone";
static const char* WIFI_PASSWORD = "kriti1111";

// Backend host information. Use your laptop's LAN IP while developing.
static const char* API_HOST = "172.20.10.11";
static const uint16_t API_PORT = 8000;
static const bool API_USE_TLS = false;

// Existing backend user/device IDs. These must already exist in the API store.
static const char* USER_ID = "user_90a7212411a3";
static const char* DEVICE_ID = "device_7514a16621e6";
static const char* FIRMWARE_VERSION = "wifi-upload-v1";

// Update these pin values to match your current XIAO + recorder wiring.
static const int BUTTON_PIN = D1;
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
