import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
import json
import os
import sys
import time
import logging
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

class VideoGeneratorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Studio Video Generator")
        self.root.geometry("800x600")
        
        # Variables
        self.chrome_path = tk.StringVar()
        self.user_data_path = tk.StringVar()
        self.save_dir = tk.StringVar()
        self.current_profile = tk.StringVar(value="Default")
        self.is_running = False
        self.driver = None
        
        # Configure logging
        self.setup_logging()
        
        # Create GUI
        self.create_gui()
        
        # Load config if exists
        self.load_config()

    def setup_logging(self):
        self.log_queue = []
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

    def create_gui(self):
        # Create main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Path configuration section
        path_frame = ttk.LabelFrame(main_frame, text="Configuration", padding="5")
        path_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # Chrome path
        ttk.Label(path_frame, text="Chrome Path:").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(path_frame, textvariable=self.chrome_path, width=50).grid(row=0, column=1, padx=5)
        ttk.Button(path_frame, text="Browse", command=lambda: self.browse_path("chrome")).grid(row=0, column=2)
        
        # User data path
        ttk.Label(path_frame, text="User Data Path:").grid(row=1, column=0, sticky=tk.W)
        ttk.Entry(path_frame, textvariable=self.user_data_path, width=50).grid(row=1, column=1, padx=5)
        ttk.Button(path_frame, text="Browse", command=lambda: self.browse_path("userdata")).grid(row=1, column=2)
        
        # Save directory
        ttk.Label(path_frame, text="Save Directory:").grid(row=2, column=0, sticky=tk.W)
        ttk.Entry(path_frame, textvariable=self.save_dir, width=50).grid(row=2, column=1, padx=5)
        ttk.Button(path_frame, text="Browse", command=lambda: self.browse_path("save")).grid(row=2, column=2)
        
        # Profile selection
        ttk.Label(path_frame, text="Profile:").grid(row=3, column=0, sticky=tk.W)
        self.profile_combo = ttk.Combobox(path_frame, textvariable=self.current_profile)
        self.profile_combo['values'] = ['Default', 'Profile 1', 'Profile 2']
        self.profile_combo.grid(row=3, column=1, sticky=tk.W, padx=5)
        
        # Control buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=1, column=0, columnspan=2, pady=10)
        
        self.start_button = ttk.Button(button_frame, text="Start Generation", command=self.start_generation)
        self.start_button.grid(row=0, column=0, padx=5)
        
        self.stop_button = ttk.Button(button_frame, text="Stop", command=self.stop_generation, state=tk.DISABLED)
        self.stop_button.grid(row=0, column=1, padx=5)
        
        ttk.Button(button_frame, text="Save Config", command=self.save_config).grid(row=0, column=2, padx=5)
        
        # Log area
        log_frame = ttk.LabelFrame(main_frame, text="Logs", padding="5")
        log_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        self.log_area = scrolledtext.ScrolledText(log_frame, height=15, width=80)
        self.log_area.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(0, weight=1)

    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] [{level}] {message}"
        self.log_area.insert(tk.END, log_message + "\n")
        self.log_area.see(tk.END)
        logging.info(message)

    def browse_path(self, path_type):
        if path_type == "chrome":
            path = filedialog.askopenfilename(
                title="Select Chrome Executable",
                filetypes=[("Executable files", "*.exe")]
            )
            if path:
                self.chrome_path.set(path)
        elif path_type == "userdata":
            path = filedialog.askdirectory(title="Select Chrome User Data Directory")
            if path:
                self.user_data_path.set(path)
        elif path_type == "save":
            path = filedialog.askdirectory(title="Select Save Directory")
            if path:
                self.save_dir.set(path)

    def save_config(self):
        config = {
            "chrome_path": self.chrome_path.get(),
            "user_data_path": self.user_data_path.get(),
            "save_dir": self.save_dir.get(),
            "profiles": list(self.profile_combo['values'])
        }
        
        try:
            with open("config.json", "w") as f:
                json.dump(config, f, indent=4)
            self.log("Configuration saved successfully")
        except Exception as e:
            self.log(f"Error saving configuration: {str(e)}", "ERROR")

    def load_config(self):
        try:
            with open("config.json", "r") as f:
                config = json.load(f)
                self.chrome_path.set(config.get("chrome_path", ""))
                self.user_data_path.set(config.get("user_data_path", ""))
                self.save_dir.set(config.get("save_dir", ""))
                if "profiles" in config:
                    self.profile_combo['values'] = config["profiles"]
            self.log("Configuration loaded successfully")
        except FileNotFoundError:
            self.log("No configuration file found, using defaults")
        except Exception as e:
            self.log(f"Error loading configuration: {str(e)}", "ERROR")

    def start_generation(self):
        if not self.validate_paths():
            return
        
        self.is_running = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.log("Starting video generation...")
        
        try:
            self.setup_chrome()
            self.generate_video()
        except Exception as e:
            self.log(f"Error during generation: {str(e)}", "ERROR")
            self.stop_generation()

    def validate_paths(self):
        if not os.path.exists(self.chrome_path.get()):
            self.log("Chrome executable not found", "ERROR")
            return False
        if not os.path.exists(self.user_data_path.get()):
            self.log("User data directory not found", "ERROR")
            return False
        if not os.path.exists(self.save_dir.get()):
            try:
                os.makedirs(self.save_dir.get())
            except Exception as e:
                self.log(f"Cannot create save directory: {str(e)}", "ERROR")
                return False
        return True

    def setup_chrome(self):
        options = webdriver.ChromeOptions()
        options.add_argument(f'--user-data-dir={self.user_data_path.get()}')
        options.add_argument(f'--profile-directory={self.current_profile.get()}')
        options.add_argument('--remote-debugging-port=9222')
        options.add_argument('--no-sandbox')
        options.binary_location = self.chrome_path.get()
        
        self.driver = webdriver.Chrome(options=options)
        self.log("Chrome launched successfully")

    def generate_video(self):
        try:
            self.driver.get("https://aistudio.google.com/generate-video")
            self.log("Navigating to AI Studio...")
            
            # Wait for textarea
            textarea = WebDriverWait(self.driver, 60).until(
                EC.presence_of_element_located((By.TAG_NAME, "textarea"))
            )
            
            # Input prompt
            prompt = "a cinematic aerial shot of a futuristic city glowing at night, flying cars in the sky, 16:9 aspect ratio, 8 seconds duration"
            textarea.send_keys(prompt)
            self.log("Entered prompt text")
            
            # Set video parameters (implement based on actual UI elements)
            self.set_video_parameters()
            
            # Click generate button
            generate_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Run') or contains(text(), 'Generate')]")
            generate_button.click()
            self.log("Started video generation")
            
            # Wait for result
            self.wait_for_generation()
            
        except TimeoutException:
            self.log("Timeout waiting for page elements", "ERROR")
        except WebDriverException as e:
            self.log(f"Chrome error: {str(e)}", "ERROR")
        except Exception as e:
            self.log(f"Unexpected error: {str(e)}", "ERROR")

    def set_video_parameters(self):
        try:
            # Set aspect ratio
            self.click_and_select_option("aspect ratio", "16:9")
            
            # Set duration
            self.click_and_select_option("duration", "8s")
            
            # Set resolution
            self.click_and_select_option("resolution", "720p")
            
            self.log("Video parameters set successfully")
        except Exception as e:
            self.log(f"Error setting video parameters: {str(e)}", "ERROR")

    def click_and_select_option(self, parameter_name, value):
        # Wait for and click parameter button
        button = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, f"//button[contains(@aria-label, '{parameter_name}')]"))
        )
        button.click()
        
        # Wait for and click option
        option = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, f"//li[@role='option'][contains(text(), '{value}')]"))
        )
        option.click()

    def wait_for_generation(self):
        max_wait = 300  # 5 minutes
        check_interval = 5
        elapsed = 0
        
        while elapsed < max_wait and self.is_running:
            try:
                # Check for quota error
                quota_error = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'quota') or contains(text(), 'limit reached')]")
                if quota_error:
                    self.log("Quota exceeded, try another profile", "WARNING")
                    break
                
                # Check for video
                video = self.driver.find_elements(By.TAG_NAME, "video")
                if video:
                    self.log("Video generated successfully")
                    self.save_video()
                    break
                
            except Exception as e:
                self.log(f"Error checking generation status: {str(e)}", "ERROR")
            
            time.sleep(check_interval)
            elapsed += check_interval
            
        if elapsed >= max_wait:
            self.log("Timeout waiting for video generation", "ERROR")

    def save_video(self):
        try:
            # Look for download button/link
            download_link = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[download]"))
            )
            
            video_url = download_link.get_attribute("href")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_path = os.path.join(self.save_dir.get(), f"video_{timestamp}.mp4")
            
            # TODO: Implement video download
            self.log(f"Video will be saved to: {save_path}")
            
        except Exception as e:
            self.log(f"Error saving video: {str(e)}", "ERROR")

    def stop_generation(self):
        self.is_running = False
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
        
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.log("Generation stopped")

if __name__ == "__main__":
    root = tk.Tk()
    app = VideoGeneratorGUI(root)
    root.mainloop()
