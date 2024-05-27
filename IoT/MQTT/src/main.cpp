#include <Arduino.h>
#include <ArduinoJson.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include "Guineapig.WiFiConfig.h"
#include "my-ca.h"

#define BTN 12
#define BUZZ 13

WiFiClientSecure espClient;
PubSubClient mqtt(espClient);

const char *server = "silverease.ntub.edu.tw";
const int mqtt_port = 8883;
const char *caCert = root_ca;

bool flag = false;

void callback(char *topic, byte *payload, unsigned int length)
{
  Serial.print("收到訊息：");
  String message = "";
  for (int i = 0; i < length; i++)
  {
    message += (char)payload[i];
    Serial.print((char)payload[i]);
  }
  Serial.println();
  Serial.println(message);
  if (String(topic)=="ESP32/got")
  {
    Serial.println("收到ESP32訊息");
    if (message == "OK")
    {
      int count = 0;
      while (count < 3)
      {
        Serial.println("我叫你叫");
        digitalWrite(BUZZ, HIGH);
        delay(1000);
        digitalWrite(BUZZ, LOW);
        delay(1000);
        count++;
      }
    };
  }
  if (String(topic)=="ESP32/help")
  {
    Serial.println("收到ESP32求救訊息");
    delay(5000);
    flag = false;
  };
  Serial.println();
};

void mqttInit()
{
  mqtt.setServer(server, mqtt_port);
  mqtt.setCallback(callback);
  mqtt.connect("ESP32Client");
  mqtt.subscribe("ESP32/#");
  if (mqtt.connected())
  {
    Serial.println("Publish message");
    mqtt.publish("ESP32/Conn", "Hello World");
  }
}

void setup()
{
  Serial.begin(115200);
  pinMode(BUZZ, OUTPUT);
  pinMode(BTN, INPUT);
  WiFiConfig.connectWiFi();
  espClient.setCACert(caCert);
  mqttInit();
}

void loop()
{
  mqtt.loop();

  Serial.println(digitalRead(BTN) == HIGH && flag == false);
  if (digitalRead(BTN) == HIGH && flag == false)
  {
    flag = true;
    Serial.println("按下按鈕");
    JsonDocument doc;
    doc["DevID"] = "1";
    doc["Message"] = "help";
    char json[200];
    serializeJson(doc, json);
    Serial.println(json);
    mqtt.publish("ESP32/help", json);
  }

  if (!mqtt.connected())
  {
    Serial.println("重新連線");
    mqtt.connect("ESP32Client");
  }
  if (WiFi.status() != WL_CONNECTED)
  {
    Serial.println("重新連線");
    WiFiConfig.connectWiFi();
  }
  delay(500);
}