#include <SimpleFOC.h>

MagneticSensorI2C sensor = MagneticSensorI2C(AS5600_I2C);
BLDCMotor motor = BLDCMotor(7);  // 7 Pole Pairs (14 Poles)
BLDCDriver3PWM driver = BLDCDriver3PWM(25, 26, 27, 14);

float targetAngle = 0.0;
unsigned long lastPrint = 0;

// --- TEACH & REPLAY STATE MACHINE ---
enum State { IDLE, RECORDING, PLAYBACK };
State currentState = IDLE;

unsigned long sampleTimer = 0;
const int SAMPLE_RATE_MS = 100; // Sample every 100ms
const int MAX_SAMPLES = 100;    // Up to 10 seconds of recording space
float recordedAngles[MAX_SAMPLES];
int recordIndex = 0;
int playbackIndex = 0;

void setup() {
  Serial.begin(115200);
  Wire.begin(21, 22);

  motor.useMonitoring(Serial);

  sensor.init();
  motor.linkSensor(&sensor);

  driver.voltage_power_supply = 7.4;
  driver.init();
  motor.linkDriver(&driver);

  // Default closed-loop safety limits for normal operations
  motor.voltage_limit = 0.5;         
  motor.voltage_sensor_align = 0.5;  
  motor.velocity_limit = 10.0;       
  motor.controller = MotionControlType::angle;

  // PID Tuning
  motor.PID_velocity.P = 0.1;
  motor.PID_velocity.I = 1.0;   
  motor.PID_velocity.D = 0.0;
  motor.P_angle.P      = 15.0;  

  // This step calibrates the motor alignment. It needs power to do this!
  motor.init();
  motor.initFOC();

  targetAngle = sensor.getAngle(); // Hold current startup position

  Serial.println("\n==============================================");
  Serial.println("System Ready!");
  Serial.println("Type 't' and press Enter to start TEACH MODE");
  Serial.println("Type 's' and press Enter to STOP and PLAYBACK");
  Serial.println("==============================================");
}

void loop() {
  // CRITICAL: Always run FOC tracking
  motor.loopFOC();

  // Check for Console Inputs
  if (Serial.available() > 0) {
    char input = Serial.read();
    
    // Ignore stray newline/carriage return characters
    if (input == 't' || input == 'T') {
      if (currentState != RECORDING) {
        Serial.println("\n>>> TEACH MODE ACTIVE. Motor relaxed. Move it by hand! <<<");
        recordIndex = 0;
        // Kill voltage completely so you can easily turn it by hand
        motor.voltage_limit = 0.0;
        motor.controller = MotionControlType::velocity_openloop;
        currentState = RECORDING;
        sampleTimer = millis();
      }
    } 
    else if (input == 's' || input == 'S') {
      if (currentState == RECORDING) {
        Serial.print("\n>>> STOPPING RECORD. Total samples captured: ");
        Serial.println(recordIndex);
        
        if (recordIndex > 0) {
          Serial.println(">>> SWITCHING TO PLAYBACK. Safety limits on! <<<");
          // Restore safety limits and re-engage angle mode
          motor.voltage_limit = 0.5; 
          motor.controller = MotionControlType::angle;
          
          playbackIndex = 0;
          targetAngle = recordedAngles[playbackIndex]; // Set first frame
          currentState = PLAYBACK;
        } else {
          Serial.println("Error: No data recorded. Try again.");
          motor.voltage_limit = 0.5;
          motor.controller = MotionControlType::angle;
          currentState = IDLE;
        }
        sampleTimer = millis();
      }
    }
  }

  // --- STATE MACHINE RUNTIME ---
  if (currentState == RECORDING) {
    motor.move(); // Does nothing because voltage_limit is 0.0

    // Record positions sequentially
    if (millis() - sampleTimer >= SAMPLE_RATE_MS) {
      sampleTimer = millis();
      
      if (recordIndex < MAX_SAMPLES) {
        recordedAngles[recordIndex] = sensor.getAngle();
        recordIndex++;
        // Visual indicator that recording is active
        Serial.print("."); 
      } else {
        Serial.println("\nMemory full! Type 's' to play back what you have.");
      }
    }
  } 
  else if (currentState == PLAYBACK) {
    motor.move(targetAngle);

    // Frame-by-frame loop execution
    if (millis() - sampleTimer >= SAMPLE_RATE_MS) {
      sampleTimer = millis();
      
      targetAngle = recordedAngles[playbackIndex];
      
      playbackIndex++;
      if (playbackIndex >= recordIndex) {
        playbackIndex = 0; // Loop seamlessly
        Serial.println("\n[Playback]: Restarting loop...");
      }
    }
  } 
  else {
    // IDLE state (holds startup position safely)
    motor.move(targetAngle);
  }

  // --- TELEMETRY MONITORING ---
  if (millis() - lastPrint > 200) {
    lastPrint = millis();
    if (currentState == PLAYBACK) {
      float currentDeg = sensor.getAngle() * (180.0 / PI);
      float targetDeg  = targetAngle * (180.0 / PI);
      Serial.print("Ist: ");
      Serial.print(currentDeg, 1);
      Serial.print("° | Soll: ");
      Serial.print(targetDeg, 1);
      Serial.print("° | Error: ");
      Serial.println((targetDeg - currentDeg), 1);
    }
  }
}
