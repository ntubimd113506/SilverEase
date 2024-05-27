#include <Arduino.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include "my-ca.h"

#define BUZZ 13

const char *ssid = "77";
const char *password = "776+chocolate";
const char *server = "silverease.ntub.edu.tw";
const int mqtt_port = 8883;
const char *caCert = root_ca;

WiFiClientSecure espClient;
PubSubClient mqtt(espClient);

void mqttInit() {
  mqtt.setServer(server, mqtt_port);
  mqtt.setCallback([](char *topic, byte *payload, unsigned int length) {
    Serial.print("收到訊息：");
    String message="";
    for (int i = 0; i < length; i++) {
      message+=(char)payload[i];    
      Serial.print((char)payload[i]);
    }
    Serial.println();
    Serial.println(message);
    if(message=="收到"){
      int count=0;
      while(count<3){
        Serial.println("我叫你叫");
        digitalWrite(BUZZ, HIGH);
        delay(1000);
        digitalWrite(BUZZ, LOW);
        delay(1000);
        count++;
      }
    };
    Serial.println();
  });
  mqtt.connect("ESP32Client");
  mqtt.subscribe("ESP001");
}

void setup() {
  Serial.begin(115200);
  pinMode(BUZZ, OUTPUT);
  WiFi.begin(ssid, password);
  espClient.setCACert(caCert);
  Serial.println("\n\n連接Wi-Fi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n連接成功");
  mqttInit();
  delay(5000);
  if (mqtt.connected())
  {
    Serial.println("Publish message");
    mqtt.publish("myTopic", "Hello World");
  }
}

void loop() {
  if (!mqtt.connected()) {
    Serial.println("重新連線");
    mqtt.connect("ESP32Client");
  }
  mqtt.loop();
}