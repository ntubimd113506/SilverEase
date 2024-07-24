#include <Arduino.h>
#include <ArduinoJson.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include "Guineapig.WiFiConfig.h"
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include "esp_camera.h"
#include "my-ca.h"

#define SERVER "silverease.ntub.edu.tw"
#define MQTT_PORT 8883
#define FLASH 33
#define BTN 12
#define BUZZ 13

WiFiClientSecure client;
PubSubClient mqtt(client);

bool init_flag = false;
bool dev_link = false;
bool btn_flag = false;

uint64_t macAddress = ESP.getEfuseMac();
uint64_t macAddressTrunc = macAddress << 40;
uint32_t chipID = macAddressTrunc >> 40;
const String DevID = String("ESP") + String(chipID, HEX);
const String TOPIC = String("ESP32/") + String(DevID.c_str());

void callback(char *topic, byte *payload, unsigned int length)
{
  // Serial.print("收到訊息：");
  String message = "";
  for (int i = 0; i < length; i++)
  {
    message += (char)payload[i];
    // Serial.print((char)payload[i]);
  }
  // Serial.println();
  String action = topic + TOPIC.length() + 1;

  Serial.println(action);
  Serial.println(message);
  Serial.print("ACTION: ");
  Serial.println((action == "connect"));
  Serial.print("MESSAGE: ");
  Serial.println((message == "isLink"));
  Serial.print("RESULT: ");
  Serial.println((action == "connect" && message == "isLink"));
  if (action == "connect" && message == "isLink")
  {
    dev_link = true;
    Serial.println("change");
  }

  if (message == "收到")
  {
    int count = 0;
    while (count < 3)
    {
      Serial.println("我叫你叫");
      digitalWrite(BUZZ, HIGH);
      vTaskDelay(1000 / portTICK_PERIOD_MS);
      digitalWrite(BUZZ, LOW);
      vTaskDelay(1000 / portTICK_PERIOD_MS);
      count++;
    }
  }
};

void reconnect()
{
  while (!mqtt.connected())
  {
    Serial.print("嘗試 MQTT 連接...");
    if (mqtt.connect("ESP32Client"))
    {
      Serial.println("已連接");
      mqtt.subscribe(String(TOPIC + "/#").c_str());
    }
    else
    {
      Serial.print("失敗, rc=");
      Serial.print(mqtt.state());
      Serial.println(" 5秒後重試");
      vTaskDelay(1000 / portTICK_PERIOD_MS);
    }
  }
}

void mqttTask(void *parameter)
{
  for (;;)
  {
    if (!mqtt.connected())
    {
      reconnect();
    }
    mqtt.loop();
    vTaskDelay(10 / portTICK_PERIOD_MS);
  }
}

bool initCamera()
{
  // 設定攝像頭的接腳和影像格式與尺寸
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

  // 初始化攝像頭
  esp_err_t err = esp_camera_init(&camera_config);
  if (err != ESP_OK)
  {
    Serial.printf("攝像頭出錯了，錯誤碼：0x%x", err);
    return false;
  }

  return true;
}

String SendImageMQTT()
{
  camera_fb_t *fb = esp_camera_fb_get();
  size_t fbLen = fb->len;
  int ps = 512;
  // 開始傳遞影像檔
  mqtt.beginPublish("ESP32/cam", fbLen, false);
  uint8_t *fbBuf = fb->buf;
  for (size_t n = 0; n < fbLen; n = n + 2048)
  {
    if (n + 2048 < fbLen)
    {
      mqtt.write(fbBuf, 2048);
      fbBuf += 2048;
    }
    else if (fbLen % 2048 > 0)
    {
      size_t remainder = fbLen % 2048;
      mqtt.write(fbBuf, remainder);
    }
  }
  boolean isPublished = mqtt.endPublish();
  esp_camera_fb_return(fb); // 清除緩衝區
  if (isPublished)
  {
    return "MQTT傳輸成功";
  }
  else
  {
    return "MQTT傳輸失敗，請檢查網路設定";
  }
}

void setup()
{
  Serial.begin(115200);
  Serial.println("ESP32CAM 開始執行…");
  pinMode(BTN, INPUT);
  pinMode(BUZZ, OUTPUT);
  Serial.println("初始化攝像頭…");
  initCamera();
  ledcSetup(LEDC_CHANNEL_0, 5000, LEDC_TIMER_0);
  ledcAttachPin(FLASH, LEDC_CHANNEL_0);
  Serial.println("初始化完成");
  WiFiConfig.connectWiFi();
  Serial.println("連接成功");
  client.setCACert(root_ca);
  mqtt.setServer(SERVER, MQTT_PORT);
  mqtt.setCallback(callback);
  
  xTaskCreate(
      mqttTask,    // 任務函數
      "MQTT Task", // 任務名稱
      8192,        // 堆棧大小
      NULL,        // 任務參數
      1,           // 任務優先級
      NULL         // 任務句柄
  );
}

void loop()
{
  Serial.println("執行主程式…");
  if (WiFi.status() == WL_CONNECTED && mqtt.connected())
  {
    Serial.print("DEV Link: ");
    Serial.println(dev_link);
    if (dev_link)
    {
      // mqtt.loop();
      Serial.print("FLAG: ");
      bool flag = digitalRead(BTN) && !btn_flag;
      Serial.println(flag);
      if (flag)
      {
        btn_flag = true;
        tone(BUZZ, 800, 5000);
        noTone(BUZZ);
        SendImageMQTT();
        tone(BUZZ, 1280, 3000);
        noTone(BUZZ);
        delay(2000);
      }
    }
    else
    {
      mqtt.publish(String(TOPIC + "/connect").c_str(), "check");
      vTaskDelay(5000 / portTICK_PERIOD_MS);
    }
  }
  else
  {
    WiFiConfig.connectWiFi();
    mqtt.connect("ESP32CAM");
    if (mqtt.connected())
    {
      mqtt.subscribe("myTopic");
      mqtt.publish("myTopic", "Hello World");
    }

    delay(5000);
  }
  delay(1000);
}