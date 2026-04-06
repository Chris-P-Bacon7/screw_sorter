//Outputs the total time of IR activation once released

//Circuit
// Arduino Uno  -->   TCRT5000
// 5v           --->   VCC
// Grnd         --->   Grnd
// A0           --->   A0
// D8           --->   D0

const int pinIRd = 8;
const int pinLED = 13;

int IRvalueD = 0;
bool sensorActive = false;
unsigned long activeStartTime = 0;

void setup()
{
  Serial.begin(9600);
  pinMode(pinIRd, INPUT);
  pinMode(pinLED, OUTPUT);
}

void loop()
{
  IRvalueD = digitalRead(pinIRd);

  if (IRvalueD == LOW && !sensorActive) {
    sensorActive = true;
    activeStartTime = millis();
  }

  if (IRvalueD == HIGH && sensorActive) {
    sensorActive = false;
    unsigned long duration = millis() - activeStartTime;
    Serial.print("Duration: ");
    Serial.print(duration);
    Serial.println(" ms");
  }

  digitalWrite(LED_BUILTIN, IRvalueD == LOW ? HIGH : LOW);

  delay(10);
}