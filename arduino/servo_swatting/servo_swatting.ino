#include <Servo.h>
#include <LiquidCrystal.h>
#include <IRremote.hpp> 

// ==========================================
// --- 1. HARDWARE PINS & SERVO CONFIG ---
// ==========================================
const int irReceiverPin = 4; 
const int servoPin = 3;
const int ledPin = 13;   
const int buzzerPin = 5; 

const int stepPin = A2;  
const int dirPin = A1;   
const int irGatePin = 2; 

// --- DIVERTER SETTINGS ---
const int SERVO_CLOSED = 90;  // Normal position (lets clean screws slide past)
const int SERVO_OPEN = 180;   // Divert position (drops rusted screws into early bin)

LiquidCrystal lcd(7, 8, 9, 10, 11, 12);
Servo swatterServo;

// ==========================================
// --- 2. SYSTEM VARIABLES ---
// ==========================================
String screwTypes[] = {"Rusted", "Clean", "Phillips", "Slot", "Hex"};
bool systemRunning = false; 
bool displayNeedsUpdate = true; 
bool screenOn = true;

unsigned long lastStepMicros = 0;
int stepSpeed = 2500; 
const int maxSpeed = 300;  
const int minSpeed = 5000; 

int pendingScrewIndex = -1;    
bool waitingForGate = false;   

// ==========================================
// --- 3. ACTION TRIGGERS & TIMERS ---
// ==========================================
volatile bool triggerToggle = false;
volatile bool triggerDance = false;
volatile bool triggerScreen = false;

char manualIRCommand = '\0';  
unsigned long lastIRTime = 0;

void setup() {
  Serial.begin(9600); 
  
  pinMode(ledPin, OUTPUT); 
  pinMode(buzzerPin, OUTPUT); 
  pinMode(irGatePin, INPUT_PULLUP);
  
  pinMode(stepPin, OUTPUT);
  pinMode(dirPin, OUTPUT);
  digitalWrite(dirPin, HIGH); 
  
  swatterServo.attach(servoPin);
  swatterServo.write(SERVO_CLOSED); 
  
  lcd.begin(16, 2); 
  IrReceiver.begin(irReceiverPin, DISABLE_LED_FEEDBACK);

  playTone(831, 150); 
}

void loop() {
  // ==========================================
  // --- STRICT IR REMOTE LOGIC ---
  // ==========================================
  if (IrReceiver.decode()) {
    if (IrReceiver.decodedIRData.protocol == NEC && !(IrReceiver.decodedIRData.flags & IRDATA_FLAGS_IS_REPEAT)) {
      uint16_t command = IrReceiver.decodedIRData.command;
      unsigned long currentTime = millis();
      
      if (currentTime - lastIRTime > 300) { 
        if (command == 69) { triggerScreen = true; lastIRTime = currentTime; } 
        else if (command == 70) { adjustSpeed(true); lastIRTime = currentTime; } 
        else if (command == 21) { adjustSpeed(false); lastIRTime = currentTime; } 
        else if (command == 64) { triggerToggle = true; lastIRTime = currentTime; } 
        else if (command == 71) { triggerDance = true; lastIRTime = currentTime; } 
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
  if (triggerScreen) {
    triggerScreen = false;
    screenOn = !screenOn;
    if (screenOn) { lcd.display(); playTone(1047, 100); } 
    else { lcd.noDisplay(); playTone(523, 100); }
  }

  if (triggerDance) {
    triggerDance = false;
    celebrationDance();
    displayNeedsUpdate = true;
  }

  if (triggerToggle) {
    triggerToggle = false;
    systemRunning = !systemRunning;
    playTone(831, 100); 
    
    if (systemRunning && screenOn) { showLoadingBar("Init...   "); } 
    else if (!systemRunning && screenOn) { showLoadingBar("Pausing..."); }
    displayNeedsUpdate = true;
  }

  // ==========================================
  // --- GLOBAL SERIAL READER ---
  // ==========================================
  char incomingChar = '\0';
  if (Serial.available() > 0) { incomingChar = Serial.read(); } 
  else if (manualIRCommand != '\0') { incomingChar = manualIRCommand; manualIRCommand = '\0'; }

  // Overrides from Python via USB
  if (incomingChar == 'S' && !systemRunning) {
    systemRunning = true;
    playTone(831, 100); 
    if (screenOn) showLoadingBar("Camera Live! ");
    displayNeedsUpdate = true;
  } 
  else if (incomingChar == 'P' && systemRunning) {
    systemRunning = false;
    playTone(523, 100); 
    displayNeedsUpdate = true;
  }

  // ==========================================
  // --- THE UNIFIED BRAIN ---
  // ==========================================
  if (systemRunning) {
    // 1. Keep the belt rolling constantly!
    unsigned long currentMicros = micros();
    if (currentMicros - lastStepMicros >= stepSpeed) {
      lastStepMicros = currentMicros;
      digitalWrite(stepPin, HIGH);
      delayMicroseconds(5); 
      digitalWrite(stepPin, LOW);
    }

    // 2. Default UI 
    if (displayNeedsUpdate && screenOn && !waitingForGate) {
      printRow(0, "System: RUNNING");
      printRow(1, "Awaiting Screws ");
      displayNeedsUpdate = false;
    }

    // 3. STEP 1: LOG THE SCREW IN MEMORY
    if (incomingChar >= '0' && incomingChar <= '4' && !waitingForGate) {
      pendingScrewIndex = incomingChar - '0';
      waitingForGate = true; 
      playTone(1047, 50); 
      
      if (screenOn) {
        printRow(0, "Seen: " + screwTypes[pendingScrewIndex]);
        printRow(1, "Waiting on Gate!");
      }
    }

    // 4. STEP 2: WAIT FOR IT TO HIT THE TRIPWIRE
    if (waitingForGate && digitalRead(irGatePin) == HIGH) {
      String detectedScrew = screwTypes[pendingScrewIndex];
      Serial.print("Gate Triggered! Checked: ");
      Serial.println(detectedScrew);

      // --- THE NEW DIVERTER LOGIC ---
      if (detectedScrew == "Rusted") {
        playTone(1319, 80); 
        safeDelay(20);          
        playTone(2093, 150); 
        
        if (screenOn) {
            printRow(0, "Rejecting...");
            printRow(1, "Act: DIVERTING!");
        }
        
        // Open the trapdoor/diverter
        swatterServo.write(SERVO_OPEN);
        
        // Wait 1.5 seconds for the screw to fall in
        safeDelay(1500);         
        
        // Snap it closed again!
        swatterServo.write(SERVO_CLOSED);
        safeDelay(300); // Give the physical motor a moment to finish moving
        
      } else {
        // IT IS A CLEAN SCREW! The servo does absolutely nothing.
        if (screenOn) {
            printRow(0, "Clean: " + detectedScrew);
            printRow(1, "Act: PASSING...");
        }
        
        // Give the screw exactly 1 second to slide past the gate into the 
        // mechanical sorter without triggering the sensor twice.
        safeDelay(1000); 
      }

      // Reset the gate logic
      waitingForGate = false;
      pendingScrewIndex = -1;
      displayNeedsUpdate = true;

      while (IrReceiver.decode()) { IrReceiver.resume(); }
      lastIRTime = millis();
      while (Serial.available() > 0) { Serial.read(); } 
    }
    
  } else {
    // PAUSED STATE
    if (displayNeedsUpdate && screenOn) {
      swatterServo.write(SERVO_CLOSED);
      printRow(0, "System: PAUSED");
      printRow(1, "Awaiting Camera");
      displayNeedsUpdate = false;
    }
  }
}

// ==========================================
// --- REUSABLE UI & PHYSICS FUNCTIONS ---
// ==========================================

void adjustSpeed(bool faster) {
  if (faster) {
    stepSpeed -= 200; 
    if (stepSpeed < maxSpeed) stepSpeed = maxSpeed;
  } else {
    stepSpeed += 200; 
    if (stepSpeed > minSpeed) stepSpeed = minSpeed;
  }
  playTone(1568, 50); 
  if (screenOn) {
    lcd.clear();
    printRow(0, "BELT SPEED:");
    int displayLevel = map(stepSpeed, minSpeed, maxSpeed, 1, 15);
    printRow(1, "Level: " + String(displayLevel));
    safeDelay(500); 
    displayNeedsUpdate = true; 
  }
}

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
    safeDelay(random(10, 50)); 
  }
}

void playTone(int frequency, int durationMs) {
  IrReceiver.stop(); 
  long halfPeriod = 1000000L / frequency / 2;
  long numCycles = (long)frequency * durationMs / 1000L;
  for (long i = 0; i < numCycles; i++) {
    digitalWrite(buzzerPin, HIGH);
    delayMicroseconds(halfPeriod);
    digitalWrite(buzzerPin, LOW);
    delayMicroseconds(halfPeriod);
    if (systemRunning) {
      unsigned long currentMicros = micros();
      if (currentMicros - lastStepMicros >= stepSpeed) {
        lastStepMicros = currentMicros;
        digitalWrite(stepPin, HIGH);
        delayMicroseconds(2); 
        digitalWrite(stepPin, LOW);
      }
    }
  }
  IrReceiver.start();
}

void safeDelay(unsigned long waitTime) {
  unsigned long startTime = millis();
  while (millis() - startTime < waitTime) {
    if (systemRunning) {
      unsigned long currentMicros = micros();
      if (currentMicros - lastStepMicros >= stepSpeed) {
        lastStepMicros = currentMicros;
        digitalWrite(stepPin, HIGH);
        delayMicroseconds(5); 
        digitalWrite(stepPin, LOW);
      }
    }
    if (IrReceiver.decode()) {
      if (IrReceiver.decodedIRData.protocol == NEC && !(IrReceiver.decodedIRData.flags & IRDATA_FLAGS_IS_REPEAT)) {
        uint16_t command = IrReceiver.decodedIRData.command;
        unsigned long currentTime = millis();
        if (currentTime - lastIRTime > 500) {
          if (command == 64) { triggerToggle = true; lastIRTime = currentTime; } 
          else if (command == 69) { triggerScreen = true; lastIRTime = currentTime; }
        }
      }
      IrReceiver.resume();
      if (triggerScreen || triggerToggle) return; 
    }
  }
}

// --- TRIPWIRE DELAY FOR DANCE MODE ---
bool danceDelay(unsigned long waitTime) {
  unsigned long startTime = millis();
  while (millis() - startTime < waitTime) {
    
    // 1. Check for Python Keyboard interrupt ('P' or 'S')
    if (Serial.available() > 0) {
      char c = Serial.peek();
      if (c == 'P') {
        Serial.read(); // Consume the Pause command
        return true;   // Abort the dance!
      } else if (c == 'S') {
        return true;   // Leave 'S' in the buffer to start the belt, but abort dance!
      }
    }
    
    // 2. Check for IR Remote interrupt
    if (IrReceiver.decode()) {
      if (IrReceiver.decodedIRData.protocol == NEC && !(IrReceiver.decodedIRData.flags & IRDATA_FLAGS_IS_REPEAT)) {
        uint16_t command = IrReceiver.decodedIRData.command;
        if (command == 64) { triggerToggle = true; IrReceiver.resume(); return true; } 
        else if (command == 69) { triggerScreen = true; IrReceiver.resume(); return true; }
      }
      IrReceiver.resume();
    }
    delay(1); 
  }
  return false;
}

// --- THE CRAZY DANCE ---
void celebrationDance() {
  bool previousState = systemRunning;
  systemRunning = false; 
  
  if (screenOn) { printRow(0, " * GOING CRAZY *"); printRow(1, "   \\(o_o)/   "); }
  
  // Phase 1: Machine Gun
  for (int i=0; i<6; i++) {
    swatterServo.write(0); playTone(1500, 40); if(danceDelay(60)) goto abortDance;
    swatterServo.write(180); playTone(1000, 40); if(danceDelay(60)) goto abortDance;
  }

  // Phase 2: The Glitch
  if (screenOn) { printRow(1, "  GLITCHING...  "); }
  for (int i=0; i<15; i++) {
    swatterServo.write(random(20, 160));
    playTone(random(400, 2500), 30);
    if(danceDelay(40)) goto abortDance;
  }

  // Phase 3: The Slow Windup
  if (screenOn) { printRow(1, "  WINDING UP!   "); }
  swatterServo.write(SERVO_CLOSED);
  for(int freq = 200; freq <= 2000; freq += 100) {
    playTone(freq, 20);
    if(danceDelay(20)) goto abortDance;
  }

  // Phase 4: The Helicopter
  if (screenOn) { printRow(1, "  HELICOPTER!!  "); }
  for (int i=0; i<5; i++) {
    swatterServo.write(180); if(danceDelay(80)) goto abortDance;
    swatterServo.write(0); if(danceDelay(80)) goto abortDance;
  }
  
  // Bow
  swatterServo.write(SERVO_CLOSED);
  playTone(831, 100); if(danceDelay(50)) goto abortDance;
  playTone(1047, 100); if(danceDelay(50)) goto abortDance;
  playTone(1319, 200);
  
  // End naturally
  while (IrReceiver.decode()) { IrReceiver.resume(); } 
  while (Serial.available() > 0) { Serial.read(); }    
  
  systemRunning = previousState; 
  displayNeedsUpdate = true;
  return;
  
abortDance:
  // --- EMERGENCY STOP TRIGGERED ---
  swatterServo.write(SERVO_CLOSED);
  systemRunning = false; 
  displayNeedsUpdate = true;
  
  if (triggerToggle) {
    triggerToggle = false; 
    playTone(523, 100);
  }
  
  while (IrReceiver.decode()) { IrReceiver.resume(); } 
}