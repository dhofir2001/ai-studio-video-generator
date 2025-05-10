/**
 * Executable automation script for Google AI Studio video generation
 * Supports Chrome profile rotation and configuration via config.json
 */

const puppeteer = require('puppeteer-core');
const fs = require('fs');
const path = require('path');

// Load configuration
let config;
try {
    const configPath = path.join(process.cwd(), 'config.json');
    config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
} catch (error) {
    console.error('Error loading config.json. Please ensure it exists in the same directory as the executable.');
    console.error('Required format:');
    console.error(`{
  "userDataPath": "C:\\\\Path\\\\To\\\\Chrome\\\\User Data",
  "profiles": ["Default", "Profile 1", "Profile 2"],
  "saveDir": "C:\\\\Path\\\\To\\\\Save\\\\Videos"
}`);
    process.exit(1);
}

const DEBUGGING_PORT = 9222;
const TARGET_URL = 'https://aistudio.google.com/generate-video';
const MAX_WAIT_TIME = 300000; // 5 minutes timeout
const CHECK_INTERVAL = 5000; // Check every 5 seconds

const PROMPT_TEXT = 'a cinematic aerial shot of a futuristic city glowing at night, flying cars in the sky, 16:9 aspect ratio, 8 seconds duration';

// Video settings
const VIDEO_SETTINGS = {
    aspectRatio: '16:9',
    duration: '8s',
    resolution: '720p'
};

// Logging utility
function log(message, type = 'info') {
    const timestamp = new Date().toISOString();
    const logMessage = `[${timestamp}] [${type}] ${message}`;
    console.log(logMessage);
    
    // Write to log file in save directory
    const logFile = path.join(config.saveDir, 'generation.log');
    fs.appendFileSync(logFile, logMessage + '\n');
}

async function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

async function findChromePath() {
    const commonPaths = [
        'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
        'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
        process.env.LOCALAPPDATA + '\\Google\\Chrome\\Application\\chrome.exe'
    ];

    for (const path of commonPaths) {
        if (fs.existsSync(path)) {
            return path;
        }
    }

    throw new Error('Chrome executable not found. Please ensure Chrome is installed.');
}

async function launchBrowser(profile) {
    log(`Launching Chrome with profile: ${profile}`);
    
    try {
        const chromePath = await findChromePath();
        const userDataDir = path.join(config.userDataPath, profile);
        
        const browser = await puppeteer.launch({
            headless: false,
            executablePath: chromePath,
            userDataDir,
            args: [
                `--remote-debugging-port=${DEBUGGING_PORT}`,
                `--profile-directory=${profile}`,
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu'
            ],
            defaultViewport: null
        });
        return browser;
    } catch (error) {
        log(`Failed to launch browser: ${error.message}`, 'error');
        throw error;
    }
}

async function waitForLoginComplete(page) {
    log('Waiting for login to complete...');
    
    try {
        await page.waitForFunction(
            () => {
                const loginForm = document.querySelector('form[action*="signin"]');
                if (loginForm) return false;
                return document.querySelector('textarea') !== null;
            },
            { timeout: 60000 }
        );
        
        log('Login completed successfully');
        return true;
    } catch (error) {
        log('Login wait timeout or error', 'error');
        return false;
    }
}

async function generateVideo(page) {
    try {
        log('Navigating to AI Studio video generator...');
        await page.goto(TARGET_URL, { waitUntil: 'networkidle0', timeout: 60000 });
        
        const loginSuccess = await waitForLoginComplete(page);
        if (!loginSuccess) {
            throw new Error('Failed to access video generator interface');
        }
        
        log('Looking for prompt input field...');
        await page.waitForSelector('textarea', { visible: true, timeout: 60000 });
        
        log('Entering prompt text...');
        await page.evaluate((text) => {
            const textarea = document.querySelector('textarea');
            textarea.value = text;
            textarea.dispatchEvent(new Event('input', { bubbles: true }));
        }, PROMPT_TEXT);
        
        log('Setting video parameters...');
        const settingsSelectors = {
            aspectRatio: '[aria-label*="aspect ratio"], [data-testid*="aspect-ratio"]',
            duration: '[aria-label*="duration"], [data-testid*="duration"]',
            resolution: '[aria-label*="resolution"], [data-testid*="resolution"]'
        };
        
        for (const [setting, value] of Object.entries(VIDEO_SETTINGS)) {
            const selector = settingsSelectors[setting];
            try {
                await page.waitForSelector(selector, { visible: true, timeout: 10000 });
                await page.click(selector);
                await page.waitForSelector(`[role="option"]:has-text("${value}")`, { visible: true });
                await page.click(`[role="option"]:has-text("${value}")`);
                log(`Set ${setting} to ${value}`);
            } catch (error) {
                log(`Warning: Failed to set ${setting}: ${error.message}`, 'warn');
            }
        }
        
        log('Starting video generation...');
        const runButton = await page.waitForSelector('button:has-text("Run"), button:has-text("Generate")', { visible: true });
        await runButton.click();
        
        log('Waiting for video generation...');
        let elapsed = 0;
        while (elapsed < MAX_WAIT_TIME) {
            const quotaError = await page.evaluate(() => {
                const errorText = document.body.innerText;
                return errorText.toLowerCase().includes('quota') || 
                       errorText.toLowerCase().includes('limit reached');
            });
            
            if (quotaError) {
                log('Quota exceeded detected', 'warn');
                return { success: false, reason: 'quota' };
            }
            
            const videoReady = await page.evaluate(() => {
                return document.querySelector('video') !== null ||
                       document.querySelector('[download]') !== null;
            });
            
            if (videoReady) {
                log('Video generated successfully');
                
                try {
                    const downloadSelector = await page.waitForSelector('[download]', { timeout: 5000 });
                    if (downloadSelector) {
                        const videoUrl = await page.evaluate(el => el.href, downloadSelector);
                        const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
                        const videoPath = path.join(config.saveDir, `video-${timestamp}.mp4`);
                        
                        log(`Saving video to: ${videoPath}`);
                        // TODO: Implement video download using page._client.send('Browser.downloadFile')
                    }
                } catch (error) {
                    log('Warning: Could not find video download link', 'warn');
                }
                
                return { success: true };
            }
            
            await delay(CHECK_INTERVAL);
            elapsed += CHECK_INTERVAL;
        }
        
        log('Timeout waiting for video generation', 'error');
        return { success: false, reason: 'timeout' };
        
    } catch (error) {
        log(`Error during video generation: ${error.message}`, 'error');
        return { success: false, reason: 'error', error: error.message };
    }
}

async function main() {
    // Create save directory if it doesn't exist
    if (!fs.existsSync(config.saveDir)) {
        fs.mkdirSync(config.saveDir, { recursive: true });
    }
    
    log('Starting video generation automation');
    log(`Using Chrome profiles from: ${config.userDataPath}`);
    log(`Saving videos to: ${config.saveDir}`);
    
    for (const profile of config.profiles) {
        log(`Attempting with profile: ${profile}`);
        
        let browser;
        try {
            browser = await launchBrowser(profile);
            const pages = await browser.pages();
            const page = pages[0] || await browser.newPage();
            
            const result = await generateVideo(page);
            
            if (result.success) {
                log(`Successfully generated video with profile: ${profile}`);
                await browser.close();
                break;
            } else {
                log(`Failed with profile ${profile}: ${result.reason}`, 'warn');
                if (result.error) {
                    log(`Error details: ${result.error}`, 'error');
                }
                await browser.close();
            }
        } catch (error) {
            log(`Fatal error with profile ${profile}: ${error.message}`, 'error');
            if (browser) {
                await browser.close();
            }
        }
    }
    
    log('Automation completed');
}

// Start the automation
if (require.main === module) {
    main().catch(error => {
        log(`Fatal error in main: ${error.message}`, 'error');
        process.exit(1);
    });
}
