#include <Servo.h>
#include <LiquidCrystal.h>
#include <IRremote.hpp> 

// --- 1. Hardware Pins ---
const int irReceiverPin = 4; 
const int servoPin = 3;  
const int ledPin = 13;   
const int buzzerPin = 5; 

LiquidCrystal lcd(7, 8, 9, 10, 11, 12);
Servo swatterServo;      

// --- 2. System Variables ---
String screwTypes[] = {"Rusted", "Robertson", "Phillips", "Slot", "Hex"};
bool systemRunning = false; 
bool displayNeedsUpdate = true; 

// --- 3. Action Triggers & Timers ---
volatile bool triggerToggle = false;
volatile bool triggerDance = false;
volatile bool triggerKill = false;

char manualIRCommand = '\0';  
unsigned long lastIRTime = 0; 

void setup() {
  Serial.begin(9600); 
  
  pinMode(ledPin, OUTPUT); 
  pinMode(buzzerPin, OUTPUT); 
  
  swatterServo.attach(servoPin);
  swatterServo.write(90); 
  
  lcd.begin(16, 2); 
  
  IrReceiver.begin(irReceiverPin, DISABLE_LED_FEEDBACK);
  
  // Power-on sound (Perfect Ab5!)
  playTone(831, 150); 
  triggerToggle = true; 
}

void loop() {
  
  // ==========================================
  // --- STRICT IR REMOTE LOGIC ---
  // ==========================================
  
  if (IrReceiver.decode()) {
    if (IrReceiver.decodedIRData.protocol == NEC && !(IrReceiver.decodedIRData.flags & IRDATA_FLAGS_IS_REPEAT)) {
      uint16_t command = IrReceiver.decodedIRData.command;
      unsigned long currentTime = millis();
      
      if (currentTime - lastIRTime > 500) {
        if (command == 69) { triggerKill = true; lastIRTime = currentTime; } 
        else if (command == 64) { triggerToggle = true; lastIRTime = currentTime; } 
        else if (command == 71) { 
          if (systemRunning) { triggerDance = true; lastIRTime = currentTime; }
        } 
        else if (systemRunning) {
          if (command == 22) { manualIRCommand = '0'; lastIRTime = currentTime; } 
          else if (command == 12) { manualIRCommand = '1'; lastIRTime = currentTime; } 
          else if (command == 24) { manualIRCommand = '2'; lastIRTime = currentTime; } 
          else if (command == 94) { manualIRCommand = '3'; lastIRTime = currentTime; } 
          else if (command == 8)  { manualIRCommand = '4'; lastIRTime = currentTime; } 
        }
      }
    }
    IrReceiver.resume(); 
  }

  // ==========================================
  // --- EXECUTING THE ACTIONS ---
  // ==========================================

  if (triggerKill) {
    triggerKill = false;
    systemRunning = false;
    swatterServo.write(90); 
    
    printRow(0, "SYSTEM OFFLINE");
    printRow(1, "Hard Reset Req.");
    
    // The Kill Switch Alarm (Descending whole tones)
    playTone(622, 200); // Eb5
    playTone(523, 200); // C5
    playTone(440, 200); // A4
    playTone(370, 400); // Gb4
    
    while (true) { delay(100); } 
  }

  if (triggerDance) {
    triggerDance = false;
    celebrationDance();
    displayNeedsUpdate = true; 
  }

  if (triggerToggle) {
    triggerToggle = false;
    systemRunning = !systemRunning; 
    
    // Clean, perfect Ab5 for Pause/Play
    playTone(831, 100);

    if (systemRunning) {
      showLoadingBar("Init...   ");
    } else {
      showLoadingBar("Pausing...");
    }
    displayNeedsUpdate = true;
  }

  // ==========================================
  // --- THE UNIFIED BRAIN ---
  // ==========================================
  
  if (systemRunning) {
    if (displayNeedsUpdate) {
      printRow(0, "System: RUNNING");
      printRow(1, "Awaiting AI/IR");
      displayNeedsUpdate = false;
    }

    char incomingChar = '\0';
    bool fromCamera = false; 

    if (Serial.available() > 0) { 
      incomingChar = Serial.read(); 
      fromCamera = true; 
    } 
    else if (manualIRCommand != '\0') {
      incomingChar = manualIRCommand;
      manualIRCommand = '\0'; 
    }

    if (incomingChar >= '0' && incomingChar <= '4') {
      int screwIndex = incomingChar - '0';
      String detectedScrew = screwTypes[screwIndex];

      Serial.print("Confirmed! Swatting ");
      Serial.println(detectedScrew);

      // Hardware-driven Success "Coin" Sound
      playTone(1319, 80); // E6
      delay(20);
      playTone(2093, 150); // C7

      if (fromCamera) {
        digitalWrite(ledPin, HIGH); 
        delay(150); 
        digitalWrite(ledPin, LOW); 
      }

      printRow(0, "Type: " + detectedScrew);

      if (detectedScrew == "Rusted") {
        printRow(1, "Act: FAST +90");
        swatFast(180); 
      } else if (detectedScrew == "Robertson") {
        printRow(1, "Act: FAST -90");
        swatFast(0); 
      } else if (detectedScrew == "Phillips") {
        printRow(1, "Act: SLOW +90");
        sweepSlow(180); 
      } else {
        printRow(1, "Act: SLOW -90");
        sweepSlow(0); 
      }
      
      delay(400); 
      if (systemRunning) {
        sweepSlow(90); 
        delay(200);
        displayNeedsUpdate = true; 
      }

      while (IrReceiver.decode()) { IrReceiver.resume(); }
      lastIRTime = millis(); 
      while (Serial.available() > 0) { Serial.read(); }
    }
  } else {
    if (displayNeedsUpdate) {
      swatterServo.write(90); 
      printRow(0, "System: PAUSED");
      printRow(1, "Awaiting Remote");
      displayNeedsUpdate = false;
    }
    while (Serial.available() > 0) { Serial.read(); }
  }
}

// ==========================================
// --- REUSABLE UI & PHYSICS FUNCTIONS ---
// ==========================================

void printRow(int row, String text) {
  lcd.setCursor(0, row);
  lcd.print(text);
  for (unsigned int i = text.length(); i < 16; i++) { lcd.print(" "); }
}

void showLoadingBar(String label) {
  lcd.clear(); 
  for (int i = 0; i <= 16; i++) {
    if (IrReceiver.decode()) { IrReceiver.resume(); } 
    int percent = (i * 100) / 16;
    lcd.setCursor(0, 0);
    lcd.print(label);
    if (percent < 100) lcd.print(" ");
    if (percent < 10) lcd.print(" ");
    lcd.print(percent);
    lcd.print("%");
    
    lcd.setCursor(0, 1);
    for (int j = 0; j < i; j++) lcd.write(255); 
    
    delay(random(10, 50)); 
  }
}

void swatFast(int targetAngle) {
  if (targetAngle == 180) { swatterServo.write(70); delay(250); swatterServo.write(180); } 
  else { swatterServo.write(110); delay(250); swatterServo.write(0); }
}

void sweepSlow(int targetAngle) {
  if (targetAngle == 180) { swatterServo.write(60); delay(350); } 
  else if (targetAngle == 0) { swatterServo.write(120); delay(350); }

  int currentAngle = swatterServo.read(); 
  if (targetAngle > currentAngle) {
    for (int pos = currentAngle; pos <= targetAngle; pos++) { swatterServo.write(pos); delay(4); }
  } else {
    for (int pos = currentAngle; pos >= targetAngle; pos--) { swatterServo.write(pos); delay(4); }
  }
}

void safeDelay(unsigned long waitTime) {
  unsigned long startTime = millis();
  while (millis() - startTime < waitTime) {
    if (IrReceiver.decode()) {
      if (IrReceiver.decodedIRData.protocol == NEC && !(IrReceiver.decodedIRData.flags & IRDATA_FLAGS_IS_REPEAT)) {
        uint16_t command = IrReceiver.decodedIRData.command;
        unsigned long currentTime = millis();
        if (currentTime - lastIRTime > 500) {
          if (command == 64) { triggerToggle = true; lastIRTime = currentTime; } 
          else if (command == 69) { triggerKill = true; lastIRTime = currentTime; }
        }
      }
      IrReceiver.resume();
      if (triggerKill || triggerToggle) return; 
    }
    delay(1); 
  }
}

// ==========================================
// --- THE DISTORTION-FREE SOUND ENGINE ---
// ==========================================
void playTone(int frequency, int durationMs) {
  // 1. Tell the IR Receiver to turn off so it doesn't interrupt our math!
  IrReceiver.stop(); 

  // 2. Calculate the exact wavelength
  long halfPeriod = 1000000L / frequency / 2;
  long numCycles = (long)frequency * durationMs / 1000L;
  
  // 3. Play the pure note
  for (long i = 0; i < numCycles; i++) {
    digitalWrite(buzzerPin, HIGH);
    delayMicroseconds(halfPeriod);
    digitalWrite(buzzerPin, LOW);
    delayMicroseconds(halfPeriod);
  }

  // 4. Turn the IR Receiver back on instantly
  IrReceiver.start(); 
}

// ==========================================
// --- THE DANCE CHOREOGRAPHY ---
// ==========================================
void celebrationDance() {
  printRow(0, "1. Stretching...");
  printRow(1, "");
  for(int pos = 90; pos <= 160; pos++) { swatterServo.write(pos); safeDelay(12); if(triggerKill || triggerToggle) { swatterServo.write(90); return; } }
  for(int pos = 160; pos >= 20; pos--) { swatterServo.write(pos); safeDelay(12); if(triggerKill || triggerToggle) { swatterServo.write(90); return; } }
  for(int pos = 20; pos <= 90; pos++)  { swatterServo.write(pos); safeDelay(12); if(triggerKill || triggerToggle) { swatterServo.write(90); return; } }

  printRow(0, "2. The Jitter!");
  for(int i = 0; i < 15; i++) { 
    swatterServo.write(75); 
    playTone(1568, 60); // G6 (Takes exactly 60ms, acts as our delay)
    
    swatterServo.write(105); 
    playTone(1319, 60); // E6
  }
  
  while (IrReceiver.decode()) { IrReceiver.resume(); }

  printRow(0, "3. Windmill!!");
  for(int i = 0; i < 4; i++) { 
    swatterServo.write(0); safeDelay(300); if(triggerKill || triggerToggle) { swatterServo.write(90); return; }
    swatterServo.write(180); safeDelay(300); if(triggerKill || triggerToggle) { swatterServo.write(90); return; }
  }

  printRow(0, "   * Bows * ");
  swatterServo.write(90); 
  
  // Final happy sequence
  playTone(831, 100); delay(50);
  playTone(1047, 100); delay(50); // C6
  playTone(1319, 200); // E6
  
  while (IrReceiver.decode()) { IrReceiver.resume(); }
  lastIRTime = millis();
  
  safeDelay(1500); 
}