#!/usr/bin/env python3

import time
try:
    import mido
except ImportError:
    print("Error: mido not installed. Run: pip install mido")
    exit(1)

def find_midi_port():
    try:
        output_ports = mido.get_output_names()
    except Exception as e:
        print(f"Error getting MIDI ports: {e}")
        return None
    
    if not output_ports:
        print("No MIDI output ports found")
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

def main():
    port_name = find_midi_port()
    if not port_name:
        print("No MIDI port available")
        return
    
    try:
        midi_port = mido.open_output(port_name)
        print(f"Connected to MIDI port: {port_name}")
        
        note = 1
        channel = 0
        velocity = 127
        
        print(f"Sending MIDI note {note} on channel {channel}")
        
        note_on = mido.Message('note_on', channel=channel, note=note, velocity=velocity)
        midi_port.send(note_on)
        
        time.sleep(0.1)
        
        note_off = mido.Message('note_off', channel=channel, note=note, velocity=0)
        midi_port.send(note_off)
        
        print(f"MIDI note {note} sent successfully")
        
        midi_port.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()