#!/usr/bin/env python3
"""Fetch city images from Wikipedia — gentle rate limiting approach."""
import json, os, time, urllib.request, urllib.parse, subprocess

CITIES_FILE = '/tmp/cities.txt'
ASSETS_DIR = '/root/hob-workflows/acb/site/assets/cities'
COOKIE_JAR = '/tmp/wiki_cookies.txt'
os.makedirs(ASSETS_DIR, exist_ok=True)

overrides = {
    "New York City": "New_York_City",
    "St. Louis": "St._Louis",
    "Salt Lake City": "Salt_Lake_City",
    "Kansas City": "Kansas_City_(Missouri)",
    "Las Vegas": "Las_Vegas",
    "Kennewick": "Kennewick,_Washington",
    "Vancouver": "Vancouver,_Washington",
}

with open(CITIES_FILE) as f:
    rows = [line.strip().split('|') for line in f if line.strip()]

# First pass: collect all image URLs from Wikipedia API
print("Phase 1: Collecting image URLs from Wikipedia...")
city_images = {}  # slug -> img_url

for i, (slug, state_slug, city, state, abbr) in enumerate(rows):
    out_path = os.path.join(ASSETS_DIR, f"{slug}.jpg")
    if os.path.exists(out_path) and os.path.getsize(out_path) > 10000:
        print(f"  [{i+1}/{len(rows)}] {city} - already exists")
        city_images[slug] = "EXISTS"
        continue
    
    page_title = overrides.get(city, f"{city}, {state}")
    encoded = urllib.parse.quote(page_title)
    api_url = f"https://en.wikipedia.org/w/api.php?action=query&prop=pageimages&format=json&piprop=original&titles={encoded}"
    
    img_url = None
    try:
        req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0 HOB/1.0'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        for pid, page in data.get('query', {}).get('pages', {}).items():
            if pid != '-1':
                img_url = page.get('original', {}).get('source', '')
    except:
        pass
    
    if not img_url:
        try:
            simple = urllib.parse.quote(city)
            req2 = urllib.request.Request(f"https://en.wikipedia.org/w/api.php?action=query&prop=pageimages&format=json&piprop=original&titles={simple}", 
                                          headers={'User-Agent': 'Mozilla/5.0 HOB/1.0'})
            with urllib.request.urlopen(req2, timeout=15) as resp2:
                data2 = json.loads(resp2.read())
            for pid, page in data2.get('query', {}).get('pages', {}).items():
                if pid != '-1':
                    img_url = page.get('original', {}).get('source', '')
        except:
            pass
    
    if img_url:
        city_images[slug] = img_url
        print(f"  [{i+1}/{len(rows)}] {city} - found ✓")
    else:
        print(f"  [{i+1}/{len(rows)}] {city} - no image ✗")
    
    time.sleep(0.8)

# Save URLs for reference
with open('/tmp/city_image_urls.json', 'w') as f:
    json.dump(city_images, f, indent=2)

# Phase 2: Download all images with generous delays
print(f"\nPhase 2: Downloading {len([v for v in city_images.values() if v != 'EXISTS'])} images...")

downloaded = 0
errors = 0

for slug, img_url in city_images.items():
    if img_url == 'EXISTS':
        continue
    
    out_path = os.path.join(ASSETS_DIR, f"{slug}.jpg")
    if os.path.exists(out_path) and os.path.getsize(out_path) > 10000:
        continue
    
    # Find city name for display
    for s, ss, c, st, a in rows:
        if s == slug:
            city = c
            state = st
            break
    
    cmd = [
        'curl', '-sL', '-o', out_path,
        '-H', 'User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        '-H', 'Accept: image/webp,image/avif,image/jpeg,*/*',
        '--max-time', '30',
        img_url
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=35)
    
    if os.path.exists(out_path) and os.path.getsize(out_path) > 5000:
        size_kb = os.path.getsize(out_path) / 1024
        print(f"  ✓ {city}, {state} - {size_kb:.0f}KB")
        downloaded += 1
    else:
        print(f"  ✗ {city}, {state} - download failed")
        errors += 1
        if os.path.exists(out_path):
            os.remove(out_path)
    
    # 3 second delay between each download to avoid rate limiting
    time.sleep(3)

print(f"\nDownloaded: {downloaded}, Errors: {errors}")
print(f"Total images: {len([f for f in os.listdir(ASSETS_DIR) if f.endswith('.jpg')])}")
