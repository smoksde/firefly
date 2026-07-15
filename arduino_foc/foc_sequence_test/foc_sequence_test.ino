#include <SimpleFOC.h>

MagneticSensorI2C sensor = MagneticSensorI2C(AS5600_I2C);
BLDCMotor motor = BLDCMotor(7);  // 7 Pole Pairs (14 Poles)
BLDCDriver3PWM driver = BLDCDriver3PWM(25, 26, 27, 14);

float targetAngle = 0.0;
unsigned long lastPrint = 0;

// Sequence variables
unsigned long sequenceTimer = 0;
int sequenceStep = 0;

void setup() {
  Serial.begin(115200);
  Wire.begin(21, 22);

  motor.useMonitoring(Serial);  // SimpleFOC debug output

  sensor.init();
  motor.linkSensor(&sensor);

  driver.voltage_power_supply = 7.4;
  driver.init();
  motor.linkDriver(&driver);

  // Safety & Limits for Gimbal Motors
  motor.voltage_limit = 0.5; // 2.0  // Keep low to prevent overheating
  motor.voltage_sensor_align = 0.5; // optional
  motor.velocity_limit = 10.0;  // Rad/s (Adjust for faster/slower transitions)
  motor.controller = MotionControlType::angle;

  // PID Tuning
  motor.PID_velocity.P = 0.1;
  motor.PID_velocity.I = 1.0;   // Slightly increased for holding precision
  motor.PID_velocity.D = 0.0;
  motor.P_angle.P      = 15.0;  // Slightly higher snappy response

  motor.init();
  motor.initFOC();

  Serial.println("Gimbal Demo Sequence Starting...");
  sequenceTimer = millis();
}

void loop() {
  // CRITICAL: Must be called as frequently as possible for FOC to work
  motor.loopFOC();
  motor.move(targetAngle);

  // --- AUTOMATED GIMBAL DEMO SEQUENCE ---
  // Every step executes after a set duration (in milliseconds)
  if (millis() - sequenceTimer > 2000) { // Change step every 3 seconds
    sequenceTimer = millis();
    sequenceStep++;
    
    float targetDeg = 0.0;

    switch (sequenceStep) {
      case 1:
        targetDeg = 45.0;
        Serial.println("\n[Step 1]: Slow Pan Right (+45°)");
        break;
      case 2:
        targetDeg = -45.0;
        Serial.println("\n[Step 2]: Large Sweep Left (-45°)");
        break;
      case 3:
        targetDeg = 0.0;
        Serial.println("\n[Step 3]: Return to Center (0°)");
        break;
      case 4:
        targetDeg = 90.0;
        Serial.println("\n[Step 4]: Extreme Quick Right (+90°)");
        break;
      case 5:
        targetDeg = 85.0; // Small micro-twitch
        Serial.println("\n[Step 5]: Micro-adjustment (-5° Twitch)");
        break;
      case 6:
        targetDeg = -90.0;
        Serial.println("\n[Step 6]: Full Sweep Left (-90°)");
        break;
      case 7:
        targetDeg = 0.0;
        Serial.println("\n[Step 7]: Centering & Reset (0°)");
        break;
      default:
        // Reset sequence to loop infinitely
        sequenceStep = 0; 
        Serial.println("\n=== Sequence Restarting ===");
        break;
    }

    // Convert degrees to radians for SimpleFOC
    targetAngle = targetDeg * (PI / 180.0);
  }

  // --- TELEMETRY MONITORING ---
  if (millis() - lastPrint > 150) {
    lastPrint = millis();
    float currentDeg = sensor.getAngle() * (180.0 / PI);
    float targetDeg  = targetAngle * (180.0 / PI);
    
    Serial.print("Ist: ");
    Serial.print(currentDeg, 1);
    Serial.print("° | Soll: ");
    Serial.print(targetDeg, 1);
    Serial.print("° | Error: ");
    Serial.print(targetDeg - currentDeg, 1);
    Serial.println("°");
  }
}
