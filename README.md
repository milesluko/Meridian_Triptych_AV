# Meridian Triptych AV

A proximity-triggered MIDI audio system that detects when people approach an ultrasonic sensor and triggers audio tracks in Reaper via MIDI.

## System Overview

This system consists of:
- **Arduino with HC-SR04 ultrasonic sensor** - detects proximity
- **Python script** - processes sensor data and sends MIDI triggers
- **Reaper DAW** - receives MIDI notes and plays corresponding audio tracks

## Hardware Setup

### HC-SR04 Ultrasonic Sensor Wiring

Connect the HC-SR04 sensor to your Arduino as follows:

```
HC-SR04 Sensor     Arduino
┌─────────────┐    ┌─────────────┐
│    VCC      │───▶│     5V      │
│    GND      │───▶│    GND      │
│    Trig     │───▶│  Digital 2  │
│    Echo     │───▶│  Digital 10 │
└─────────────┘    └─────────────┘
```

## Software Setup

### Requirements

1. **Arduino IDE** - to upload the sensor code
2. **Python 3.7+** - to run the MIDI trigger script
3. **Reaper DAW** - to receive MIDI and play audio

### Installation

1. Clone this repository
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Upload the Arduino sketch:
   - Open `hc_sr04_distance/hc_sr04_distance.ino` in Arduino IDE
   - Upload to your Arduino board

### Audio File Setup

1. Create an `audio` folder in the project directory
2. Add your audio files with note numbers in the filename:
   - `60.wav` → MIDI note 60
   - `track_72.mp3` → MIDI note 72
   - `ambient_64_loop.flac` → MIDI note 64

The system automatically maps the first number found in each filename to its corresponding MIDI note.

### Running the System

1. Connect your Arduino via USB
2. Open Reaper and set up MIDI input
3. Run the Python script:
   ```bash
   python receive_distance.py
   ```

The system will:
- Load audio files and create a duration dictionary
- Connect to Arduino and MIDI output
- Monitor for proximity detection
- Queue tracks with 5-minute delay when triggered
- Send MIDI notes to Reaper
- Automatically clear tracks from queue when playback finishes

### Configuration

Key settings in `receive_distance.py`:
- `PROXIMITY_THRESHOLD = 100` - Detection distance in cm
- `TRACK_DELAY = 300` - Delay before playing (5 minutes)
- `MAX_QUEUED_TRACKS = 2` - Maximum tracks in queue
- `DETECTION_COOLDOWN = 5` - Seconds between detections
