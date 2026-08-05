# Zabbix Monitoring Automation Bot

An automation project for Zabbix monitoring and notification integration.

## 📁 Main File Structure
* `Mon_Zabbix.py` - Main script for Zabbix monitoring.
* `wa_server.js` - A Node.js server for handling WhatsApp messages and notifications.
* `run_all.bat` - A batch file to automatically run all services at once.

## ⚙️ Installation & Execution

1. **Clone this repository to your local computer:**
   ```bash
   git clone [https://github.com/gariramadhan/automation-zabbix.git](https://github.com/gariramadhan/automation-zabbix.git)
   cd automation-zabbix

2. Configure the Environment (.env)
Create a file named .env inside this project folder, then customize its contents using the following format:
Running the Program:
# Zabbix Configuration
ZABBIX_URL=https://your-zabbix-server-url/api_jsonrpc.php
ZABBIX_USER=your_username
ZABBIX_PASSWORD=your_password

# Other Configurations (if any)
PORT=3000

3. Install Python Dependencies
Make sure Python is already installed, then install the required libraries by running this command in the terminal:

- pip install requests zabbix-utils python-dotenv
(Adjust the list of libraries above if your project uses other additional modules).

4. Install Node.js Dependencies & Chromium
This project requires Node.js for the WhatsApp server. Run this command inside the project folder:
- npm install
(Also make sure Chromium / Google Chrome is installed on your computer for browser automation needs, if required).


### 5. Install Playwright & Browser Binaries
If your script requires Playwright, run:
```bash
- pip install playwright
- playwright install

🚀 Running the Program
Once all configurations and dependencies are installed, you can run the entire program by:

- run_all.bat



   
