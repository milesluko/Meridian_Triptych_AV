import serial.tools.list_ports
import serial
import time
import random
import threading
import os
import glob
import re
from pathlib import Path

try:
    import mido
except ImportError:
    print("Error: mido not installed. Run: pip install mido")
    exit(1)

try:
    import mutagen
    from mutagen import File as MutagenFile
except ImportError:
    print("Error: mutagen not installed. Run: pip install mutagen")
    exit(1)

BAUD_RATE = 9600
PROXIMITY_THRESHOLD = 100
MIDI_CHANNEL = 0
NUM_TRACKS = 8
DETECTION_COOLDOWN = 5
TRACK_DELAY = 300  # 5 minutes in seconds
MAX_QUEUED_TRACKS = 2
AUDIO_FOLDER = "audio"
EMPTY_QUEUE_TIMEOUT = 1200  # 20 minutes in seconds

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

def create_audio_dictionary(audio_folder=AUDIO_FOLDER):
    audio_dict = {}
    audio_extensions = ('.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a', '.wma')
    
    if not os.path.exists(audio_folder):
        print(f"Warning: Audio folder '{audio_folder}' not found")
        return audio_dict
    
    audio_files = []
    for ext in audio_extensions:
        audio_files.extend(glob.glob(os.path.join(audio_folder, f"*{ext}")))
        audio_files.extend(glob.glob(os.path.join(audio_folder, f"*{ext.upper()}")))
    
    print(f"Found {len(audio_files)} audio files in '{audio_folder}'")
    
    for file_path in audio_files:
        try:
            audio_file = MutagenFile(file_path)
            if audio_file is not None and hasattr(audio_file, 'info'):
                length = audio_file.info.length
                filename = os.path.basename(file_path)
                audio_dict[filename] = length
                print(f"  {filename}: {length:.2f} seconds")
            else:
                print(f"  Warning: Could not read audio info for {os.path.basename(file_path)}")
        except Exception as e:
            print(f"  Error reading {os.path.basename(file_path)}: {e}")
    
    return audio_dict

def select_midi_port():
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
    
    print("\nAvailable MIDI output ports:")
    print("=" * 50)
    for i, port in enumerate(output_ports):
        print(f"  {i}: {port}")
    print("=" * 50)
    
    while True:
        try:
            choice = input(f"\nSelect MIDI port (0-{len(output_ports)-1}): ")
            port_index = int(choice)
            if 0 <= port_index < len(output_ports):
                selected_port = output_ports[port_index]
                print(f"Selected MIDI port: {selected_port}")
                return selected_port
            else:
                print(f"Invalid selection. Please enter a number between 0 and {len(output_ports)-1}")
        except ValueError:
            print("Invalid input. Please enter a number.")
        except KeyboardInterrupt:
            print("\nExiting...")
            return None

class MIDITrackTrigger:
    def __init__(self, midi_channel=0, num_tracks=8, audio_dict=None):
        self.midi_channel = midi_channel
        self.num_tracks = num_tracks
        self.midi_port = None
        self.queued_count = 0
        self.playing_count = 0
        self.lock = threading.Lock()
        self.audio_dict = audio_dict or {}
        self.note_to_file_map = {}
        self.playing_tracks = {}
        self.active_timers = []
        self.last_queue_activity = time.time()
        self.empty_queue_timer = None
        
        self._create_note_mapping()
        
        port_name = select_midi_port()
        if port_name:
            try:
                self.midi_port = mido.open_output(port_name)
                print(f"Connected to MIDI port: {port_name}")
            except Exception as e:
                print(f"Error opening MIDI port {port_name}: {e}")
        else:
            print("No MIDI port available")
        
        # Start empty queue timer since queue starts empty
        self._reset_empty_queue_timer()
    
    def _extract_note_from_filename(self, filename):
        name_without_ext = os.path.splitext(filename)[0]
        match = re.search(r'(\d+)', name_without_ext)
        if match:
            note_num = int(match.group(1))
            if 0 <= note_num <= 127:
                return note_num
        return None
    
    def _create_note_mapping(self):
        if not self.audio_dict:
            print("Warning: No audio files found for MIDI mapping")
            return
        
        mapped_files = []
        unmapped_files = []
        
        for filename in self.audio_dict.keys():
            note = self._extract_note_from_filename(filename)
            if note is not None:
                self.note_to_file_map[note] = filename
                mapped_files.append((note, filename))
                print(f"MIDI Note {note} -> {filename} ({self.audio_dict[filename]:.2f}s)")
            else:
                unmapped_files.append(filename)
                print(f"Warning: Could not extract MIDI note from filename: {filename}")
        
        if mapped_files:
            print(f"Successfully mapped {len(mapped_files)} audio files to MIDI notes")
        
        if unmapped_files:
            print(f"Warning: {len(unmapped_files)} files could not be mapped (no valid note number in filename)")
    
    def queue_random_track(self):
        if not self.midi_port:
            print("No MIDI port available")
            return
        
        if not self.note_to_file_map:
            print("No mapped audio files available for playback")
            return
        
        with self.lock:
            if self.queued_count >= MAX_QUEUED_TRACKS:
                print(f"Queue full ({self.queued_count} tracks queued). Skipping new track.")
                return
            
            self.queued_count += 1
            available_notes = list(self.note_to_file_map.keys())
            track_note = random.choice(available_notes)
            filename = self.note_to_file_map[track_note]
            print(f"Queued {filename} (Note {track_note}) - will play in ({TRACK_DELAY/60}) minutes ({self.queued_count} in queue)")
            
            # Schedule track to play after delay
            timer = threading.Timer(TRACK_DELAY, self._trigger_track, args=[track_note])
            self.active_timers.append(timer)
            timer.start()
            print(f"Timer started for track {track_note}, will trigger in {TRACK_DELAY} seconds")
            
            self.last_queue_activity = time.time()
            self._reset_empty_queue_timer()
    
    def _trigger_track(self, track_note):
        print(f"_trigger_track called for note {track_note}")
        if not self.midi_port:
            print("No MIDI port available")
            with self.lock:
                self.queued_count -= 1
            return
        
        filename = self.note_to_file_map.get(track_note, "Unknown")
        duration = self.audio_dict.get(filename, 0)
        
        with self.lock:
            self.queued_count -= 1
            self.playing_count += 1
            self.playing_tracks[track_note] = {"filename": filename, "start_time": time.time()}
            print(f"Playing scheduled track {track_note} (Note {track_note}) - {filename}")
            print(f"Queue: {self.queued_count} queued, {self.playing_count} playing")
            
            if self.queued_count == 0 and self.playing_count == 1:
                self._reset_empty_queue_timer()
        
        try:
            note_on = mido.Message('note_on', channel=self.midi_channel, note=track_note, velocity=127)
            self.midi_port.send(note_on)
            
            time.sleep(0.1)
            
            note_off = mido.Message('note_off', channel=self.midi_channel, note=track_note, velocity=0)
            self.midi_port.send(note_off)
            
            print(f"MIDI trigger sent for track {track_note} - will finish in {duration:.2f}s")
            
            if duration > 0:
                cleanup_timer = threading.Timer(duration, self._track_finished, args=[track_note])
                cleanup_timer.start()
            
        except Exception as e:
            print(f"MIDI error: {e}")
            with self.lock:
                self.playing_count -= 1
                if track_note in self.playing_tracks:
                    del self.playing_tracks[track_note]
    
    def _track_finished(self, track_note):
        with self.lock:
            if track_note in self.playing_tracks:
                track_info = self.playing_tracks[track_note]
                elapsed = time.time() - track_info["start_time"]
                print(f"Track {track_note - 59} ({track_info['filename']}) finished after {elapsed:.2f}s")
                del self.playing_tracks[track_note]
                self.playing_count -= 1
                print(f"Queue status: {self.queued_count} queued, {self.playing_count} playing")
                
                if self.queued_count == 0 and self.playing_count == 0:
                    self._reset_empty_queue_timer()
    
    def _reset_empty_queue_timer(self):
        if self.empty_queue_timer and self.empty_queue_timer.is_alive():
            self.empty_queue_timer.cancel()
        
        if self.queued_count == 0 and self.playing_count == 0:
            print(f"Queue is empty - setting 20 minute timer for auto-queue")
            self.empty_queue_timer = threading.Timer(EMPTY_QUEUE_TIMEOUT, self._auto_queue_track)
            self.empty_queue_timer.start()
        else:
            self.empty_queue_timer = None
    
    def _auto_queue_track(self):
        with self.lock:
            if self.queued_count == 0 and self.playing_count == 0:
                print("Auto-queuing track after 20 minutes of empty queue")
                self.queue_random_track()
    
    def close(self):
        # Cancel all active timers
        with self.lock:
            for timer in self.active_timers:
                if timer.is_alive():
                    timer.cancel()
                    print(f"Cancelled active timer")
            self.active_timers.clear()
            
            if self.empty_queue_timer and self.empty_queue_timer.is_alive():
                self.empty_queue_timer.cancel()
                print("Cancelled empty queue timer")
        
        if self.midi_port:
            self.midi_port.close()
            print("MIDI port closed")

def main():
    try:
        print("Loading audio file dictionary...")
        audio_dict = create_audio_dictionary()
        print(f"Audio dictionary created with {len(audio_dict)} files\n")
        
        midi_trigger = MIDITrackTrigger(MIDI_CHANNEL, NUM_TRACKS, audio_dict)
        
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
                if data and data.startswith("Distance:"):
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