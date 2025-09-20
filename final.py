# Combined Script: dish_scraper.py and generate_html_guide.py

# --- IMPORTS (Combined from both files) ---
import requests
import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from datetime import datetime, timedelta, date, timezone
import html

# ==============================================================================
# --- PART 1: DISH TV SCRAPER CODE (from dish_scraper.py) ---
# ==============================================================================

# --- SCRAPER CONFIGURATION ---
desired_channels = [
    "&prive HD",
    "&flix HD",
    "MNX",
    "Sony Pix",
    "Movies Now",
    "Star Movies",
    "Romedy Now",
    "MN+",
    "Star Movies Select HD"
]

# --- SCRAPER FUNCTIONS ---
def get_fresh_credentials():
    """
    Uses Selenium to open the Dish TV guide page and grab fresh credentials.
    (This function is MODIFIED to work on GitHub Actions)
    """
    print("🤖 Starting automated browser to get fresh credentials...")
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=chrome_options)
    
    auth_token = None
    cookie_string = ""

    try:
        driver.get("https://www.dishtv.in/channel-guide.html")
        print("   Page loaded, waiting for token generation...")
        time.sleep(10) 
        
        token_cookie = driver.get_cookie('channelguidetoken')
        if token_cookie:
            auth_token = token_cookie['value']
            print("   ✅ Authorization token found!")
        else:
            print("   ❌ Could not find 'channelguidetoken' cookie.")
            return None, None

        all_cookies = driver.get_cookies()
        cookie_string = "; ".join([f"{cookie['name']}={cookie['value']}" for cookie in all_cookies])
        print("   ✅ Session cookies captured!")

    except Exception as e:
        print(f"   Error during browser automation: {e}")
        return None, None
    finally:
        driver.quit()
        print("   Browser closed.")
    
    return auth_token, cookie_string


def fetch_tv_guide(auth_token, cookie_string, target_date_str):
    """
    Uses the fresh credentials to fetch the entire TV guide for a specific date.
    """
    REQUEST_URL = "https://www.dishtv.in/services/epg/channels"
    
    headers = {
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.9',
        'authorization-token': auth_token,
        'origin': 'https://www.dishtv.in',
        'referer': 'https://www.dishtv.in/channel-guide.html',
        'user-agent': 'Mozilla/5.0 (Linux; Android 13; SM-G981B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Mobile Safari/537.36',
        'cookie': cookie_string
    }
    
    all_channels = []
    total_pages = 1

    try:
        print(f"\n📡 Fetching page 1 for {target_date_str} to get total page count...")
        form_data_page_1 = {
            'channelgenre': '', 'language': '', 'allowPastEvents': 'true',
            'dataSize': 'large', 'pageNum': '1', 'date': target_date_str
        }
        response = requests.post(REQUEST_URL, headers=headers, files=form_data_page_1, timeout=20)

        if response.status_code == 200:
            data = response.json()
            total_pages = int(data.get('totalPages', 1))
            print(f"✅ Success! Total pages found: {total_pages}")
            
            page_1_channels = data.get('programDetailsByChannel', [])
            all_channels.extend(page_1_channels)
            print(f"   Collected {len(page_1_channels)} channels from page 1.")
        else:
            print(f"Error fetching page 1: {response.status_code}")
            print(response.text)
            return None, None

        for page_num in range(2, total_pages + 1):
            print(f"Fetching page {page_num} of {total_pages}...")
            form_data_current_page = form_data_page_1.copy()
            form_data_current_page['pageNum'] = str(page_num)
            
            try:
                response = requests.post(REQUEST_URL, headers=headers, files=form_data_current_page, timeout=20)
                if response.status_code == 200:
                    data = response.json()
                    new_channels = data.get('programDetailsByChannel', [])
                    all_channels.extend(new_channels)
                    print(f"   Collected {len(new_channels)} channels. Total so far: {len(all_channels)}")
                else:
                    print(f"   Could not fetch page {page_num}. Status: {response.status_code}")
                time.sleep(0.5)
            except Exception as e:
                print(f"   An error occurred on page {page_num}: {e}")
        
        return all_channels, total_pages

    except Exception as e:
        print(f"A critical error occurred during fetching: {e}")
        return None, None

def print_guide(all_channels, day_label):
    if not all_channels:
        print(f"No channel data was fetched for {day_label}.")
        return

    print("\n" + "=" * 60)
    print(f"📺 TV GUIDE SCHEDULE FOR {day_label.upper()} (Filtered for your channels)")
    print("=" * 60)
    
    channels_printed = 0
    for channel in all_channels:
        channel_name = channel.get('channelname', 'Unknown Channel')
        
        channels_printed += 1
        print(f"\n- {channel_name}")
        
        if 'programs' in channel and channel['programs']:
            for program in channel['programs']:
                program_name = program.get('title', 'Unknown Program')
                start_time_str = program.get('start', '')
                end_time_str = program.get('stop', '')
                start_time = start_time_str[11:16] if start_time_str else ''
                end_time = end_time_str[11:16] if end_time_str else ''
                time_display = f"{start_time} - {end_time}" if start_time and end_time else "Live"
                print(f"  ⏰ {time_display}: {program_name}")
        else:
            print("  No program information available.")
    
    if channels_printed == 0:
        print("\nNone of your desired channels were found in the schedule for this day.")

# ==============================================================================
# --- PART 2: HTML GUIDE GENERATOR CODE (from generate_html_guide.py) ---
# ==============================================================================

def create_timeline_guide():
    desired_channels = [
        "&prive HD", "&flix HD", "MNX", "Sony Pix", "Movies Now",
        "Star Movies", "Romedy Now", "MN+", "Star Movies Select HD"
    ]
    JSON_INPUT_FILE = 'tv_guide_today_and_tomorrow.json'
    HTML_OUTPUT_FILE = 'index.html' # <<< YOUR FIX IS INCLUDED HERE

    def parse_assumed_local_time(time_str):
        return datetime.fromisoformat(time_str[:-1])

    print("\n" + "=" * 60)
    print("--- Starting HTML Guide Generation (v6.1 Timestamp Fix) ---")

    try:
        with open(JSON_INPUT_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        all_channels_data = data.get('programDetailsByChannel', [])
    except Exception as e:
        print(f"❌ Error loading or parsing JSON file: {e}")
        return

    filtered_channels = [ch for ch in all_channels_data if not desired_channels or ch.get('channelname') in desired_channels]
    if not filtered_channels:
        print("❌ Warning: None of your desired channels were found in the JSON file.")
        return
    print(f"✅ Found {len(filtered_channels)} matching channels to display.")

    ist_timezone = timezone(timedelta(hours=5, minutes=30))
    today_date = datetime.now(ist_timezone).date()
    tomorrow_date = today_date + timedelta(days=1)

    color_palette = [
        ("#4285F4", "#1a73e8"), ("#DB4437", "#c53727"), ("#0F9D58", "#0b8043"),
        ("#AB47BC", "#8E24AA"), ("#00ACC1", "#00838F"), ("#FF7043", "#F4511E"),
        ("#F4B400", "#f09300"), ("#78909C", "#546E7A"), ("#5C6BC0", "#3949AB")
    ]

    def generate_program_blocks(channels, target_date):
        blocks = []
        for i, ch in enumerate(channels):
            bg_color, border_color = color_palette[i % len(color_palette)]
            for prog in ch.get('programs', []):
                p_start = parse_assumed_local_time(prog['start'])
                p_stop = parse_assumed_local_time(prog['stop'])
                if p_start.date() == target_date:
                    duration_minutes = (p_stop - p_start).total_seconds() / 60
                    if duration_minutes <= 0: continue
                    start_minute_of_day = p_start.hour * 60 + p_start.minute
                    top_percent = (start_minute_of_day / 1440) * 100
                    height_percent = (duration_minutes / 1440) * 100
                    left_pixels = i * 200
                    width_pixels = 190
                    style = (
                        f'top:{top_percent:.4f}%; left:{left_pixels}px; height:{height_percent:.4f}%; width:{width_pixels}px;'
                        f'background-color: {bg_color}; border-color: {border_color};'
                    )
                    description = html.escape(prog.get("desc", "No description available."))
                    title = html.escape(prog.get("title", "Untitled Program"))
                    time_str = f'{p_start.strftime("%H:%M")} - {p_stop.strftime("%H:%M")}'
                    blocks.append(
                        f'<div class="program-block" style="{style}" data-description="{description}">'
                        f'<span class="program-title">{title}</span>'
                        f'<span class="program-time">{time_str}</span>'
                        '</div>'
                    )
        return ''.join(blocks)

    num_channels = len(filtered_channels)
    grid_width = num_channels * 200
    channel_headers_html = ''.join([f'<div class="channel-header">{html.escape(ch["channelname"])}</div>' for ch in filtered_channels])
    today_blocks = generate_program_blocks(filtered_channels, today_date)
    tomorrow_blocks = generate_program_blocks(filtered_channels, tomorrow_date)
    time_markers_html = ''.join([f'<div class="time-marker"><span>{h % 24:02d}:00</span></div>' for h in range(24)])

    JAVASCRIPT_BLOCK = """
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            const scrollPane = document.querySelector('.schedule-scroll-pane');
            const timeMarkers = document.querySelector('.time-markers');
            const channelsHeader = document.querySelector('.channels-header-wrapper');
            const todayBtn = document.getElementById('todayBtn');
            const tomorrowBtn = document.getElementById('tomorrowBtn');
            const todayGrid = document.getElementById('todayGrid');
            const tomorrowGrid = document.getElementById('tomorrowGrid');
            const tooltip = document.getElementById('tooltip');
            const timeIndicator = document.querySelector('#todayGrid .time-indicator');
            scrollPane.addEventListener('scroll', () => {
                channelsHeader.scrollLeft = scrollPane.scrollLeft;
                timeMarkers.scrollTop = scrollPane.scrollTop;
            });
            function updateReadability(gridElement) {
                if (!gridElement || gridElement.classList.contains('hidden')) return;
                gridElement.querySelectorAll('.program-block').forEach(block => {
                    const timeEl = block.querySelector('.program-time');
                    if (timeEl) {
                        timeEl.style.display = (block.offsetHeight < 35) ? 'none' : 'block';
                    }
                });
            }
            function showDay(day) {
                const isToday = day === 'today';
                todayGrid.classList.toggle('hidden', !isToday);
                tomorrowGrid.classList.toggle('hidden', isToday);
                todayBtn.classList.toggle('active', isToday);
                tomorrowBtn.classList.toggle('active', !isToday);
                const visibleGrid = isToday ? todayGrid : tomorrowGrid;
                updateReadability(visibleGrid);
                if (isToday) { updateTimeline(); }
            }
            todayBtn.addEventListener('click', () => showDay('today'));
            tomorrowBtn.addEventListener('click', () => showDay('tomorrow'));
            document.querySelectorAll('.program-block').forEach(block => {
                block.addEventListener('mousemove', function(e) {
                    tooltip.style.display = 'block';
                    tooltip.textContent = this.dataset.description;
                    tooltip.style.left = (e.clientX + 15) + 'px';
                    tooltip.style.top = (e.clientY + 15) + 'px';
                });
                block.addEventListener('mouseleave', () => { tooltip.style.display = 'none'; });
                block.addEventListener('click', function() {
                    const titleElement = this.querySelector('.program-title');
                    if (titleElement) {
                        const title = titleElement.textContent;
                        const searchURL = `https://www.google.com/search?q=${encodeURIComponent(title)}`;
                        window.open(searchURL, '_blank');
                    }
                });
            });
            function getISTTime() {
                const now = new Date();
                const utc_ms = now.getTime();
                const ist_offset_ms = 330 * 60 * 1000;
                const istDate = new Date(utc_ms + ist_offset_ms);
                return { hour: istDate.getUTCHours(), minute: istDate.getUTCMinutes() };
            }
            function updateTimeline() {
                if (todayGrid.classList.contains('hidden')) return;
                const istTime = getISTTime();
                const totalMinutes = istTime.hour * 60 + istTime.minute;
                const topPercent = (totalMinutes / 1440) * 100;
                if (timeIndicator) {
                    timeIndicator.style.top = `${topPercent}%`;
                    timeIndicator.style.display = 'block';
                }
            }
            function scrollToNow() {
                const istTime = getISTTime();
                const totalMinutes = istTime.hour * 60 + istTime.minute;
                const topPercent = (totalMinutes / 1440) * 100;
                const topPositionInPx = (topPercent / 100) * scrollPane.scrollHeight;
                scrollPane.scrollTo({ top: Math.max(0, topPositionInPx - scrollPane.clientHeight / 3), behavior: 'smooth' });
            }
            showDay('today');
            scrollToNow();
            setInterval(updateTimeline, 60000);
        });
    </script>
    """

    HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TV Timeline Guide</title>
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {{ --header-height: 60px; --timeline-header-height: 40px; --time-col-width: 60px; --channel-width: 200px; --hour-height: 80px; }}
        html, body {{ height: 100%; margin: 0; overflow: hidden; font-family: 'Roboto', sans-serif; background-color: #f1f3f4; }}
        .page-header {{ height: var(--header-height); text-align: center; background-color: #fff; border-bottom: 1px solid #ddd; display: flex; align-items: center; justify-content: center; flex-direction: column; padding: 5px 0; box-sizing: border-box; }}
        .page-header h1 {{ margin: 0 0 5px 0; font-size: 1.2em; }}
        .date-switcher button {{ font-size: 0.9em; padding: 5px 12px; margin: 0 5px; border: 1px solid #ccc; background-color: #fff; border-radius: 5px; cursor: pointer; }}
        .date-switcher button.active {{ background-color: #1a73e8; color: white; border-color: #1a73e8; }}
        .timeline-container {{ display: grid; grid-template-columns: var(--time-col-width) 1fr; grid-template-rows: var(--timeline-header-height) 1fr; height: calc(100vh - var(--header-height)); }}
        .corner-block {{ grid-column: 1; grid-row: 1; background-color: #fff; border-right: 1px solid #ddd; border-bottom: 1px solid #ddd; }}
        .channels-header-wrapper {{ grid-column: 2; grid-row: 1; background-color: #fff; overflow: hidden; border-bottom: 1px solid #ddd; }}
        .channels-header-content {{ display: flex; width: {grid_width}px; }}
        .channel-header {{ flex: 0 0 var(--channel-width); box-sizing: border-box; text-align: center; padding: 10px 5px; font-weight: 500; border-left: 1px solid #ddd; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
        .time-markers {{ grid-column: 1; grid-row: 2; overflow-y: hidden; text-align: right; font-size: 0.8em; color: #5f6368; background-color: #fff; border-right: 1px solid #ddd; }}
        .time-marker {{ height: var(--hour-height); box-sizing: border-box; padding-right: 5px; position: relative; }}
        .time-marker span {{ position: relative; top: -0.6em; }}
        .schedule-scroll-pane {{ grid-column: 2; grid-row: 2; overflow: auto; }}
        .schedule-grid {{ position: relative; width: {grid_width}px; height: calc(var(--hour-height) * 24); 
                         background-image: linear-gradient(#e0e0e0 1px, transparent 1px), linear-gradient(to right, #e0e0e0 1px, transparent 1px);
                         background-size: 100% var(--hour-height), var(--channel-width) 100%; }}
        .program-block {{ position: absolute; box-sizing: border-box; border: 1px solid; color: #fff; border-radius: 4px; padding: 4px; font-size: 0.8em; overflow: hidden; display: flex; flex-direction: column; transition: filter 0.15s ease-in-out; cursor: pointer; }}
        .program-block:hover {{ z-index: 10; filter: brightness(115%); }}
        .program-title {{ font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
        .program-time {{ font-size: 0.9em; opacity: 0.8; white-space: nowrap; }}
        .time-indicator {{ position: absolute; width: 100%; height: 2px; background-color: #ea4335; left: 0; z-index: 20; display: none; pointer-events: none; }}
        .time-indicator::before {{ content: ''; display: block; width: 10px; height: 10px; border-radius: 50%; background-color: #ea4335; position: absolute; left: -5px; top: -4px; }}
        #tooltip {{ position: fixed; display: none; background: rgba(0,0,0,0.85); color: white; padding: 10px 15px; border-radius: 6px; z-index: 100; max-width: 300px; font-size: 0.9em; pointer-events: none; }}
        .hidden {{ display: none; }}
    </style>
</head>
<body>
    <header class="page-header">
        <h1>My TV Guide</h1>
        <div class="date-switcher"><button id="todayBtn" class="active">Today</button><button id="tomorrowBtn">Tomorrow</button></div>
    </header>
    <div class="timeline-container">
        <div class="corner-block"></div>
        <div class="channels-header-wrapper"><div class="channels-header-content">{channel_headers_html}</div></div>
        <div class="time-markers">{time_markers_html}</div>
        <div class="schedule-scroll-pane">
            <div id="todayGrid" class="schedule-grid"><div class="time-indicator"></div>{today_blocks}</div>
            <div id="tomorrowGrid" class="schedule-grid hidden">{tomorrow_blocks}</div>
        </div>
    </div>
    <div id="tooltip"></div>
    {javascript_block}
</body>
</html>
"""

    final_html = HTML_TEMPLATE.format(
        grid_width=grid_width,
        channel_headers_html=channel_headers_html,
        time_markers_html=time_markers_html,
        today_blocks=today_blocks,
        tomorrow_blocks=tomorrow_blocks,
        javascript_block=JAVASCRIPT_BLOCK
    )

    with open(HTML_OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(final_html)
    
    print(f"🎉 Success! Your new timeline guide has been created: '{HTML_OUTPUT_FILE}'")

# ==============================================================================
# --- MAIN EXECUTION BLOCK ---
# ==============================================================================
if __name__ == "__main__":
    # --- Step 1: Execute the scraper logic ---
    token, cookies = get_fresh_credentials()
    
    data_was_scraped = False
    if token and cookies:
        # --- Date Setup ---
        today = datetime.now()
        tomorrow = today + timedelta(days=1)
        today_str = today.strftime('%d/%m/%Y')
        tomorrow_str = tomorrow.strftime('%d/%m/%Y')

        # --- Fetch Data for Both Days (Full data) ---
        today_channels_all, _ = fetch_tv_guide(token, cookies, today_str)
        tomorrow_channels_all, _ = fetch_tv_guide(token, cookies, tomorrow_str)

        # <<< NEW: Filter the channels based on the desired_channels list >>>
        if desired_channels:
            print(f"\nFiltering for {len(desired_channels)} desired channels...")
            today_channels = [ch for ch in today_channels_all if ch.get('channelname') in desired_channels]
            tomorrow_channels = [ch for ch in tomorrow_channels_all if ch.get('channelname') in desired_channels]
        else:
            # If the desired_channels list is empty, use all channels
            today_channels = today_channels_all
            tomorrow_channels = tomorrow_channels_all

        # --- Print Guides to console (using the filtered data) ---
        if today_channels:
            print_guide(today_channels, f"TODAY ({today_str})")
        if tomorrow_channels:
            print_guide(tomorrow_channels, f"TOMORROW ({tomorrow_str})")
            
        # --- Combine and Save Data (using the filtered data) ---
        if today_channels and tomorrow_channels:
            combined_channels_dict = {ch['channelname']: ch for ch in today_channels}
            for tmrw_ch in tomorrow_channels:
                ch_name = tmrw_ch.get('channelname')
                if ch_name in combined_channels_dict:
                    # Append tomorrow's programs to the existing channel's program list
                    combined_channels_dict[ch_name]['programs'].extend(tmrw_ch.get('programs', []))

            # Convert the dictionary back to a list
            final_channels_list = list(combined_channels_dict.values())
            
            # Save the combined data
            final_data_structure = {"programDetailsByChannel": final_channels_list}
            save_filename = 'tv_guide_today_and_tomorrow.json'
            with open(save_filename, 'w', encoding='utf-8') as f:
                json.dump(final_data_structure, f, indent=2, ensure_ascii=False)
            print(f"\n📁 Complete combined data for your desired channels saved to: {save_filename}")
            data_was_scraped = True

    else:
        print("\nCould not retrieve credentials. Aborting scraper.")

    # --- Step 2: If scraper was successful, execute the HTML generator logic ---
    if data_was_scraped:
        create_timeline_guide()
    else:
        print("\nSkipping HTML generation because data scraping failed.")

}
what next
