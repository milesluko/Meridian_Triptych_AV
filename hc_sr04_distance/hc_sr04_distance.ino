// HC-SR04 Ultrasonic Distance Sensor
// Pins
const int trigPin = 2;
const int echoPin = 10;

// Variables
long duration;
int distance;

void setup() {
  // Initialize serial communication
  Serial.begin(9600);
  
  // Set pin modes
  pinMode(trigPin, OUTPUT);
  pinMode(echoPin, INPUT);
  
  Serial.println("HC-SR04 Distance Sensor Ready");
}

void loop() {
  // Clear the trigPin
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  
  // Trigger the sensor by setting trigPin HIGH for 10 microseconds
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);
  
  // Read the echoPin, returns the sound wave travel time in microseconds
  duration = pulseIn(echoPin, HIGH);
  
  // Calculate the distance (duration/2 because sound travels to object and back)
  // Speed of sound is 343 m/s or 0.0343 cm/microsecond
  distance = duration * 0.0343 / 2;
  
  // Send distance over serial
  Serial.print("Distance: ");
  Serial.print(distance);
  Serial.println(" cm");
  
  // Wait before next measurement
  delay(500);
}