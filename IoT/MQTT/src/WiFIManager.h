#ifndef WIFI_MANAGER_H
#define WIFI_MANAGER_H

#include <Arduino.h>
#include <Preferences.h>
#include <ArduinoJson.h>
#include <WiFi.h>
#include <WiFiMulti.h>

class WiFiManager {
public:
    WiFiManager();
    bool begin();
    bool addWiFi(const char* ssid, const char* password);
    bool removeWiFi(const char* ssid);
    void listWiFi();
    bool setWiFiPwd(const char* ssid, String& password);
    int getWiFiCount();
    void setupMulti(WiFiMulti& wifiMulti);
    bool connectMulti(WiFiMulti& wifiMulti, unsigned long timeout = 10000);

private:
    Preferences preferences;
    bool loadWiFi(JsonDocument& doc);
    bool saveWiFi(const JsonDocument& doc);
    static const char* PREF_NAME;
    static const char* WIFI_KEY;
};

#endif // WIFI_MANAGER_H