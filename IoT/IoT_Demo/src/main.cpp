#include <Arduino.h>
#include <WiFi.h>
#include <ESPAsyncWebServer.h>
#include "Guineapig.WiFiConfig.h"
#include "esp_camera.h"

#define FLASH       4
#define BTN         12
#define BUZZ        13
#define SERVER      "silverease.ntub.edu.tw"  
#define UPLOAD_URL  "/cam/esp32cam"
#define PORT        80

AsyncWebServer webServer(80);
WiFiClient client;

bool btn_flag=false;

bool initCamera() {
  // 設定攝像頭的接腳和影像格式與尺寸
  static camera_config_t camera_config = {
    .pin_pwdn       = 32,  // 斷電腳
    .pin_reset      = -1,  // 重置腳
    .pin_xclk       = 0,   // 外部時脈腳
    .pin_sscb_sda   = 26,  // I2C資料腳
    .pin_sscb_scl   = 27,  // I2C時脈腳
    .pin_d7         = 35,  // 資料腳
    .pin_d6         = 34,
    .pin_d5         = 39,
    .pin_d4         = 36,
    .pin_d3         = 21,
    .pin_d2         = 19,
    .pin_d1         = 18,
    .pin_d0         = 5,
    .pin_vsync      = 25,   // 垂直同步腳
    .pin_href       = 23,   // 水平同步腳
    .pin_pclk       = 22,   // 像素時脈腳
    .xclk_freq_hz   = 20000000,       // 設定外部時脈：20MHz
    .ledc_timer     = LEDC_TIMER_0,   // 指定產生XCLK時脈的計時器
    .ledc_channel   = LEDC_CHANNEL_0, // 指定產生XCLM時脈的通道
    .pixel_format   = PIXFORMAT_JPEG, // 設定影像格式：JPEG
    .frame_size     = FRAMESIZE_SVGA, // 設定影像大小：SVGA
    .jpeg_quality   = 5,  // 設定JPEG影像畫質，有效值介於0-63，數字越低畫質越高。
    .fb_count       = 1    // 影像緩衝記憶區數量
  };

  // 初始化攝像頭
  esp_err_t err = esp_camera_init(&camera_config);
  if (err != ESP_OK) {
    Serial.printf("攝像頭出錯了，錯誤碼：0x%x", err);
    return false;
  }

  return true;
}

void postImage() {
  camera_fb_t *fb = NULL;    // 宣告儲存影像結構資料的變數
  fb = esp_camera_fb_get();  // 拍照

  if(!fb) {
    Serial.println("無法取得影像資料…");
    delay(1000);
    ESP.restart();  // 重新啟動
  }

  Serial.printf("連接伺服器：%s\n", SERVER);

  if (client.connect(SERVER, PORT)) {
    Serial.println("開始上傳影像…");     

    String boundBegin = "--ESP32CAM\r\n";
    boundBegin += "Content-Disposition: form-data; name=\"DevID\"\r\n";
    boundBegin += "\r\n";
    boundBegin += "1\"\r\n";
    boundBegin +="--ESP32CAM\r\n";
    boundBegin += "Content-Disposition: form-data; name=\"filename\"; filename=\"pict.jpg\"\r\n";
    boundBegin += "Content-Type: image/jpeg\r\n";
    boundBegin += "\r\n";

    String boundEnd = "\r\n--ESP32CAM--\r\n";

    uint32_t imgSize = fb->len;  // 取得影像檔的大小
    uint32_t payloadSize = boundBegin.length() + imgSize + boundEnd.length();

    String httpMsg = String("POST ") + UPLOAD_URL + " HTTP/1.1\r\n";
    httpMsg += String("Host: ") + SERVER + "\r\n";
    httpMsg += "User-Agent: Arduino/ESP32CAM\r\n";
    httpMsg += "Content-Length: " + String(payloadSize) + "\r\n";
    httpMsg += "Content-Type: multipart/form-data; boundary=ESP32CAM\r\n";
    httpMsg += "\r\n";

    
    httpMsg += boundBegin;

    // 送出HTTP標頭訊息
    client.print(httpMsg.c_str());

    // 上傳檔案
    uint8_t *buf = fb->buf;

    for (uint32_t i=0; i<imgSize; i+=1024) {
      if (i+1024 < imgSize) {
        client.write(buf, 1024);
        buf += 1024;
      } else if (imgSize%1024>0) {
        uint32_t remainder = imgSize%1024;
        client.write(buf, remainder);
      }
    }

    client.print(boundEnd.c_str());

    esp_camera_fb_return(fb);

    // 等待伺服器的回應（10秒）
    long timout = 10000L + millis();

    while (timout > millis()) {
      Serial.print(".");
      delay(100);

      if (client.available()){
        // 讀取伺服器的回應
        Serial.println("\n伺服器回應：");
        String line = client.readStringUntil('\r');
        Serial.println(line);
        break;
      }
    }

    Serial.println("關閉連線");
  } else {
    Serial.printf("無法連接伺服器：%s\n", SERVER);
  }

  client.stop();  // 關閉用戶端
}

void setup()
{
  initCamera();
  Serial.begin(115200);
  pinMode(BTN, INPUT);
  pinMode(BUZZ, OUTPUT);
  Serial.println(WiFiConfig.connectWiFi());
}

void loop()
{
  if (WiFi.status() == WL_CONNECTED){
    delay(1000);
    Serial.println(digitalRead(BTN)==LOW && btn_flag==false);
    if (digitalRead(BTN)==LOW && btn_flag==false){
      btn_flag = true;
      tone(BUZZ, 800, 5000);
      noTone(BUZZ);
      Serial.println("按下按鈕");
      postImage();
      tone(BUZZ, 1280, 3000);
      noTone(BUZZ);
      delay(2000);
    }
  }

  else{
    WiFiConfig.connectWiFi();
    delay(500);
  }
}