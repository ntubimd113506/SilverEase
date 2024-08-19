#include <Arduino.h>
#include <ArduinoJson.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <HardwareSerial.h>
#include <TinyGPS++.h>

#define BTN 12
#define BUZZ 13

const char root_ca[] PROGMEM = R"=====(
-----BEGIN CERTIFICATE-----
MIIDfzCCAmegAwIBAgIUEFxp3W0ar2M3XpfrytLO6AVpd1owDQYJKoZIhvcNAQEL
BQAwTzELMAkGA1UEBhMCVFcxEzARBgNVBAoMClNpbHZlckVhc2UxCzAJBgNVBAsM
AklUMR4wHAYDVQQDDBVzaWx2ZXJlYXNlbnR1Yi5lZHUudHcwHhcNMjQwNTI2MTMz
MzE5WhcNMjUwNTI2MTMzMzE5WjBPMQswCQYDVQQGEwJUVzETMBEGA1UECgwKU2ls
dmVyRWFzZTELMAkGA1UECwwCSVQxHjAcBgNVBAMMFXNpbHZlcmVhc2VudHViLmVk
dS50dzCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBALW23eikbFCvaO1r
eJS49nc9glDUm3LlZTqzBC6KzH3c2Ul2J96lm8b9voGPWxKqy9E/6nvdsIvgoTPP
Oc8htq3Syqw5A1+dkOJrTYfb3IUXdXiQNXhoqodVBYGqky3IvLtJfBw5MJT0vOTa
C3bEZ5tYnDxNXJE5gLh+yGgSjqSwWaA6aYjriqIDdiyfjDfqeUpiUWbm0xtSc+67
CaPRKdOfPJBiuDh/9f5Qj9vpp3R7G0SJXUKT9dlz6Cc4Hua9B+vCl2rnmtZckQh1
FK9z4nOUouYm2W8BJUMKH+4pQ4PaFAEYGjSfBYjKXPlEwCpjSjuAkPLzj443p+Hq
DbenL70CAwEAAaNTMFEwHQYDVR0OBBYEFF16jW5UcMDfoqQbUttqCEBRN/5yMB8G
A1UdIwQYMBaAFF16jW5UcMDfoqQbUttqCEBRN/5yMA8GA1UdEwEB/wQFMAMBAf8w
DQYJKoZIhvcNAQELBQADggEBACVMOJY9KITwKQ2BhTl+ZhckVK73mUBlr6qu1GvV
f40JgOnvaVHdsV50U+LUv/x23iwXyYO0xBl7kSfj5aDhD6JddyhfRwi+BUGC8rS+
yZtO8CETpFj3N6EK7xndvVtuEJjPxCESpKLseH1xBHEec2ctQ7W8wYl9ek9cgJef
ItyeKUBgssI5r7/o31WhgV0oKSaYpvCPV7A7JyhheBusXl9dvr9/ZTtJ2gGBCzu2
qGU9T1QKgBa16C9EcDfDHjQX25yKl7tKX6ZhQ5sNYbPLrVtTMVKgk5gKljihcYCm
IAmOl2Oac/vPXfrdLaSrZenLklC/yWLbGPFCDTztAt83aKs=
-----END CERTIFICATE-----
)=====";

const char *wifi_ssid = "寧";
const char *wifi_pass = "20021212";
const char *server = "silverease.ntub.edu.tw";
const int mqtt_port = 8883;
const char *caCert = root_ca;

bool flag = false;
bool btn_flag = false;

WiFiClientSecure espClient;
PubSubClient mqtt(espClient);

TinyGPSPlus gps;

String latitude = "";
String longitude = "";
unsigned long lastCheckTime = 0;
unsigned long lastSendTime = 0;
bool gpsInitialized = false;
bool wifiConnected = false;
bool mqttConnected = false;

void callback(char *topic, byte *payload, unsigned int length) {
  Serial.print("收到訊息：");
  String message = "";
  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
    Serial.print((char)payload[i]);
  }
  Serial.println();
  Serial.println(message);
  if (String(topic) == "ESP32/got") {
    Serial.println("收到ESP32訊息");
    if (message == "OK") {
      int count = 0;
      while (count < 3) {
        Serial.println("我叫你叫");
        digitalWrite(BUZZ, HIGH);
        delay(1000);
        digitalWrite(BUZZ, LOW);
        delay(1000);
        count++;
      }
    }
  } 
  
  if (String(topic) == "/nowGPS") { // /nowGPS
    Serial.println("取得GPS");
    if (gps.location.isValid()) {
      String lat = String(gps.location.lat(), 6);
      String lon = String(gps.location.lng(), 6);
      String google_maps_url = "https://www.google.com/maps/search/?api=1&query=" + lat + "," + lon;
      mqtt.publish("/upGPS", google_maps_url.c_str());
      Serial.println("發送GPS數據：" + google_maps_url);
    } else {
      mqtt.publish("/upGPS", "Invalid GPS Data"); // /upGPS
      Serial.println("GPS數據無效");
    }
  }
  
  if (String(topic) == "ESP32/help") {
    Serial.println("收到ESP32求救訊息");
    delay(5000);
    flag = false;
  }
  Serial.println();
}

void connectToWiFi() {
  WiFi.begin(wifi_ssid, wifi_pass);
  Serial.println("");
  Serial.print("Connecting to ");
  Serial.println(wifi_ssid);

  unsigned long startTime = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - startTime < 10000) {
    delay(500);
    Serial.print(".");
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("");
    Serial.println("WiFi connected!");
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
    wifiConnected = true;

  } else {
    Serial.println("");
    Serial.println("Failed to connect to WiFi!");
    wifiConnected = false;
  }
}

void connectToMQTT() {
  mqtt.setServer(server, mqtt_port);
  mqtt.setCallback(callback);
  while (!mqtt.connected()) {
    Serial.print("Connecting to MQTT...");
    if (mqtt.connect("ESP32Client")) {
      Serial.println("connected");
      mqtt.subscribe("ESP32/#");
      mqtt.subscribe("/nowGPS"); // 訂閱 /nowGPS 主題
      mqtt.subscribe("/SOSgps"); // 訂閱 /SOSgps 主題

    } else {
      Serial.print("failed with state ");
      Serial.print(mqtt.state());
      delay(2000);
    }
  }
}

void setup() {
  pinMode(BUZZ, OUTPUT);
  pinMode(BTN, INPUT);
  Serial.begin(9600); // ESP32-CAM
  connectToWiFi();
  while (!wifiConnected) {
    Serial.println("等待WiFi連接...");
    delay(1000);
    connectToWiFi();
  }
  espClient.setCACert(caCert);
  connectToMQTT();
  Serial.println("Initializing GPS module...");
  xTaskCreate(mainTask, "Main Task", 4096, NULL, 1, NULL); // 創建一個任務來處理按鈕
}

void loop() {
  unsigned long currentTime = millis();

  if (!gpsInitialized) {
    if (currentTime - lastCheckTime >= 15000) { // 等待 15 秒
      gpsInitialized = true;
      Serial.println("GPS initialization done. Starting to check GPS status...");
    }
  } else {
    if (currentTime - lastCheckTime >= 15000) {
      lastCheckTime = currentTime;
      Serial.println("Checking GPS status...");
    }

    if (Serial.available() > 0) {
      gps.encode(Serial.read());
    }

    if (currentTime - lastSendTime >= 60000) { // 60000 毫秒 = 1分鐘
      lastSendTime = currentTime;
      Serial.println("1min");
      if (gps.location.isValid()) {
        latitude = String(gps.location.lat(), 6);
        longitude = String(gps.location.lng(), 6);
        sendGPSData(latitude, longitude);
      }
    }

    if (!mqtt.connected()) {
      Serial.println("重新連線MQTT");
      connectToMQTT();
    }
    mqtt.loop();

    if (WiFi.status() != WL_CONNECTED) {
      Serial.println("重新連線WIFI");
      connectToWiFi();
    }
  }
}

void sendGPSData(String lat, String lon) {
  String googleMapsUrl = "https://www.google.com/maps/search/?api=1&query=" + lat + "," + lon;
  mqtt.publish("ESP32/gps", googleMapsUrl.c_str());
  Serial.println("GPS data sent: " + googleMapsUrl);
}

void SOSGPSData(String lat, String lon) {
  String googleMapsUrl = "https://www.google.com/maps/search/?api=1&query=" + lat + "," + lon;
  mqtt.publish("/SOSgps", googleMapsUrl.c_str());  // /SOSGPS
  Serial.println("SOS位置已發送");
  Serial.println("GPS data sent: " + googleMapsUrl);
}

void mainTask(void *parameter)
{
  while (1)
  {
    if (WiFi.status() == WL_CONNECTED){
      Serial.print("FLAG: ");
      bool flag = digitalRead(BTN) && !btn_flag;
      Serial.println(flag);
      if (flag)
      {
        btn_flag = true;
        digitalWrite(BUZZ, HIGH);
        if (gps.location.isValid()) {
          SOSGPSData(String(gps.location.lat(), 6), String(gps.location.lng(), 6));
        } else {
          Serial.println("無效的GPS數據，無法發送SOS");
        }
        digitalWrite(BUZZ, LOW);
        vTaskDelay(5000 / portTICK_PERIOD_MS);
        btn_flag = false;
      }
    }
    else
    {
      Serial.println("重新連接");
      connectToWiFi();
      vTaskDelay(5000 / portTICK_PERIOD_MS);
    }
    vTaskDelay(500 / portTICK_PERIOD_MS);
  }
}