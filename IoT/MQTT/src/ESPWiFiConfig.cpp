#include <Arduino.h>
#include <WiFi.h>
#include <ESPAsyncWebServer.h>
#include "ESPWiFIConfig.h"

#define LED_BUILTIN 33

void ESPWiFiConfig::printLog(String msg)
{
    Serial.print(msg);
    if (this->logCallback != 0)
        this->logCallback(msg);
}

bool ESPWiFiConfig::connectWiFi()
{
    if (this->ssid != NULL || this->pwd != NULL)
    {
        WiFi.mode(WIFI_STA);
        WiFi.begin(this->ssid, this->pwd);
        return true;
    }
    else
    {
        initConfigWeb();
        return false;
    }
}

void ESPWiFiConfig::initConfigWeb()
{
    WiFi.mode(WIFI_AP_STA);
    WiFi.softAP("ESP32-AP", "12345678");
    AsyncWebServer server(80);

    String state("WAIT"), msg("請設定 SSID 與密碼");
    bool reboot = false;

    server.on("/", HTTP_GET, [](AsyncWebServerRequest *request)
              { request->send_P(200, "text/html", wifi_config_html); });

    server.on("/", HTTP_POST, [this, &state, &msg, &reboot](AsyncWebServerRequest *request)
              {
                if ((*request->getParam("action", true)).value() == "重新啟動") {
                    reboot = true;
                }
                else{
                    this->ssid = (*request->getParam("ssid", true)).value();
                    this->pwd = (*request->getParam("passwd", true)).value();
                    msg = "正在測試 [" + ssid + "] 無線網路...";
                    state = "CONNECTING";
                }
                
                request->send(200, "text/plain", "OK"); });

    server.on("/status", HTTP_GET, [&state, &msg](AsyncWebServerRequest *request)
              { request->send(200, "application/json", "{ \"state\":\"" + state + "\", \"msg\":\"" + msg + "\" }"); });

    server.begin();

    String wifiIp;
    while (true)
    {
        if (state == "CONNECTING")
        {
            WiFi.begin(ssid.c_str(), pwd.c_str());
            this->printlnLog("connecting [" + ssid + "] ");
            int timeout = 30;
            while (WiFi.status() != WL_CONNECTED && timeout-- > 0)
            {
                this->printLog(".");
                delay(1000);
            }
            this->printlnLog();
            if (WiFi.status() == WL_CONNECTED)
            {
                this->printlnLog("connected.");
                wifiIp = WiFi.localIP().toString();
                this->printlnLog("IP=" + wifiIp);
                state = "CONNECTED";
                msg = "[" + ssid + "]連線成功<br />IP " + wifiIp + "<br />重新啟動後生效";
            }
            else
            {
                this->printlnLog(ssid + " not connected");
                state = "FAILED";
                msg = "[" + ssid + "]連線失敗<br />請重新輸入";
            }
        }
        if (reboot)
        {
            state = "REBOOT";
            msg = "ESP 正在重新啟動...<br />稍後請切換網路";
            delay(5000);
            ESP.restart();
        }
        digitalWrite(LED_BUILTIN, digitalRead(LED_BUILTIN) ^ 1);
        delay(200);
    }
}