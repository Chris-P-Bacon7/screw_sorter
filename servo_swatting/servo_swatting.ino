// #include <Servo.h>
// #include <LiquidCrystal.h>
// #include <IRremote.hpp> 

// // ==========================================
// // --- 1. HARDWARE PINS ---
// // ==========================================
// const int irReceiverPin = 4; 
// const int servoPin = 3;
// const int ledPin = 13;   
// const int buzzerPin = 5; 

// // Stepper Motor Pins (Analog as Digital)
// const int stepPin = A3;  // Connected to PUL+
// const int dirPin = A2;   // Connected to DIR+

// LiquidCrystal lcd(7, 8, 9, 10, 11, 12);
// Servo swatterServo;

// // ==========================================
// // --- 2. SYSTEM VARIABLES ---
// // ==========================================
// String screwTypes[] = {"Rusted", "Robertson", "Phillips", "Slot", "Hex"};
// bool systemRunning = false;
// bool displayNeedsUpdate = true; 
// bool screenOn = true;

// // Stepper Motor Speed Control
// unsigned long lastStepMicros = 0;
// int stepSpeed = 1000; // Microseconds between steps. Lower = Faster belt!
// const int maxSpeed = 300;  // Fastest safe speed (lowest delay)
// const int minSpeed = 2500; // Slowest safe speed (highest delay)

// // ==========================================
// // --- 3. ACTION TRIGGERS & TIMERS ---
// // ==========================================
// volatile bool triggerToggle = false;
// volatile bool triggerDance = false;
// volatile bool triggerScreen = false;

// char manualIRCommand = '\0';  
// unsigned long lastIRTime = 0;

// void setup() {
//   Serial.begin(9600); 
  
//   pinMode(ledPin, OUTPUT); 
//   pinMode(buzzerPin, OUTPUT); 
  
//   // Setup Stepper Pins
//   pinMode(stepPin, OUTPUT);
//   pinMode(dirPin, OUTPUT);
//   digitalWrite(dirPin, HIGH); // Set initial belt direction to FORWARD
  
//   swatterServo.attach(servoPin);
//   swatterServo.write(90); 
  
//   lcd.begin(16, 2); 
//   IrReceiver.begin(irReceiverPin, DISABLE_LED_FEEDBACK);

//   // Power-on sound (Perfect Ab5!)
//   playTone(831, 150); 
//   triggerToggle = true;
// }

// void loop() {
  
//   // ==========================================
//   // --- STRICT IR REMOTE LOGIC ---
//   // ==========================================
  
//   if (IrReceiver.decode()) {
//     if (IrReceiver.decodedIRData.protocol == NEC && !(IrReceiver.decodedIRData.flags & IRDATA_FLAGS_IS_REPEAT)) {
//       uint16_t command = IrReceiver.decodedIRData.command;
//       unsigned long currentTime = millis();
      
//       if (currentTime - lastIRTime > 300) { // Reduced cooldown to make volume tapping feel responsive
        
//         // --- THE NEW CONTROLS ---
//         if (command == 69) { triggerScreen = true; lastIRTime = currentTime; } // Power Button
//         else if (command == 70) { adjustSpeed(true); lastIRTime = currentTime; } // Vol+ Button (Faster)
//         else if (command == 21) { adjustSpeed(false); lastIRTime = currentTime; } // Vol- Button (Slower)
        
//         // --- EXISTING CONTROLS ---
//         else if (command == 64) { triggerToggle = true; lastIRTime = currentTime; } // Play/Pause
//         else if (command == 71) { 
//           if (systemRunning) { triggerDance = true; lastIRTime = currentTime; }
//         } 
//         else if (systemRunning) {
//           if (command == 22) { manualIRCommand = '0'; lastIRTime = currentTime; } 
//           else if (command == 12) { manualIRCommand = '1'; lastIRTime = currentTime; } 
//           else if (command == 24) { manualIRCommand = '2'; lastIRTime = currentTime; } 
//           else if (command == 94) { manualIRCommand = '3'; lastIRTime = currentTime; } 
//           else if (command == 8)  { manualIRCommand = '4'; lastIRTime = currentTime; } 
//         }
//       }
//     }
//     IrReceiver.resume();
//   }

//   // ==========================================
//   // --- EXECUTING THE ACTIONS ---
//   // ==========================================

//   // NEW: Screen Toggle Logic
//   if (triggerScreen) {
//     triggerScreen = false;
//     screenOn = !screenOn;
    
//     if (screenOn) {
//       lcd.display();
//       playTone(1047, 100); // High chirp on
//     } else {
//       lcd.noDisplay();
//       playTone(523, 100);  // Low chirp off
//     }
//   }

//   if (triggerDance) {
//     triggerDance = false;
//     celebrationDance();
//     displayNeedsUpdate = true;
//   }

//   if (triggerToggle) {
//     triggerToggle = false;
//     systemRunning = !systemRunning;
    
//     playTone(831, 100); // Clean Ab5 for Pause/Play
    
//     if (systemRunning && screenOn) {
//       showLoadingBar("Init...   ");
//     } else if (!systemRunning && screenOn) {
//       showLoadingBar("Pausing...");
//     }
//     displayNeedsUpdate = true;
//   }

//   // ==========================================
//   // --- THE UNIFIED BRAIN ---
//   // ==========================================
  
//   if (systemRunning) {
//     // Non-Blocking Stepper Motor Pulse
//     unsigned long currentMicros = micros();
//     if (currentMicros - lastStepMicros >= stepSpeed) {
//       lastStepMicros = currentMicros;
//       digitalWrite(stepPin, HIGH);
//       delayMicroseconds(5); // Tiny pulse just to trigger the TB6600
//       digitalWrite(stepPin, LOW);
//     }

//     // LCD Update Check
//     if (displayNeedsUpdate && screenOn) {
//       printRow(0, "System: RUNNING");
//       printRow(1, "Awaiting AI/IR");
//       displayNeedsUpdate = false;
//     }

//     char incomingChar = '\0';
//     bool fromCamera = false;
    
//     if (Serial.available() > 0) { 
//       incomingChar = Serial.read(); 
//       fromCamera = true;
//     } 
//     else if (manualIRCommand != '\0') {
//       incomingChar = manualIRCommand;
//       manualIRCommand = '\0'; 
//     }

//     if (incomingChar >= '0' && incomingChar <= '4') {
//       int screwIndex = incomingChar - '0';
//       String detectedScrew = screwTypes[screwIndex];

//       Serial.print("Confirmed! Swatting ");
//       Serial.println(detectedScrew);

//       // Hardware-driven Success "Coin" Sound
//       playTone(1319, 80); // E6
//       delay(20);
//       playTone(2093, 150); // C7

//       if (fromCamera) {
//         digitalWrite(ledPin, HIGH); 
//         delay(150);
//         digitalWrite(ledPin, LOW); 
//       }

//       if (screenOn) printRow(0, "Type: " + detectedScrew);
      
//       // Execute the swat (The belt will safely pause during these animations!)
//       if (detectedScrew == "Rusted") {
//         if (screenOn) printRow(1, "Act: FAST +90");
//         swatFast(180);
//       } else if (detectedScrew == "Robertson") {
//         if (screenOn) printRow(1, "Act: FAST -90");
//         swatFast(0);
//       } else if (detectedScrew == "Phillips") {
//         if (screenOn) printRow(1, "Act: SLOW +90");
//         sweepSlow(180);
//       } else {
//         if (screenOn) printRow(1, "Act: SLOW -90");
//         sweepSlow(0);
//       }
      
//       delay(400);
      
//       if (systemRunning) {
//         sweepSlow(90); 
//         delay(200);
//         displayNeedsUpdate = true;
//       }

//       while (IrReceiver.decode()) { IrReceiver.resume(); }
//       lastIRTime = millis();
      
//       while (Serial.available() > 0) { Serial.read(); }
//     }
//   } else {
//     // PAUSED STATE
//     if (displayNeedsUpdate && screenOn) {
//       swatterServo.write(90);
//       printRow(0, "System: PAUSED");
//       printRow(1, "Awaiting Remote");
//       displayNeedsUpdate = false;
//     }
//     while (Serial.available() > 0) { Serial.read(); }
//   }
// }

// // ==========================================
// // --- REUSABLE UI & PHYSICS FUNCTIONS ---
// // ==========================================

// // NEW: Live Speed Adjustment Function
// void adjustSpeed(bool faster) {
//   if (faster) {
//     stepSpeed -= 150; // Decrease delay = go faster
//     if (stepSpeed < maxSpeed) stepSpeed = maxSpeed;
//   } else {
//     stepSpeed += 150; // Increase delay = go slower
//     if (stepSpeed > minSpeed) stepSpeed = minSpeed;
//   }
  
//   playTone(1568, 50); // Little blip sound
  
//   if (screenOn) {
//     lcd.clear();
//     printRow(0, "BELT SPEED:");
    
//     // Map the raw microseconds to a friendly 1-10 scale for the screen
//     int displayLevel = map(stepSpeed, minSpeed, maxSpeed, 1, 15);
//     printRow(1, "Level: " + String(displayLevel));
    
//     delay(500); // Briefly show the speed
//     displayNeedsUpdate = true; // Tell the loop to redraw the main menu
//   }
// }

// void printRow(int row, String text) {
//   lcd.setCursor(0, row);
//   lcd.print(text);
//   for (unsigned int i = text.length(); i < 16; i++) { lcd.print(" "); }
// }

// void showLoadingBar(String label) {
//   lcd.clear();
//   for (int i = 0; i <= 16; i++) {
//     if (IrReceiver.decode()) { IrReceiver.resume(); } 
//     int percent = (i * 100) / 16;
//     lcd.setCursor(0, 0);
//     lcd.print(label);
//     if (percent < 100) lcd.print(" ");
//     if (percent < 10) lcd.print(" ");
//     lcd.print(percent);
//     lcd.print("%");
    
//     lcd.setCursor(0, 1);
//     for (int j = 0; j < i; j++) lcd.write(255); 
    
//     delay(random(10, 50));
//   }
// }

// void swatFast(int targetAngle) {
//   if (targetAngle == 180) { swatterServo.write(70); delay(250); swatterServo.write(180); } 
//   else { swatterServo.write(110); delay(250); swatterServo.write(0); }
// }

// void sweepSlow(int targetAngle) {
//   if (targetAngle == 180) { swatterServo.write(60); delay(350); } 
//   else if (targetAngle == 0) { swatterServo.write(120); delay(350); }

//   int currentAngle = swatterServo.read();
//   if (targetAngle > currentAngle) {
//     for (int pos = currentAngle; pos <= targetAngle; pos++) { swatterServo.write(pos); delay(4); }
//   } else {
//     for (int pos = currentAngle; pos >= targetAngle; pos--) { swatterServo.write(pos); delay(4); }
//   }
// }

// void safeDelay(unsigned long waitTime) {
//   unsigned long startTime = millis();
//   while (millis() - startTime < waitTime) {
//     if (IrReceiver.decode()) {
//       if (IrReceiver.decodedIRData.protocol == NEC && !(IrReceiver.decodedIRData.flags & IRDATA_FLAGS_IS_REPEAT)) {
//         uint16_t command = IrReceiver.decodedIRData.command;
//         unsigned long currentTime = millis();
//         if (currentTime - lastIRTime > 500) {
//           if (command == 64) { triggerToggle = true; lastIRTime = currentTime; } 
//           else if (command == 69) { triggerScreen = true; lastIRTime = currentTime; }
//         }
//       }
//       IrReceiver.resume();
//       if (triggerScreen || triggerToggle) return; 
//     }
//     delay(1);
//   }
// }

// // ==========================================
// // --- THE DISTORTION-FREE SOUND ENGINE ---
// // ==========================================
// void playTone(int frequency, int durationMs) {
//   IrReceiver.stop(); 
//   long halfPeriod = 1000000L / frequency / 2;
//   long numCycles = (long)frequency * durationMs / 1000L;
  
//   for (long i = 0; i < numCycles; i++) {
//     digitalWrite(buzzerPin, HIGH);
//     delayMicroseconds(halfPeriod);
//     digitalWrite(buzzerPin, LOW);
//     delayMicroseconds(halfPeriod);
//   }
//   IrReceiver.start();
// }

// // ==========================================
// // --- THE DANCE CHOREOGRAPHY ---
// // ==========================================
// void celebrationDance() {
//   if (screenOn) {
//     printRow(0, "1. Stretching...");
//     printRow(1, "");
//   }
//   for(int pos = 90; pos <= 160; pos++) { swatterServo.write(pos); safeDelay(12); if(triggerScreen || triggerToggle) { swatterServo.write(90); return; } }
//   for(int pos = 160; pos >= 20; pos--) { swatterServo.write(pos); safeDelay(12); if(triggerScreen || triggerToggle) { swatterServo.write(90); return; } }
//   for(int pos = 20; pos <= 90; pos++)  { swatterServo.write(pos); safeDelay(12); if(triggerScreen || triggerToggle) { swatterServo.write(90); return; } }

//   if (screenOn) printRow(0, "2. The Jitter!");
//   for(int i = 0; i < 15; i++) { 
//     swatterServo.write(75);
//     playTone(1568, 60); 
//     swatterServo.write(105);
//     playTone(1319, 60); 
//   }
  
//   while (IrReceiver.decode()) { IrReceiver.resume(); }

//   if (screenOn) printRow(0, "3. Windmill!!");
//   for(int i = 0; i < 4; i++) { 
//     swatterServo.write(0); safeDelay(300); if(triggerScreen || triggerToggle) { swatterServo.write(90); return; }
//     swatterServo.write(180); safeDelay(300); if(triggerScreen || triggerToggle) { swatterServo.write(90); return; }
//   }

//   if (screenOn) printRow(0, "   * Bows * ");
//   swatterServo.write(90); 
  
//   playTone(831, 100); delay(50);
//   playTone(1047, 100); delay(50); 
//   playTone(1319, 200); 
  
//   while (IrReceiver.decode()) { IrReceiver.resume(); }
//   lastIRTime = millis();
  
//   safeDelay(1500); 

const int stepPin = A2; 
const int dirPin = A1;  

void setup() {
  pinMode(stepPin, OUTPUT);
  pinMode(dirPin, OUTPUT);
}

void loop() {
  digitalWrite(dirPin, HIGH); // Forward
  
  // Send an ULTRA SLOW pulse
  digitalWrite(stepPin, HIGH);
  delay(20); // 20 FULL milliseconds (Very slow, high torque)
  digitalWrite(stepPin, LOW);
  delay(20); 
}