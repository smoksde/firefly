#include <SimpleFOC.h>

// --- MOTOR 1 (Existing) ---
MagneticSensorI2C sensor1 = MagneticSensorI2C(AS5600_I2C);
BLDCMotor motor1 = BLDCMotor(7);
BLDCDriver3PWM driver1 = BLDCDriver3PWM(25, 26, 27, 14);

// --- MOTOR 2 (New) ---
MagneticSensorI2C sensor2 = MagneticSensorI2C(AS5600_I2C); 
BLDCMotor motor2 = BLDCMotor(7); 
BLDCDriver3PWM driver2 = BLDCDriver3PWM(32, 33, 23, 5); 

float targetAngle1 = 0.0;
float targetAngle2 = 0.0;
unsigned long lastPrint = 0;
unsigned long moveTimer = 0;
bool movingRight = true;

// Variables for loop timing analysis
unsigned long loopCount = 0;
unsigned long lastLoopTimeCheck = 0;
float averageLoopTimeUs = 0.0;

void setup() {
  // Ultra-high-speed baud rate
  Serial.begin(921600);
  
  // Initialize both I2C buses
  Wire.begin(21, 22);      // Bus 0 for Sensor 1
  Wire1.begin(19, 18);     // Bus 1 for Sensor 2

  Wire.setClock(800000);  // Boost Bus 0 to 800kHz
  Wire1.setClock(800000); // Boost Bus 1 to 800kHz

  motor1.useMonitoring(Serial);
  motor2.useMonitoring(Serial);

  // Initialize Sensor & Motor 1
  sensor1.init(&Wire); 
  motor1.linkSensor(&sensor1);
  driver1.voltage_power_supply = 7.4;
  driver1.init();
  motor1.linkDriver(&driver1);

  // Initialize Sensor & Motor 2
  sensor2.init(&Wire1); 
  motor2.linkSensor(&sensor2);
  driver2.voltage_power_supply = 7.4; 
  driver2.init();
  motor2.linkDriver(&driver2);

  // Limits & Tuning for Motor 1
  motor1.voltage_limit = 0.8;
  motor1.voltage_sensor_align = 0.5;
  motor1.velocity_limit = 10.0;
  motor1.controller = MotionControlType::angle;
  motor1.PID_velocity.P = 0.1;
  motor1.PID_velocity.I = 1.0;
  motor1.P_angle.P      = 15.0;

  // Limits & Tuning for Motor 2 (Mirroring Motor 1)
  motor2.voltage_limit = 0.8;
  motor2.voltage_sensor_align = 0.5;
  motor2.velocity_limit = 10.0;
  motor2.controller = MotionControlType::angle;
  motor2.PID_velocity.P = 0.1;
  motor2.PID_velocity.I = 1.0;
  motor2.P_angle.P      = 15.0;

  // Init both motors
  motor1.init();
  motor1.initFOC();
  
  motor2.init();
  motor2.initFOC();

  // The Ultimate CSV Header (11 Columns)
  Serial.println("time_ms,loop_us,target1,angle1,v_target1,vel1,vq1,target2,angle2,v_target2,vel2,vq2");

  targetAngle1 = 45.0 * (PI / 180.0);
  targetAngle2 = -45.0 * (PI / 180.0); 
  moveTimer = millis();
  lastLoopTimeCheck = micros();
}

void loop() {
  unsigned long loopStart = micros();

  // Run FOC calculations
  motor1.loopFOC();
  motor2.loopFOC();

  // Run motion control calculations
  motor1.move(targetAngle1);
  motor2.move(targetAngle2);

  // Calculate execution time for just this iteration
  unsigned long currentLoopTime = micros() - loopStart;
  
  // Keep a running average of the loop execution time
  loopCount++;
  averageLoopTimeUs += (currentLoopTime - averageLoopTimeUs) / loopCount;

  // --- AUTOMATED OSCILLATION ---
  if (millis() - moveTimer > 2000) { 
    moveTimer = millis();
    if (movingRight) {
      targetAngle1 = -45.0 * (PI / 180.0);
      targetAngle2 = 45.0 * (PI / 180.0);  
      movingRight = false;
    } else {
      targetAngle1 = 45.0 * (PI / 180.0);
      targetAngle2 = -45.0 * (PI / 180.0);
      movingRight = true;
    }
  }

  // --- TELEMETRY (10ms interval / 100Hz) ---
  if (millis() - lastPrint >= 10) {
    lastPrint = millis();

    // Motor 1 Variables
    float t1 = targetAngle1 * (180.0 / PI);
    float a1 = sensor1.getAngle() * (180.0 / PI);
    float vt1 = motor1.shaft_velocity_sp * (180.0 / PI); // What the angle controller *wants* the speed to be
    float v1 = sensor1.getVelocity() * (180.0 / PI);   // What the speed actually is
    float vq1 = motor1.voltage.q;                      // Applied control effort

    // Motor 2 Variables
    float t2 = targetAngle2 * (180.0 / PI);
    float a2 = sensor2.getAngle() * (180.0 / PI);
    float vt2 = motor2.shaft_velocity_sp * (180.0 / PI); 
    float v2 = sensor2.getVelocity() * (180.0 / PI);   
    float vq2 = motor2.voltage.q;                      

    // Output all 12 columns
    Serial.print(lastPrint);
    Serial.print(",");
    Serial.print(averageLoopTimeUs, 1); // Microseconds spent per loop
    Serial.print(",");
    Serial.print(t1, 1);
    Serial.print(",");
    Serial.print(a1, 2);
    Serial.print(",");
    Serial.print(vt1, 1);
    Serial.print(",");
    Serial.print(v1, 1);
    Serial.print(",");
    Serial.print(vq1, 3);
    Serial.print(",");
    Serial.print(t2, 1);
    Serial.print(",");
    Serial.print(a2, 2);
    Serial.print(",");
    Serial.print(vt2, 1);
    Serial.print(",");
    Serial.print(v2, 1);
    Serial.print(",");
    Serial.println(vq2, 3);

    // Reset loop time averaging tracker
    loopCount = 0;
    averageLoopTimeUs = 0;
  }
}
