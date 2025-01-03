#include <Arduino.h>
#include <WiFi.h>
#include <WiFiClient.h>
// #include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include "Guineapig.WiFiConfig.h"
#include <ArduinoJson.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include "esp_camera.h"
#include "my-ca.h"
#include <TinyGPS++.h>
#include "soc/soc.h"
#include "soc/rtc_cntl_reg.h"

#define SERVER "silverease.ntub.edu.tw"
#define MQTT_PORT 8883
#define FLASH 33
#define BTN 12
#define BUZZ 13

WiFiClient client;
// WiFiClientSecure client;
PubSubClient mqtt(client);
TinyGPSPlus gps;

bool dev_link = false;
bool btn_flag = false;
bool cam_flag = false;

String latitude = "";
String longitude = "";
String getTime = "";
String devTime = "";
unsigned long lastGetTime = 0;
unsigned long lastSendTime = 0;
unsigned long sendDataTime = 0;
bool gpsLocat = false;

uint64_t macAddress = ESP.getEfuseMac();
uint64_t macAddressTrunc = macAddress << 40;
uint32_t chipID = macAddressTrunc >> 40;
const String DevID = String("ESP") + String(chipID, HEX);
const String TOPIC = String("ESP32/") + String(DevID.c_str());

void updateGPS()
{
  if (gps.date.isValid() && gps.time.isValid())
  {
    devTime = String(gps.date.year()) + "," + String(gps.date.month()) + "," + String(gps.date.day()) + "," + String(gps.time.hour()) + "," + String(gps.time.minute()) + "," + String(gps.time.second());
  }
  if (gps.location.isValid())
  {
    gpsLocat = true;
    latitude = String(gps.location.lat(), 6);
    longitude = String(gps.location.lng(), 6);
    getTime = devTime;
  }
}

void sendGPSData()
{
  updateGPS();
  if (gpsLocat)
  {
    JsonDocument doc;
    doc["lat"] = latitude;
    doc["lon"] = longitude;
    doc["sendTime"] = getTime;

    String jsonData;
    serializeJson(doc, jsonData);

    mqtt.publish(String(TOPIC + "/gps").c_str(), jsonData.c_str());
  }
}

void sos_morsecode()
{
  for (int i = 0; i < 3; i++)
  {
    digitalWrite(BUZZ, HIGH);
    vTaskDelay(250 / portTICK_PERIOD_MS);
    digitalWrite(BUZZ, LOW);
    vTaskDelay(250 / portTICK_PERIOD_MS);
  }
  for (int i = 0; i < 3; i++)
  {
    digitalWrite(BUZZ, HIGH);
    vTaskDelay(500 / portTICK_PERIOD_MS);
    digitalWrite(BUZZ, LOW);
    vTaskDelay(250 / portTICK_PERIOD_MS);
  }
  for (int i = 0; i < 3; i++)
  {
    digitalWrite(BUZZ, HIGH);
    vTaskDelay(250 / portTICK_PERIOD_MS);
    digitalWrite(BUZZ, LOW);
    vTaskDelay(250 / portTICK_PERIOD_MS);
  }
  vTaskDelay(1000 / portTICK_PERIOD_MS);
}

void callback(char *topic, byte *payload, unsigned int length)
{
  String action = topic + TOPIC.length() + 1;
  if (action == "isLink")
  {
    dev_link = true;
    Serial.println("change");
  }

  if (action == "setLink")
  {
    String message = "";
    for (int i = 0; i < length; i++)
    {
      message += (char)payload[i];
    }
    int cnt = 0;
    int res = 10;
    while (res > 0 and cnt < 3)
    {
      digitalWrite(BUZZ, HIGH);
      Serial.println(digitalRead(BTN));
      if (digitalRead(BTN))
      {
        digitalWrite(BUZZ, LOW);
        cnt++;
      }
      else
      {
        cnt = 0;
      }
      vTaskDelay(500 / portTICK_PERIOD_MS);
      digitalWrite(BUZZ, LOW);
      vTaskDelay(500 / portTICK_PERIOD_MS);
      res--;
    }
    if (cnt >= 3)
    {
      dev_link = true;
      mqtt.publish(String(TOPIC + "/link").c_str(), message.c_str());
    }
    else
    {
      mqtt.publish(String(TOPIC + "/link").c_str(), "fail");
    }
  }

  if (action == "SOSOver")
  {
    for (int cnt = 0; cnt < 2; cnt++)
    {
      sos_morsecode();
    }
    btn_flag = false;
  }

  if (action == "gotHelp")
  {
    for (int cnt = 0; cnt < 3; cnt++)
    {
      sos_morsecode();
    }
  }

  if (action == "newGPS")
  {
    sendGPSData();
  }
};

void reconnect()
{
  while (!WiFi.isConnected())
  {
    Serial.println("重新連接WiFi");
    WiFiConfig.connectWiFi();
    vTaskDelay(5000 / portTICK_PERIOD_MS);
  }
  int cnt = 0;
  while (!mqtt.connected() && cnt < 10)
  {
    Serial.print("MQTT 連接...");
    if (mqtt.connect(DevID.c_str(), String(TOPIC + "/offline").c_str(), 0, 0, "offline"))
    {
      Serial.println("已連接");
      mqtt.subscribe(String(TOPIC + "/#").c_str());
    }
    else
    {
      Serial.print("失敗, rc=");
      Serial.print(mqtt.state());
      Serial.println(" 1秒後重試");
      cnt++;
      vTaskDelay(1000 / portTICK_PERIOD_MS);
    }
  }
}

void mqttTask(void *parameter)
{
  while (1)
  {
    if (!mqtt.connected())
    {
      reconnect();
    }
    mqtt.loop();
    vTaskDelay(50 / portTICK_PERIOD_MS);
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
  Serial.println("攝像頭初始化成功");
  return true;
}

void SendImageMQTT()
{
  sendGPSData();
  if (!gpsLocat)
  {
    mqtt.publish(String(TOPIC + "/noSOSLocat").c_str(), devTime.c_str());
  }
  camera_fb_t *fb = NULL;
  fb = esp_camera_fb_get();
  esp_camera_fb_return(fb);
  fb = esp_camera_fb_get();
  if (!fb)
  {
    mqtt.publish(String(TOPIC + "/help").c_str(), "noImage");
    return;
  }
  size_t fbLen = fb->len;
  int ps = 512;
  // 開始傳遞影像檔
  mqtt.beginPublish(String(TOPIC + "/help").c_str(), fbLen, false);
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
  mqtt.publish(String(TOPIC + "/SOSOver").c_str(), "");
}

void mainTask(void *parameter)
{
  int btn_cnt = 0;
  while (1)
  {
    if (WiFi.status() == WL_CONNECTED)
    {
      bool flag = digitalRead(BTN) && !btn_flag;
      if (flag)
      {
        btn_cnt++;
        if (btn_cnt >= 3)
        {
          btn_flag = true;
          digitalWrite(BUZZ, HIGH);
          vTaskDelay(1000 / portTICK_PERIOD_MS);
          digitalWrite(BUZZ, LOW);
          SendImageMQTT();
          vTaskDelay(5000 / portTICK_PERIOD_MS);
          btn_cnt = 0;
        }
      }
    }
    else
    {
      Serial.println("重新連接");
      WiFiConfig.connectWiFi();
      vTaskDelay(5000 / portTICK_PERIOD_MS);
    }
    vTaskDelay(500 / portTICK_PERIOD_MS);
  }
}

void setup()
{
  WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0); // disable brownout detector
  Serial.begin(9600);
  Serial.println("ESP32CAM Setup…");
  pinMode(BTN, INPUT);
  pinMode(BUZZ, OUTPUT);
  cam_flag = initCamera();
  /** tls 連線
   * client.setCACert(root_ca);
   */
  mqtt.setServer(SERVER, MQTT_PORT);
  mqtt.setCallback(callback);
  WiFiConfig.connectWiFi();

  xTaskCreatePinnedToCore(
      mqttTask,    // 任務函數
      "MQTT_Task", // 任務名稱
      8192,        // 堆棧大小
      NULL,        // 任務參數
      1,           // 任務優先級
      NULL,        // 任務句柄
      0            // 任務核心
  );
  while (!dev_link)
  {
    mqtt.publish(String(TOPIC + "/checkLink").c_str(), "");
    vTaskDelay(5000 / portTICK_PERIOD_MS);
  }

  xTaskCreate(mainTask, "Main_Task", 8192, NULL, 1, NULL);
}

void loop()
{
  unsigned long currentTime = millis();

  if (Serial.available() > 0)
  {
    gps.encode(Serial.read());
    updateGPS();

    if (currentTime - lastGetTime >= 5000)
    {
      lastGetTime = currentTime;
      JsonDocument doc;
      doc["lat"] = latitude;
      doc["lon"] = longitude;
      doc["devTime"] = devTime;
      doc["getTime"] = getTime;
      String jsonData;
      serializeJson(doc, jsonData);
      mqtt.publish(String("MsgBy/" + DevID).c_str(), jsonData.c_str());
      Serial.println(jsonData);
    }
  }

  if (currentTime - lastSendTime >= 60000)
  { // 60000 毫秒 = 1分鐘/
    lastSendTime = currentTime;
    Serial.println("1min");
    sendGPSData();
  }
}