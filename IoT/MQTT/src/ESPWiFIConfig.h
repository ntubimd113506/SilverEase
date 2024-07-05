#include <Arduino.h>
#include <WiFi.h>
#include <ESPAsyncWebServer.h>
#include "WiFIManager.h"

class ESPWiFiConfig
{
public:
    ESPWiFiConfig() = default;
    typedef void (*LogCallback)(String);
    LogCallback logCallback;
    bool connectWiFi();

private:
    WiFiManager WiFiManager;
    void initConfigWeb();
    void printLog(String msg);
    void printlnLog(String msg) { printLog(msg + "\n"); }
    void printlnLog() { printlnLog(""); }
};
extern ESPWiFiConfig WiFiConfig;

const char wifi_config_html[] PROGMEM = R"====(
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta charset="utf-8" />
    <style>
        .content { width: 240px; margin: 0 auto; font-size: 16pt; font-family: '微軟正黑體' }
        form > * { width: 95%; margin: 6px auto;  }
        #dvStatus { font-size: 14pt; color: dodgerblue; }
    </style>
</head>
<body>
<div class=content>
    <div style='text-align:center'>無線網路設定<div>
    <form action="/" method="POST" target='submitRes'>
    <input name="ssid" placeholder="SSID" />
    <input type="password" name="passwd" placeholder="請輸入密碼" />
    <input type="submit" name="action" value="儲存設定" id=btnSave />
    <input type="submit" name="action" value="重新啟動" disabled id=btnReboot />
    </form>
    <iframe name='submitRes' style='display:none'></iframe>
    <div id=dvStatus></div>
</div>
<script>
var xhr = new XMLHttpRequest();
xhr.addEventListener("load", function() {
    var res = JSON.parse(this.responseText);
    document.getElementById('dvStatus').innerHTML = res.msg;
    if (res.state == "CONNECTED") {
        document.getElementById('btnSave').disabled = true;
        document.getElementById('btnReboot').disabled = false;
    }
    else if (res.state == "REBOOT") {
        clearInterval(hnd);
    }
});
var hnd = setInterval(function() { 
    xhr.open("GET", "http://" + location.host + "/status");
    xhr.send(); 
}, 1000);
</script>
</body></html>
)====";