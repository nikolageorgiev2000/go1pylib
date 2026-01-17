"""
Simple beat-synced head bobbing script.
Makes the robot bob its head in sync with music beats.
"""

import asyncio
import time
import librosa
import sounddevice as sd
from go1pylib import Go1, Go1Mode


async def main():
    # Load and analyze music
    print("Loading music file...")
    audio_file = "beat_routine/up_town_funk.wav"
    y, sr = librosa.load(audio_file)
    
    print("Detecting beats...")
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    
    print(f"Tempo: {tempo[0]:.1f} BPM")
    print(f"Detected {len(beat_times)} beats")
    
    # Initialize robot
    print("Connecting to robot...")
    dog = Go1()
    dog.init()
    
    # Wait for connection
    start_time = time.time()
    while not dog.mqtt.connected and (time.time() - start_time < 10):
        await asyncio.sleep(0.1)
    
    if not dog.mqtt.connected:
        print("Failed to connect")
        return
    
    print("Connected!")
    
    # Set to stand mode
    dog.set_mode(Go1Mode.STAND)
    await asyncio.sleep(2)
    
    print("Starting in 3 seconds...")
    await asyncio.sleep(3)
    
    # Play music in separate thread
    print("Playing music and bobbing head every 16 beats!")
    sd.play(y, sr)
    
    start_time = time.time()
    
    try:
        for i, beat_time in enumerate(beat_times):
            # Only process every 16th beat
            if i % 16 != 0:
                continue
            
            # Wait until this beat time
            current_time = time.time() - start_time
            wait_time = beat_time - current_time
            
            if wait_time > 0:
                await asyncio.sleep(wait_time)
            
            # Bob head
            print(f"Bobbing on beat {i}...")
            await dog.look_down(speed=1.0, duration_ms=100)
            await dog.look_up(speed=0.8, duration_ms=100)
    
    except KeyboardInterrupt:
        print("Stopped by user")
    finally:
        sd.stop()
        await dog.reset_body()
        dog.set_mode(Go1Mode.WALK)
        dog.mqtt.disconnect()
        print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
