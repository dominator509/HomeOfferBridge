#!/usr/bin/env python3
"""Download Wikipedia images with slow, careful rate limiting."""
import json, os, time, subprocess

ASSETS_DIR = '/root/hob-workflows/acb/site/assets/cities'
URL_FILE = '/tmp/city_image_urls.json'

with open(URL_FILE) as f:
    all_images = json.load(f)

ok = 0
err = 0
skipped = 0

for slug, img_url in sorted(all_images.items()):
    if img_url == 'EXISTS':
        skipped += 1
        continue
    
    out_path = os.path.join(ASSETS_DIR, f"{slug}.jpg")
    if os.path.exists(out_path) and os.path.getsize(out_path) > 10000:
        skipped += 1
        continue
    
    # Find city name
    city = slug.replace('-', ' ').title()
    
    for attempt in range(5):
        result = subprocess.run([
            'curl', '-sL', '-o', out_path,
            '-H', 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            '-H', 'Accept: image/avif,image/webp,image/jpeg,*/*',
            '--max-time', '30',
            img_url
        ], capture_output=True, text=True, timeout=35)
        
        if os.path.exists(out_path) and os.path.getsize(out_path) > 5000:
            size_kb = os.path.getsize(out_path) / 1024
            print(f"  ✓ {city} - {size_kb:.0f}KB")
            ok += 1
            break
        else:
            if os.path.exists(out_path):
                os.remove(out_path)
            if attempt < 4:
                wait = (attempt + 1) * 8
                print(f"  ... {city} retry {attempt+1}/5 (wait {wait}s)")
                time.sleep(wait)
            else:
                print(f"  ✗ {city} - failed after 5 attempts")
                err += 1
    
    # 8 second delay between different images
    time.sleep(8)

print(f"\nOK: {ok}, Skipped: {skipped}, Errors: {err}")
