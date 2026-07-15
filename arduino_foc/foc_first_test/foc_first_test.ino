#include <SimpleFOC.h>

MagneticSensorI2C sensor = MagneticSensorI2C(AS5600_I2C);
BLDCMotor motor = BLDCMotor(7);  // 0 = automatisch ermitteln
BLDCDriver3PWM driver = BLDCDriver3PWM(25, 26, 27, 14);

float targetAngle = 0.0;
unsigned long lastPrint = 0;

void setup() {
  Serial.begin(115200);
  Wire.begin(21, 22);

  motor.useMonitoring(Serial);  // SimpleFOC debug output

  sensor.init();
  motor.linkSensor(&sensor);

  driver.voltage_power_supply = 7.4;
  driver.init();
  motor.linkDriver(&driver);

  motor.voltage_limit = 2;
  motor.velocity_limit = 15;
  motor.controller = MotionControlType::angle;

  motor.PID_velocity.P = 0.1;
  motor.PID_velocity.I = 0.4;
  motor.PID_velocity.D = 0.0;
  motor.P_angle.P      = 10.0;

  motor.init();
  motor.initFOC();

  Serial.println("Bereit. Zielwinkel eingeben (z.B. 90 oder -45):");
}

void loop() {
  motor.loopFOC();
  motor.move(targetAngle);

  if (millis() - lastPrint > 200) {
    lastPrint = millis();
    float currentDeg = sensor.getAngle() * (180.0 / PI);
    float targetDeg  = targetAngle * (180.0 / PI);
    Serial.print("Ist: ");
    Serial.print(currentDeg, 1);
    Serial.print("°  |  Soll: ");
    Serial.print(targetDeg, 1);
    Serial.print("°  |  PP: ");
    Serial.println(motor.pole_pairs);
  }

  if (Serial.available()) {
    float input = Serial.parseFloat();
    if (input != 0.0 || Serial.peek() == '\n') {
      targetAngle = input * (PI / 180.0);
      Serial.print("→ Neuer Zielwinkel: ");
      Serial.print(input);
      Serial.println("°");
    }
    while (Serial.available()) Serial.read();
  }
}
