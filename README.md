# UCI Luxe East Side Gallery (Berlin) — IMAX OmU Booking Monitor & Notifier

Automated booking monitor and real-time notifier in Python to track showings of Christopher Nolan's **"The Odyssey" (Die Odyssee)** at **UCI Luxe East Side Gallery, Berlin**.

Catches newly scheduled sessions or released inventory in **IMAX** with **original audio and German subtitles (OmU)** and alerts immediately via push notifications on [ntfy.sh](https://ntfy.sh), native desktop banners, and console outputs.

---

## Target Specifications

| Specification | Setting / Filter |
| :--- | :--- |
| **Target Cinema** | UCI Luxe East Side Gallery, Berlin (Site ID `82`) |
| **Movie Title** | Christopher Nolan's *"The Odyssey"* / *"Die Odyssee"* (Film ID `407923`) |
| **Required Format** | **IMAX** AND **OmU** (Original version with subtitles) |
| **Excluded Formats** | Standard 2D, iSense, German-dubbed sessions (without OmU), and plain OV (without OmU) |
| **Schedule Target URL** | `https://www.uci-kinowelt.de/kinoprogramm/berlin-east-side-gallery` |
| **Direct Film URL** | `https://www.uci-kinowelt.de/film/die-odyssee/407923/berlin-east-side-gallery/82` |
| **Push Notification** | `ntfy.sh` (custom topic with direct 1-tap booking action buttons) |

---

## Features

- **Zero External Dependencies**: Built 100% with Python's standard library (`urllib.request`, `html.parser`, `dataclasses`, `json`, `re`, `argparse`, `logging`). Compatible with Python 3.10 through 3.14+.
- **Strict Format Filtering**: Isolates `IMAX` + `OmU` performances while strictly rejecting German dubs, iSense, plain OV, and standard 2D.
- **Instant Push Alerts with Actions**: Delivers `ntfy.sh` push notifications equipped with 1-tap direct booking URLs (`https://buchung.uci-kinowelt.de/?perf_id=...&site_id=82`).
- **State Persistence & Drop Detection**: Maintains `monitor_state.json` to remember previously observed sessions and immediately alert only when new sessions or inventory drop.
- **Native Desktop Notifications**: Integrated macOS (`osascript`) notification banners with sound.
- **Offline / Simulation Mode**: Supports parsing local HTML dumps (`--file sample_page.html`) for testing and offline verification.
- **Resilient Network Fetching**: Built-in exponential backoff, browser header spoofing, and automatic fallback to direct film pages.

---

## Installation & Quickstart

### 1. Requirements
- Python 3.10+ (tested on Python 3.14.3)
- No `pip install` required!

### 2. Verify with Dry Run
Inspect what sessions are currently active without sending alerts or writing state:
```bash
# Check against live cinema schedule:
python3 main.py --once --dry-run

# Or test against local sample file:
python3 main.py --file sample_page.html --once --dry-run
```

### 3. Test Push Notifications (ntfy.sh)
Choose a unique topic name (e.g., `uci-odyssey-yourname`) and send a test notification:
```bash
python3 main.py --test-notify --ntfy-topic uci-odyssey-yourname
```
To receive push notifications on your phone or computer:
- **Mobile (iOS / Android)**: Download the free **ntfy** app and subscribe to your topic name (`uci-odyssey-yourname`).
- **Browser**: Open `https://ntfy.sh/uci-odyssey-yourname` in any browser and click **Subscribe**.

### 4. Start Continuous Monitoring
Start the monitor polling every 5 minutes (300 seconds) in the background:
```bash
python3 main.py --ntfy-topic uci-odyssey-yourname --interval 300
```

---

## Command-Line Usage

```
usage: main.py [-h] [--config CONFIG] [--url URL] [--film-url FILM_URL]
               [--file FILE] [--ntfy-topic NTFY_TOPIC]
               [--ntfy-server NTFY_SERVER] [--interval INTERVAL] [--once]
               [--dry-run] [--notify-existing] [--test-notify] [--reset-state]
               [--no-desktop] [--verbose]
```

### Options Breakdown

| Flag | Description |
| :--- | :--- |
| `--once` | Run a single check cycle and exit immediately. |
| `--dry-run` | Parse and print matching sessions without saving state or sending alerts. |
| `--file PATH` | Read from a local HTML dump (e.g. `sample_page.html`) instead of network. |
| `--ntfy-topic TOPIC` | The ntfy.sh topic to publish push notifications to. |
| `--ntfy-server URL` | Custom ntfy server URL (default: `https://ntfy.sh`). |
| `--interval SEC` | Polling interval in seconds (default: `300`). |
| `--notify-existing` | Send alerts immediately for all currently matching sessions on startup. |
| `--test-notify` | Dispatch a test notification to verify ntfy and desktop setup, then exit. |
| `--reset-state` | Clear `monitor_state.json` and exit. |
| `--no-desktop` | Disable native desktop notification banners. |
| `--verbose`, `-v` | Enable detailed debug logging. |
| `--config PATH` | Load options from a custom JSON config file. |

---

## Configuration via File or Environment

You can copy `config.json.example` to `config.json`:
```bash
cp config.json.example config.json
```

Or configure via environment variables:
```bash
export NTFY_TOPIC="uci-odyssey-yourname"
export UCI_POLL_INTERVAL=180
export UCI_NOTIFY_EXISTING=0
python3 main.py
```

---

## 24/7 Cloud Monitoring via GitHub Actions (Free, No Laptop Needed)

A pre-configured GitHub Actions workflow is included at [`.github/workflows/monitor.yml`](.github/workflows/monitor.yml). It runs on GitHub's cloud runners every 10 minutes, checks for new sessions, saves state, and sends push notifications to your phone—**with your laptop completely off**.

### Setup Steps:
1. **Create a Private GitHub Repository**:
   - Go to [github.com/new](https://github.com/new) and create a **Private** repository (e.g. `uci-odyssey-monitor`).
2. **Push This Code**:
   ```bash
   git add .
   git commit -m "Setup 24/7 UCI Luxe cinema monitor"
   git branch -M main
   git remote add origin https://github.com/<your-username>/uci-odyssey-monitor.git
   git push -u origin main
   ```
3. **Enable Workflow Permissions**:
   - In your GitHub repo, go to **Settings → Actions → General**.
   - Under **Workflow permissions**, select **Read and write permissions** (so the action can save `monitor_state.json`), then click **Save**.
4. **(Optional) Set Custom Topic Secret**:
   - Go to **Settings → Secrets and variables → Actions**.
   - Add a repository secret named `NTFY_TOPIC` with your chosen topic (e.g., `my-secret-topic-99`).
   - If not set, it defaults to `uci-luxe-odyssey-imax`.
5. **Receive Alerts**:
   - Open `https://ntfy.sh/<your-topic>` on your phone or install the free **ntfy** app (iOS/Android) and subscribe to `<your-topic>`.

---

## Running Locally on macOS
Create `~/Library/LaunchAgents/com.uci.odyssey.monitor.plist`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.uci.odyssey.monitor</string>
    <key>ProgramArguments</key>
    <array>
        <string>/opt/homebrew/bin/python3</string>
        <string>/Users/MAC/Documents/antigravity/resilient-pasteur/main.py</string>
        <string>--ntfy-topic</string>
        <string>uci-odyssey-yourname</string>
        <string>--interval</string>
        <string>300</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/uci_monitor.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/uci_monitor_err.log</string>
</dict>
</plist>
```
Load with:
```bash
launchctl load ~/Library/LaunchAgents/com.uci.odyssey.monitor.plist
```

---

## Running Automated Tests

Run the full unit test suite:
```bash
python3 -m unittest discover -s tests -p "test_*.py" -v
```

All 18 unit tests validate:
- HTML parsing of cinema and film pages.
- Strict format filter rules (`IMAX + OmU` matching, `German dub`, `OV`, `iSense`, and `2D` rejection).
- State persistence and session drop detection.
- `ntfy.sh` push payload construction and action headers.
