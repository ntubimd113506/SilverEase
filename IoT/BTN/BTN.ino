#define LED 4//已內建閃光燈
#define Btn 12//外接 VCC+IO12-Btn-(電阻)-GND
#define Sound 13//外接 IO13-蜂鳴器-GND

void setup() {
  pinMode(LED, OUTPUT);   //設定LED的PIN腳為輸出
  pinMode(Btn, INPUT);
}

void loop() {
  if (digitalRead(Btn)==LOW){
    tone(Sound, 500, 5000);
    digitalWrite(LED,HIGH);
  } else{
    digitalWrite(LED,LOW);
  }
}
