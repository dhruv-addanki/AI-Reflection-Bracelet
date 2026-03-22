#include <Arduino.h>
#include <HTTPClient.h>
#include <SD.h>
#include <SPI.h>
#include <WiFi.h>
#include <WiFiClient.h>
#include <time.h>

#include "wifi_config.h"

enum BraceletState {
  STATE_BOOTING,
  STATE_WIFI_CONNECTING,
  STATE_IDLE,
  STATE_RECORDING,
  STATE_STOPPING,
  STATE_UPLOAD_PENDING,
  STATE_UPLOAD_SUCCESS,
  STATE_UPLOAD_FAILED,
};

struct SessionContext {
  String sessionId;
  String fileName;
  String filePath;
  uint32_t startedAtMs;
  uint32_t durationMs;
  uint32_t timestampMs;
  uint8_t uploadAttempts;
};

BraceletState braceletState = STATE_BOOTING;
SessionContext currentSession;

bool storageReady = false;
bool wifiReady = false;
bool clockSynced = false;
bool lastButtonReading = HIGH;
bool buttonState = HIGH;
unsigned long lastDebounceAtMs = 0;
unsigned long lastWiFiAttemptAtMs = 0;
const unsigned long kDebounceDelayMs = 40;
const unsigned long kReconnectIntervalMs = 10000;

void connectWiFi(bool force);
void maintainWiFi();
void syncClock();
void handleButton();
void transitionToIdle();
void startRecordingSession();
void stopRecordingSession();
void serviceRecorderLoop();
bool initializeStorage();
bool beginRecorderForSession(const SessionContext& session);
void serviceRealRecorder();
bool stopRecorderForSession(const SessionContext& session);
bool beginRealRecorder(const SessionContext& session);
bool stopRealRecorder(const SessionContext& session);
bool writeFakeWavFile(const SessionContext& session);
bool postConnectivityTest(const SessionContext& session);
bool uploadRecordedWav(const SessionContext& session);
String currentIsoTimestampUtc();
String buildApiUrl(const char* path);
String buildSessionId();
String readHttpResponse(WiFiClient& client);
size_t multipartFieldLength(const String& boundary, const String& name, const String& value);
void writeMultipartField(WiFiClient& client, const String& boundary, const String& name, const String& value);
size_t multipartFileHeaderLength(const String& boundary, const String& fieldName, const String& fileName, const String& contentType);
void writeMultipartFileHeader(WiFiClient& client, const String& boundary, const String& fieldName, const String& fileName, const String& contentType);
bool parseBaseUrl(String& scheme, String& host, uint16_t& port);
void writeLe16(File& file, uint16_t value);
void writeLe32(File& file, uint32_t value);

void setup() {
  Serial.begin(115200);
  delay(250);

  pinMode(BUTTON_PIN, INPUT_PULLUP);
  braceletState = STATE_WIFI_CONNECTING;

  Serial.println();
  Serial.println("=== XIAO Bracelet Wi-Fi Upload ===");
  Serial.printf("Firmware: %s\n", FIRMWARE_VERSION);

  storageReady = initializeStorage();
  connectWiFi(true);
}

void loop() {
  maintainWiFi();
  handleButton();

  if (braceletState == STATE_RECORDING) {
    serviceRecorderLoop();
  }

  if (braceletState == STATE_UPLOAD_PENDING) {
    bool testOk = true;
    bool uploadOk = true;

    if (ENABLE_TEST_POST) {
      testOk = postConnectivityTest(currentSession);
    }

    if (testOk && ENABLE_REAL_UPLOAD) {
      uploadOk = uploadRecordedWav(currentSession);
    }

    if (testOk && uploadOk) {
      braceletState = STATE_UPLOAD_SUCCESS;
      Serial.printf("[UPLOAD] success for %s\n", currentSession.fileName.c_str());
      if (DELETE_FILE_AFTER_UPLOAD && SD.exists(currentSession.filePath)) {
        SD.remove(currentSession.filePath);
        Serial.printf("[UPLOAD] deleted local file %s\n", currentSession.filePath.c_str());
      }
    } else {
      braceletState = STATE_UPLOAD_FAILED;
      Serial.printf("[UPLOAD] failed for %s. File preserved on SD.\n", currentSession.fileName.c_str());
    }

    transitionToIdle();
  }
}

void connectWiFi(bool force) {
  if (!force && WiFi.status() == WL_CONNECTED) {
    wifiReady = true;
    return;
  }

  unsigned long now = millis();
  if (!force && now - lastWiFiAttemptAtMs < kReconnectIntervalMs) {
    return;
  }
  lastWiFiAttemptAtMs = now;

  Serial.printf("[WIFI] connecting to %s\n", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  unsigned long started = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - started < 12000) {
    delay(250);
    Serial.print(".");
  }
  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    wifiReady = true;
    Serial.println("[WIFI] connected");
    Serial.print("[WIFI] IP: ");
    Serial.println(WiFi.localIP());
    syncClock();
  } else {
    wifiReady = false;
    Serial.printf("[WIFI] failed, status=%d\n", WiFi.status());
  }
}

void maintainWiFi() {
  if (WiFi.status() == WL_CONNECTED) {
    wifiReady = true;
    return;
  }
  wifiReady = false;
  connectWiFi(false);
}

void syncClock() {
  if (!wifiReady) {
    return;
  }

  configTime(0, 0, "pool.ntp.org", "time.nist.gov", "time.google.com");
  time_t now = time(nullptr);
  unsigned long started = millis();
  while (now < 1700000000 && millis() - started < 8000) {
    delay(200);
    now = time(nullptr);
  }

  clockSynced = now >= 1700000000;
  if (clockSynced) {
    Serial.printf("[CLOCK] synced unix=%lu\n", static_cast<unsigned long>(now));
  } else {
    Serial.println("[CLOCK] sync failed, uploads will use a fallback timestamp");
  }
}

void handleButton() {
  bool reading = digitalRead(BUTTON_PIN);
  if (reading != lastButtonReading) {
    lastDebounceAtMs = millis();
  }

  if (millis() - lastDebounceAtMs > kDebounceDelayMs) {
    if (reading != buttonState) {
      buttonState = reading;
      if (buttonState == LOW) {
        if (braceletState == STATE_IDLE) {
          startRecordingSession();
        } else if (braceletState == STATE_RECORDING) {
          stopRecordingSession();
        }
      }
    }
  }

  lastButtonReading = reading;
}

void transitionToIdle() {
  braceletState = STATE_IDLE;
  Serial.println("[STATE] idle");
}

void startRecordingSession() {
  if (!storageReady) {
    Serial.println("[RECORDER] SD storage unavailable, cannot start recording");
    return;
  }
  if (braceletState == STATE_RECORDING) {
    return;
  }

  currentSession = {};
  currentSession.sessionId = buildSessionId();
  currentSession.fileName = currentSession.sessionId + ".wav";
  currentSession.filePath = "/" + currentSession.fileName;
  currentSession.startedAtMs = millis();
  currentSession.timestampMs = millis();
  currentSession.uploadAttempts = 0;

  if (!beginRecorderForSession(currentSession)) {
    Serial.println("[RECORDER] failed to start recording session");
    braceletState = STATE_IDLE;
    return;
  }

  braceletState = STATE_RECORDING;
  Serial.printf("[RECORDER] started %s\n", currentSession.filePath.c_str());
}

void stopRecordingSession() {
  if (braceletState != STATE_RECORDING) {
    return;
  }

  braceletState = STATE_STOPPING;
  currentSession.durationMs = millis() - currentSession.startedAtMs;
  Serial.printf("[RECORDER] stopping %s after %lu ms\n", currentSession.fileName.c_str(), static_cast<unsigned long>(currentSession.durationMs));

  if (!stopRecorderForSession(currentSession)) {
    Serial.println("[RECORDER] failed to finalize WAV file");
    braceletState = STATE_UPLOAD_FAILED;
    transitionToIdle();
    return;
  }

  braceletState = STATE_UPLOAD_PENDING;
}

void serviceRecorderLoop() {
  if (!BRACELET_FAKE_RECORDER) {
    serviceRealRecorder();
  }
}

bool initializeStorage() {
  if (!SD.begin(SD_CS_PIN)) {
    Serial.printf("[SD] init failed on CS pin %d\n", SD_CS_PIN);
    return false;
  }
  uint64_t cardSizeMb = SD.cardSize() / (1024ULL * 1024ULL);
  Serial.printf("[SD] ready, size=%llu MB\n", cardSizeMb);
  return true;
}

bool beginRecorderForSession(const SessionContext& session) {
  if (BRACELET_FAKE_RECORDER) {
    Serial.printf("[RECORDER] fake mode enabled for %s\n", session.fileName.c_str());
    return true;
  }
  return beginRealRecorder(session);
}

bool stopRecorderForSession(const SessionContext& session) {
  if (BRACELET_FAKE_RECORDER) {
    return writeFakeWavFile(session);
  }
  return stopRealRecorder(session);
}

bool beginRealRecorder(const SessionContext& session) {
  Serial.printf("[RECORDER] TODO wire real begin logic for %s\n", session.fileName.c_str());
  return false;
}

void serviceRealRecorder() {
  // TODO: call your proven capture loop here while STATE_RECORDING is active.
}

bool stopRealRecorder(const SessionContext& session) {
  Serial.printf("[RECORDER] TODO wire real stop/finalize logic for %s\n", session.fileName.c_str());
  return false;
}

bool writeFakeWavFile(const SessionContext& session) {
  File file = SD.open(session.filePath, FILE_WRITE);
  if (!file) {
    Serial.printf("[RECORDER] could not open %s for fake WAV output\n", session.filePath.c_str());
    return false;
  }

  uint32_t sampleCount = max<uint32_t>(WAV_SAMPLE_RATE, (session.durationMs * WAV_SAMPLE_RATE) / 1000);
  uint32_t dataSize = sampleCount * WAV_CHANNEL_COUNT * (WAV_BITS_PER_SAMPLE / 8);
  uint32_t riffSize = 36 + dataSize;
  uint32_t byteRate = WAV_SAMPLE_RATE * WAV_CHANNEL_COUNT * (WAV_BITS_PER_SAMPLE / 8);
  uint16_t blockAlign = WAV_CHANNEL_COUNT * (WAV_BITS_PER_SAMPLE / 8);

  file.seek(0);
  file.write(reinterpret_cast<const uint8_t*>("RIFF"), 4);
  writeLe32(file, riffSize);
  file.write(reinterpret_cast<const uint8_t*>("WAVE"), 4);
  file.write(reinterpret_cast<const uint8_t*>("fmt "), 4);
  writeLe32(file, 16);
  writeLe16(file, 1);
  writeLe16(file, WAV_CHANNEL_COUNT);
  writeLe32(file, WAV_SAMPLE_RATE);
  writeLe32(file, byteRate);
  writeLe16(file, blockAlign);
  writeLe16(file, WAV_BITS_PER_SAMPLE);
  file.write(reinterpret_cast<const uint8_t*>("data"), 4);
  writeLe32(file, dataSize);

  const size_t kChunkBytes = 512;
  uint8_t zeros[kChunkBytes];
  memset(zeros, 0, sizeof(zeros));
  uint32_t written = 0;
  while (written < dataSize) {
    size_t chunk = min<uint32_t>(kChunkBytes, dataSize - written);
    file.write(zeros, chunk);
    written += chunk;
  }
  file.flush();
  file.close();

  Serial.printf("[RECORDER] fake WAV finalized at %s (%lu bytes)\n", session.filePath.c_str(), static_cast<unsigned long>(dataSize + 44));
  return true;
}

bool postConnectivityTest(const SessionContext& session) {
  if (!wifiReady) {
    Serial.println("[TEST] skipped because Wi-Fi is unavailable");
    return false;
  }

  HTTPClient http;
  String url = buildApiUrl("/test-upload");
  String payload =
      "{"
      "\"user_id\":\"" + String(USER_ID) + "\","
      "\"device_id\":\"" + String(DEVICE_ID) + "\","
      "\"session_id\":\"" + session.sessionId + "\","
      "\"filename\":\"" + session.fileName + "\","
      "\"duration_ms\":" + String(session.durationMs) + ","
      "\"timestamp_ms\":" + String(session.timestampMs) + ","
      "\"message\":\"hello from bracelet\""
      "}";

  Serial.printf("[TEST] POST %s\n", url.c_str());
  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  int statusCode = http.POST(payload);
  String response = http.getString();
  http.end();

  Serial.printf("[TEST] status=%d response=%s\n", statusCode, response.c_str());
  return statusCode >= 200 && statusCode < 300;
}

bool uploadRecordedWav(const SessionContext& session) {
  if (!wifiReady) {
    Serial.println("[UPLOAD] skipped because Wi-Fi is unavailable");
    return false;
  }
  if (!SD.exists(session.filePath)) {
    Serial.printf("[UPLOAD] file missing on SD: %s\n", session.filePath.c_str());
    return false;
  }

  String scheme;
  String host;
  uint16_t port = API_PORT;
  if (!parseBaseUrl(scheme, host, port)) {
    Serial.println("[UPLOAD] failed to parse API host configuration");
    return false;
  }

  File file = SD.open(session.filePath, FILE_READ);
  if (!file) {
    Serial.printf("[UPLOAD] could not open %s\n", session.filePath.c_str());
    return false;
  }

  const String boundary = "----xiaoBraceletBoundary";
  const String uploadPath = "/sessions/upload";
  const String timestamp = currentIsoTimestampUtc();
  const String batteryStatus = "";

  size_t contentLength = 0;
  contentLength += multipartFieldLength(boundary, "user_id", String(USER_ID));
  contentLength += multipartFieldLength(boundary, "device_id", String(DEVICE_ID));
  contentLength += multipartFieldLength(boundary, "timestamp", timestamp);
  contentLength += multipartFieldLength(boundary, "source_type", "bracelet");
  if (batteryStatus.length() > 0) {
    contentLength += multipartFieldLength(boundary, "battery_status", batteryStatus);
  }
  contentLength += multipartFileHeaderLength(boundary, "audio_file", session.fileName, "audio/wav");
  contentLength += file.size();
  contentLength += 2;  // CRLF after file body
  contentLength += boundary.length() + 6;  // --boundary--\r\n

  WiFiClient client;
  Serial.printf("[UPLOAD] connecting to %s:%u\n", host.c_str(), port);
  if (!client.connect(host.c_str(), port)) {
    Serial.println("[UPLOAD] TCP connect failed");
    file.close();
    return false;
  }

  client.printf("POST %s HTTP/1.1\r\n", uploadPath.c_str());
  client.printf("Host: %s:%u\r\n", host.c_str(), port);
  client.println("Connection: close");
  client.printf("Content-Type: multipart/form-data; boundary=%s\r\n", boundary.c_str());
  client.printf("Content-Length: %u\r\n", static_cast<unsigned int>(contentLength));
  client.print("\r\n");

  writeMultipartField(client, boundary, "user_id", String(USER_ID));
  writeMultipartField(client, boundary, "device_id", String(DEVICE_ID));
  writeMultipartField(client, boundary, "timestamp", timestamp);
  writeMultipartField(client, boundary, "source_type", "bracelet");
  if (batteryStatus.length() > 0) {
    writeMultipartField(client, boundary, "battery_status", batteryStatus);
  }
  writeMultipartFileHeader(client, boundary, "audio_file", session.fileName, "audio/wav");

  uint8_t buffer[1024];
  while (file.available()) {
    size_t readCount = file.read(buffer, sizeof(buffer));
    if (readCount == 0) {
      break;
    }
    client.write(buffer, readCount);
  }
  file.close();

  client.print("\r\n");
  client.printf("--%s--\r\n", boundary.c_str());

  String response = readHttpResponse(client);
  client.stop();

  bool ok = response.indexOf(" 200 ") >= 0 || response.indexOf(" 201 ") >= 0;
  Serial.printf("[UPLOAD] response=%s\n", response.c_str());
  return ok;
}

String currentIsoTimestampUtc() {
  time_t now = time(nullptr);
  if (clockSynced && now >= 1700000000) {
    struct tm timeInfo;
    gmtime_r(&now, &timeInfo);
    char buffer[32];
    strftime(buffer, sizeof(buffer), "%Y-%m-%dT%H:%M:%SZ", &timeInfo);
    return String(buffer);
  }

  unsigned long fallbackSeconds = millis() / 1000;
  char fallback[32];
  snprintf(fallback, sizeof(fallback), "2026-01-01T00:%02lu:%02luZ", (fallbackSeconds / 60) % 60, fallbackSeconds % 60);
  return String(fallback);
}

String buildApiUrl(const char* path) {
  String url = API_USE_TLS ? "https://" : "http://";
  url += API_HOST;
  url += ":";
  url += String(API_PORT);
  url += path;
  return url;
}

String buildSessionId() {
  return "bracelet_" + String(millis());
}

String readHttpResponse(WiFiClient& client) {
  String response;
  unsigned long started = millis();
  while (client.connected() && millis() - started < 10000) {
    while (client.available()) {
      char c = static_cast<char>(client.read());
      response += c;
      started = millis();
    }
  }
  return response;
}

size_t multipartFieldLength(const String& boundary, const String& name, const String& value) {
  String part = "--" + boundary + "\r\n";
  part += "Content-Disposition: form-data; name=\"" + name + "\"\r\n\r\n";
  part += value + "\r\n";
  return part.length();
}

void writeMultipartField(WiFiClient& client, const String& boundary, const String& name, const String& value) {
  client.print("--");
  client.print(boundary);
  client.print("\r\n");
  client.print("Content-Disposition: form-data; name=\"");
  client.print(name);
  client.print("\"\r\n\r\n");
  client.print(value);
  client.print("\r\n");
}

size_t multipartFileHeaderLength(const String& boundary, const String& fieldName, const String& fileName, const String& contentType) {
  String header = "--" + boundary + "\r\n";
  header += "Content-Disposition: form-data; name=\"" + fieldName + "\"; filename=\"" + fileName + "\"\r\n";
  header += "Content-Type: " + contentType + "\r\n\r\n";
  return header.length();
}

void writeMultipartFileHeader(WiFiClient& client, const String& boundary, const String& fieldName, const String& fileName, const String& contentType) {
  client.print("--");
  client.print(boundary);
  client.print("\r\n");
  client.print("Content-Disposition: form-data; name=\"");
  client.print(fieldName);
  client.print("\"; filename=\"");
  client.print(fileName);
  client.print("\"\r\n");
  client.print("Content-Type: ");
  client.print(contentType);
  client.print("\r\n\r\n");
}

bool parseBaseUrl(String& scheme, String& host, uint16_t& port) {
  scheme = API_USE_TLS ? "https" : "http";
  host = String(API_HOST);
  port = API_PORT;
  return host.length() > 0;
}

void writeLe16(File& file, uint16_t value) {
  uint8_t bytes[2];
  bytes[0] = static_cast<uint8_t>(value & 0xFF);
  bytes[1] = static_cast<uint8_t>((value >> 8) & 0xFF);
  file.write(bytes, sizeof(bytes));
}

void writeLe32(File& file, uint32_t value) {
  uint8_t bytes[4];
  bytes[0] = static_cast<uint8_t>(value & 0xFF);
  bytes[1] = static_cast<uint8_t>((value >> 8) & 0xFF);
  bytes[2] = static_cast<uint8_t>((value >> 16) & 0xFF);
  bytes[3] = static_cast<uint8_t>((value >> 24) & 0xFF);
  file.write(bytes, sizeof(bytes));
}
