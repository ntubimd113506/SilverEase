#include "WiFiManager.h"

const char* WiFiManager::PREF_NAME = "wifiManager";
const char* WiFiManager::WIFI_KEY = "wifiList";

WiFiManager::WiFiManager() {}

bool WiFiManager::begin() {
    return preferences.begin(PREF_NAME, false);
}

bool WiFiManager::addWiFi(const char* ssid, const char* password) {
    DynamicJsonDocument doc(1024);
    loadWiFi(doc);
    
    doc[ssid] = password;
    
    return saveWiFi(doc);
}

bool WiFiManager::removeWiFi(const char* ssid) {
    DynamicJsonDocument doc(1024);
    loadWiFi(doc);
    
    doc.remove(ssid);
    
    return saveWiFi(doc);
}

void WiFiManager::listWiFi() {
    DynamicJsonDocument doc(1024);
    loadWiFi(doc);
    
    Serial.println("Stored WiFi Networks:");
    for (JsonPair kv : doc.as<JsonObject>()) {
        Serial.printf("SSID: %s, Password: %s\n", kv.key().c_str(), kv.value().as<const char*>());
    }
}

bool WiFiManager::setWiFiPwd(const char* ssid, String& password) {
    DynamicJsonDocument doc(1024);
    loadWiFi(doc);
    
    if (doc.containsKey(ssid)) {
        password = doc[ssid].as<String>();
        return true;
    }
    return false;
}

int WiFiManager::getWiFiCount() {
    DynamicJsonDocument doc(1024);
    loadWiFi(doc);
    return doc.size();
}

void WiFiManager::setupMulti(WiFiMulti& wifiMulti) {
    DynamicJsonDocument doc(1024);
    loadWiFi(doc);
    
    for (JsonPair kv : doc.as<JsonObject>()) {
        const char* ssid = kv.key().c_str();
        const char* password = kv.value().as<const char*>();
        wifiMulti.addAP(ssid, password);
    }
}

bool WiFiManager::connectMulti(WiFiMulti& wifiMulti, unsigned long timeout) {
    Serial.println("Connecting to WiFi...");
    unsigned long startAttemptTime = millis();

    while (WiFi.status() != WL_CONNECTED && millis() - startAttemptTime < timeout) {
        if (wifiMulti.run() == WL_CONNECTED) {
            Serial.println("");
            Serial.print("Connected to ");
            Serial.println(WiFi.SSID());
            Serial.print("IP address: ");
            Serial.println(WiFi.localIP());
            return true;
        }
        delay(500);
        Serial.print(".");
    }

    Serial.println("");
    Serial.println("Connection failed!");
    return false;
}

bool WiFiManager::loadWiFi(JsonDocument& doc) {
    String jsonString = preferences.getString(WIFI_KEY, "{}");
    DeserializationError error = deserializeJson(doc, jsonString);
    return !error;
}

bool WiFiManager::saveWiFi(const JsonDocument& doc) {
    String jsonString;
    serializeJson(doc, jsonString);
    return preferences.putString(WIFI_KEY, jsonString);
}