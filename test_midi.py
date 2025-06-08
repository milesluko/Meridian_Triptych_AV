#!/usr/bin/env python3

import time
try:
    import mido
except ImportError:
    print("Error: mido not installed. Run: pip install mido")
    exit(1)

def select_midi_port():
    try:
        output_ports = mido.get_output_names()
    except Exception as e:
        print(f"Error getting MIDI ports: {e}")
        return None
    
    if not output_ports:
        print("No MIDI output ports found")
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

def main():
    port_name = select_midi_port()
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