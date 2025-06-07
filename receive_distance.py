import serial.tools.list_ports
import serial
import time
import random
import threading

try:
    import mido
except ImportError:
    print("Error: mido not installed. Run: pip install mido")
    exit(1)

BAUD_RATE = 9600
PROXIMITY_THRESHOLD = 100
MIDI_CHANNEL = 0
NUM_TRACKS = 8
DETECTION_COOLDOWN = 5
TRACK_DELAY = 300  # 5 minutes in seconds
MAX_QUEUED_TRACKS = 2

def find_arduino_port():
    ports = serial.tools.list_ports.comports()
    
    for port in ports:
        if any(keyword in port.description.lower() for keyword in ['arduino', 'ch340', 'cp2102', 'ftdi']):
            return port.device
        
        if port.vid and port.pid:
            if (port.vid == 0x2341 and port.pid in [0x0043, 0x0001]) or \
               (port.vid == 0x1A86 and port.pid == 0x7523) or \
               (port.vid == 0x10C4 and port.pid == 0xEA60):
                return port.device
        
        device = port.device.lower()
        if any(pattern in device for pattern in ['usbmodem', 'usbserial', 'ttyusb', 'ttyacm']):
            return port.device
    
    return None

def find_midi_port():
    try:
        output_ports = mido.get_output_names()
    except Exception as e:
        print(f"Error getting MIDI ports: {e}")
        print("Try installing python-rtmidi: pip install python-rtmidi")
        return None
    
    if not output_ports:
        print("No MIDI output ports found")
        print("Make sure you have MIDI software running (like Reaper) or virtual MIDI ports set up")
        return None
    
    print("Available MIDI output ports:")
    for i, port in enumerate(output_ports):
        print(f"  {i}: {port}")
    
    preferred_ports = ['reaper', 'daw', 'virtual', 'midi']
    
    for port in output_ports:
        if any(pref in port.lower() for pref in preferred_ports):
            print(f"Using MIDI port: {port}")
            return port
    
    selected_port = output_ports[0]
    print(f"Using first available MIDI port: {selected_port}")
    return selected_port

class MIDITrackTrigger:
    def __init__(self, midi_channel=0, num_tracks=8):
        self.midi_channel = midi_channel
        self.num_tracks = num_tracks
        self.midi_port = None
        self.queued_count = 0
        self.lock = threading.Lock()
        
        port_name = find_midi_port()
        if port_name:
            try:
                self.midi_port = mido.open_output(port_name)
                print(f"Connected to MIDI port: {port_name}")
            except Exception as e:
                print(f"Error opening MIDI port {port_name}: {e}")
        else:
            print("No MIDI port available")
    
    def queue_random_track(self):
        if not self.midi_port:
            print("No MIDI port available")
            return
        
        with self.lock:
            if self.queued_count > MAX_QUEUED_TRACKS:
                print(f"Queue full ({self.queued_count} tracks queued). Skipping new track.")
                return
            
            self.queued_count += 1
            track_note = 60 + random.randint(0, self.num_tracks - 1)
            print(f"Queued track {track_note - 59} (Note {track_note}) - will play in 5 minutes ({self.queued_count} in queue)")
            
            # Schedule track to play after delay
            timer = threading.Timer(TRACK_DELAY, self._trigger_track, args=[track_note])
            timer.start()
    
    def _trigger_track(self, track_note):
        if not self.midi_port:
            print("No MIDI port available")
            return
        
        with self.lock:
            self.queued_count -= 1
            print(f"Playing scheduled track {track_note - 59} (Note {track_note}) - {self.queued_count} remaining in queue")
        
        try:
            note_on = mido.Message('note_on', channel=self.midi_channel, note=track_note, velocity=127)
            self.midi_port.send(note_on)
            
            time.sleep(0.1)
            
            note_off = mido.Message('note_off', channel=self.midi_channel, note=track_note, velocity=0)
            self.midi_port.send(note_off)
            
            print(f"MIDI trigger sent for track {track_note - 59}")
            
        except Exception as e:
            print(f"MIDI error: {e}")
    
    def close(self):
        if self.midi_port:
            self.midi_port.close()
            print("MIDI port closed")

def main():
    try:
        midi_trigger = MIDITrackTrigger(MIDI_CHANNEL, NUM_TRACKS)
        
        serial_port = find_arduino_port()
        if not serial_port:
            print("Error: No Arduino found on any serial port.")
            print("Please check that the Arduino is connected and try again.")
            return
        
        arduino = serial.Serial(serial_port, BAUD_RATE, timeout=1)
        print(f"Connected to Arduino on {serial_port}")
        
        time.sleep(2)
        
        person_detected = False
        last_detection_time = 0
        
        print(f"Monitoring for proximity within {PROXIMITY_THRESHOLD} cm...")
        
        while True:
            if arduino.in_waiting > 0:
                data = arduino.readline().decode('utf-8').strip()
                if data:
                    print(data)
                    
                    if data.startswith("Distance:"):
                        try:
                            distance_str = data.split(":")[1].strip().replace(" cm", "")
                            distance = float(distance_str)
                            current_time = time.time()
                            
                            if distance <= PROXIMITY_THRESHOLD:
                                if not person_detected and (current_time - last_detection_time) > DETECTION_COOLDOWN:
                                    person_detected = True
                                    last_detection_time = current_time
                                    print(f"PROXIMITY DETECTED! Person within {distance} cm - Queuing MIDI track")
                                    midi_trigger.queue_random_track()
                            else:
                                if person_detected:
                                    person_detected = False
                                    print("Person moved away from sensor")
                            
                        except (ValueError, IndexError):
                            pass
            
            time.sleep(0.1)
            
    except serial.SerialException as e:
        print(f"Error: Could not connect to Arduino. {e}")
        print("Check that the Arduino is connected and the port is correct.")
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        if 'arduino' in locals():
            arduino.close()
        if 'midi_trigger' in locals():
            midi_trigger.close()

if __name__ == "__main__":
    main()