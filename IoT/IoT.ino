#include "index.h"
#include <WiFi.h>
#include <WiFiClient.h>
#include <WiFiAP.h>
#include <WebServer.h>

const char *ssid = "SilverEaseIoT";
const char *password = "123456789";

WebServer server(80);

//root page
void handleRoot(){
  server.send(200,"text/html",PAGE_INDEX);
}

//wifi 處理及連線
void handleWifi(){
  Serial.println(server.args());
  server.send(200,"text/html",PAGE_INDEX);

  // 連線到指定的WiFi 
  WiFi.mode(WIFI_STA);
  WiFi.begin(server.arg("ssid"), server.arg("password"));
  Serial.println("");

  // Wait for connection
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("");
  Serial.print("Connected to ");
  Serial.println(ssid);
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());
}

void setup(void) {
  Serial.begin(115200);
  Serial.println();
  Serial.println("Configuring access point...");

  //啟動AP
  if (!WiFi.softAP(ssid, password)) {
    log_e("Soft AP creation failed.");
    while(1);
  }
  IPAddress myIP = WiFi.softAPIP();
  Serial.print("AP IP address: ");
  Serial.println(myIP);
  
  //設定路由
  server.on("/",handleRoot);
  server.on("/wifiInfo",handleWifi);
  
  //啟動server
  server.begin();
  Serial.println("Server started");
  
}

void loop(void) {
  server.handleClient();
  delay(2);
}
