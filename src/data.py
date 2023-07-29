import json
import os
import time
import wave
from typing import List, Tuple

import numpy as np
import sounddevice as sd
from pydub import AudioSegment
from pydub.silence import detect_silence
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

CHROME = 1
FIREFOX = 2
EDGE = 3

DEFAULT_OUT_SAMPLE_RATE = 44100
DEFAULT_OUT_ID = 0
DEFAULT_OUT_CHANNELS = 1

TEST_PHRASES = [
    (1, "test phrase 1"),
    (2, "test phrase 2")
]


class DrSbaitsoAudioCollector:
    def __init__(self, browser: int):
        self.set_driver(browser)
        self.is_recording = False
        self.recorded_data = []
        try:
            with open('device.json') as f:
                device_info = json.load(f)
                self.output_device_id = device_info["ID"]
                self.output_device_samplerate = device_info["Samplerate"]
                self.output_device_channels = device_info["Channels"]
        except FileNotFoundError:
            # Current Default Output Device
            devices = sd.query_devices()
            default_output_device = next((device for device in devices if device['default_output']), None)
            if default_output_device is not None:
                self.output_device_id = default_output_device['id']
                self.output_device_samplerate = default_output_device['default_samplerate']
                self.output_device_channels = default_output_device['max_output_channels']
            else:
                # No Default Output Device Found?
                self.output_device_id = DEFAULT_OUT_ID
                self.output_device_samplerate = DEFAULT_OUT_SAMPLE_RATE
                self.output_device_channels = DEFAULT_OUT_CHANNELS
            
    def set_driver(self, browser: int):
        if browser == CHROME:
            from selenium.webdriver.chrome.options import Options
            options = Options()
            webdriver_instance = webdriver.Chrome
        elif browser == FIREFOX:
            from selenium.webdriver.firefox.options import Options
            options = Options()
            options.set_preference('detach', True)
            webdriver_instance = webdriver.Firefox
        elif browser == EDGE:
            from selenium.webdriver.edge.options import Options
            options = Options()
            webdriver_instance = webdriver.Edge
        else:
            raise WebDriverException('Invalid browser: choose from CHROME, FIREFOX, or EDGE.')

        options.add_argument('--log-level=3')
        if browser != FIREFOX:
            options.add_experimental_option('detach', True)
        else:
            options.set_preference('detach', True)
            
        self.driver = webdriver_instance(options=options)


    def callback(self, indata, frames, time, status):
        if self.is_recording:
            self.recorded_data.extend(indata.tolist())
    
    def start_recording(self):
        self.is_recording = True
        self.recorded_data = []
        self.stream = sd.InputStream(callback=self.callback, device=self.output_device_id, samplerate=self.output_device_samplerate)
        self.stream.start()
    
    def check_silence(self, audio_file: str):
        audio = AudioSegment.from_file(audio_file, format="wav")
        silence = detect_silence(audio[-1000:], min_silence_len=500, silence_thresh=-16)
        return len(silence) > 0
    
    def stop_recording(self):
        self.stream.stop()
        self.stream.close()
        self.is_recording = False
    
    def save_recording(self, filename: str):
        filename = f'recordings/{filename}.wav'
        np_data = np.array(self.recorded_data, dtype='float32')
        num_channels = 2
        samplerate = self.output_device_samplerate
        data = np_data * (2**15 - 1)  # scale to int16 range
        data = data.astype(np.int16)
        with wave.open(filename, 'w') as f:
            f.setnchannels(num_channels)
            f.setsampwidth(2)  # int16 => 2 bytes
            f.setframerate(samplerate)
            f.writeframes(data.tostring())
    
    def produce_audio(self, phrases: List[Tuple]):
        self.driver.get('https://classicreload.com/dr-sbaitso.html')
        print("""
Welcome to the audio producer for SCP-079's voice.

In the selenium driver window, please procede to load DR SBAITSO.
Once loaded, do .param and enter 0544.

This will modify the voice of DR SBAITSO to be more like SCP-079's voice.
Make sure to do test out this voice before continuing to prevent audio glitches upon first run.

After this is done, enter anything here to continue: """, end="")
        input()

        os.makedirs('recordings', exist_ok=True)
        body = self.driver.find_element(By.XPATH, "//body")
        for phrase_id, phrase in TEST_PHRASES:
            body.send_keys('say ' + phrase)
            self.start_recording()
            body.send_keys(Keys.ENTER)
            time.sleep(1)  # wait for TTS to start
            while True:
                time.sleep(1)  # wait for a chunk of audio
                filename = f'{phrase_id}'
                self.save_recording(filename)
                if self.check_silence(f'recordings/{filename}.wav'):
                    break
            self.stop_recording()

