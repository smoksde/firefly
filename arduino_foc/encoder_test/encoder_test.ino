#include <Wire.h>

#define AS5600_ADDR 0x36
#define RAW_ANGLE_H 0x0C
#define RAW_ANGLE_L 0x0D
#define STATUS_REG  0x0B

void setup() {
  Serial.begin(115200);
  Wire.begin(21, 22); // SDA, SCL
  delay(500);
  Serial.println("AS5600 Encoder Test");
}

int readReg(uint8_t reg) {
  Wire.beginTransmission(AS5600_ADDR);
  Wire.write(reg);
  Wire.endTransmission(false);
  Wire.requestFrom(AS5600_ADDR, 1);
  return Wire.available() ? Wire.read() : -1;
}

void loop() {
  // Verbindung prüfen
  Wire.beginTransmission(AS5600_ADDR);
  bool found = (Wire.endTransmission() == 0);

  if (!found) {
    Serial.println("ERROR: AS5600 nicht gefunden (0x36)!");
    delay(1000);
    return;
  }

  // Status auslesen
  int status = readReg(STATUS_REG);
  bool magnetTooWeak   = status & (1 << 5);
  bool magnetTooStrong = status & (1 << 4);
  bool magnetDetected  = status & (1 << 3);

  // Roher Winkel (12-bit, 0–4095)
  int high = readReg(RAW_ANGLE_H);
  int low  = readReg(RAW_ANGLE_L);
  int raw  = ((high & 0x0F) << 8) | low;

  // In Grad umrechnen
  float degrees = raw * 360.0 / 4096.0;

  // Ausgabe
  Serial.print("Magnet: ");
  if      (!magnetDetected)  Serial.print("NICHT ERKANNT ⚠️  ");
  else if (magnetTooWeak)    Serial.print("zu schwach ⚠️    ");
  else if (magnetTooStrong)  Serial.print("zu stark ⚠️     ");
  else                       Serial.print("OK ✓             ");

  Serial.print(" | Raw: ");
  Serial.print(raw);
  Serial.print(" | Winkel: ");
  Serial.print(degrees, 1);
  Serial.println("°");

  delay(100);
}
