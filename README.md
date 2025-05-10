# AI Studio Video Generator

A Python GUI application for automating video generation on Google AI Studio with Chrome profile support.

## Features

- User-friendly GUI interface
- Chrome profile selection and rotation
- Configurable paths and settings
- Real-time logging
- Automatic video saving
- Quota management

## Requirements

- Python 3.7 or higher
- Chrome browser (version below 136)
- Google account logged into Chrome profiles

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
python video_generator.py
```

## Configuration

1. In the application GUI:
   - Set Chrome executable path
   - Set Chrome user data directory path
   - Set video save directory
   - Select Chrome profile

2. The settings will be saved automatically in `config.json`

## Usage

1. Configure paths and profile in the GUI
2. Click "Start Generation" to begin
3. Monitor progress in the log window
4. Videos will be saved to the specified directory
5. Use "Stop" button to halt generation

## Video Generation Settings

- Prompt: "a cinematic aerial shot of a futuristic city glowing at night, flying cars in the sky, 16:9 aspect ratio, 8 seconds duration"
- Aspect Ratio: 16:9
- Duration: 8s
- Resolution: 720p

## Notes

- Ensure Chrome profiles are already logged into Google
- The application will detect quota limits and notify you
- Check the log window for real-time status updates
- Generated videos are saved with timestamps
