#include <Arduino.h>
#include <ArduinoJson.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include "Guineapig.WiFiConfig.h"
#include "esp_camera.h"
#include "my-ca.h"
#include "Base64.h"

#define BTN 12
#define BUZZ 13

uint64_t macAddress = ESP.getEfuseMac();
uint64_t macAddressTrunc = macAddress << 40;
uint32_t chipID = macAddressTrunc >> 40;
const String DevID = String("ESP") + String(chipID, HEX);
const String TOPIC = String("ESP32/") + String(DevID.c_str());

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
  mqtt.setBufferSize(2048);
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
  static camera_config_t camera_config = {
      .pin_pwdn = 32,     // 斷電腳
      .pin_reset = -1,    // 重置腳
      .pin_xclk = 0,      // 外部時脈腳
      .pin_sscb_sda = 26, // I2C資料腳
      .pin_sscb_scl = 27, // I2C時脈腳
      .pin_d7 = 35,       // 資料腳
      .pin_d6 = 34,
      .pin_d5 = 39,
      .pin_d4 = 36,
      .pin_d3 = 21,
      .pin_d2 = 19,
      .pin_d1 = 18,
      .pin_d0 = 5,
      .pin_vsync = 25,                // 垂直同步腳
      .pin_href = 23,                 // 水平同步腳
      .pin_pclk = 22,                 // 像素時脈腳
      .xclk_freq_hz = 20000000,       // 設定外部時脈：20MHz
      .ledc_timer = LEDC_TIMER_0,     // 指定產生XCLK時脈的計時器
      .ledc_channel = LEDC_CHANNEL_0, // 指定產生XCLM時脈的通道
      .pixel_format = PIXFORMAT_JPEG, // 設定影像格式：JPEG
      .frame_size = FRAMESIZE_SVGA,   // 設定影像大小：UXGA
      .jpeg_quality = 5,              // 設定JPEG影像畫質，有效值介於0-63，數字越低畫質越高。
      .fb_count = 1                   // 影像緩衝記憶區數量
  };

  // ledcSetup(LEDC_CHANNEL_0, 5000, LEDC_TIMER_0);
  // ledcAttachPin(FLASH, LEDC_CHANNEL_0);

  // 初始化攝像頭
  esp_err_t err = esp_camera_init(&camera_config);
  if (err != ESP_OK)
  {
    Serial.printf("攝像頭出錯了，錯誤碼：0x%x", err);
  }
  Serial.println("攝像頭初始化成功");
}

void mqtt_img()
{
    // 拍照
  camera_fb_t * fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("Camera capture failed");
    return;
  }
  
  // 準備JSON數據
  JsonDocument doc;
  doc["width"] = fb->width;
  // doc["height"] = fb->height;
  // doc["size"] = fb->len;
  
  // 將圖片數據轉換為Base64
  String encoded = base64::encode(fb->buf, fb->len);
  doc["length"] = encoded.length();
  doc["image"] = encoded;
  
  // 序列化JSON
  String output;
  serializeJson(doc, output);
  
  // 發布到MQTT
  mqtt.publish(String(TOPIC + "/help").c_str(), output.c_str());
  // mqtt.beginPublish(String(TOPIC + "/help").c_str(), output.length(), false);
  // mqtt.print(output.c_str());
  // mqtt.endPublish();
  
  // 釋放相機緩衝區
  esp_camera_fb_return(fb);
}

void loop()
{
  mqtt.loop();

  Serial.println(digitalRead(BTN) == HIGH && flag == false);
  if (digitalRead(BTN) == HIGH && flag == false)
  {
    flag = true;
    Serial.println("按下按鈕");
    mqtt_img();
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