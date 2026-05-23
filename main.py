import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials
from google import genai
import os

# ======================
# Gemini client
# ======================
gemini_client = genai.Client(api_key="")

# ======================
# Google Sheets auth
# ======================
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_name(
    "credentials.json",
    scope
)

gs_client = gspread.authorize(creds)
sheet = gs_client.open("beauty_vocab_db").sheet1

# ======================
# Get all rows
# ======================
rows = sheet.get_all_records()

existing_words = []
unused_rows_new_generate = []

for row in rows:
    existing_words.append(row["japanese"])

    if row["status"] == "unused":
        unused_rows_new_generate.append(row)

# ==================================================
# GENERATE NEW VOCAB ONLY ONCE
# ==================================================

if len(unused_rows_new_generate) < 4:

    existing_text = ", ".join(existing_words)

    generate_prompt = f"""
    Generate 30 Japanese beauty vocabulary words.

    Categories:
    - skincare
    - makeup
    - hair

    IMPORTANT:
    Do NOT generate these Japanese words:
    {existing_text}

    Return ONLY valid JSON.

    Format:
    [
    {{
        "category":"skincare",
        "japanese":"美容液",
        "reading":"びようえき",
        "burmese":"serum",
        "image_keyword":"japanese serum"
    }}
    ]
    """

    generate_response = gemini_client.models.generate_content(
        model="gemini-flash-latest",
        # model="gemini-2.0-flash-lite",
        contents=generate_prompt
    )

    # clean json
    clean_text = generate_response.text.replace(
        "```json", ""
    ).replace(
        "```", ""
    ).strip()

    # json -> python
    new_vocab_data = json.loads(clean_text)

    added_count = 0

    for item in new_vocab_data:

        japanese = item["japanese"]

        # skip duplicate
        if japanese in existing_words:
            print(f"Skipped duplicate: {japanese}")
            continue

        new_id = len(rows) + 1

        new_row = [
            new_id,
            item["category"],
            japanese,
            item["reading"],
            item["burmese"],
            item["image_keyword"],
            "unused"
        ]

        sheet.append_row(new_row)

        print(f"Added new vocab: {japanese}")

        rows.append({
            "id": new_id,
            "category": item["category"],
            "japanese": japanese,
            "reading": item["reading"],
            "burmese": item["burmese"],
            "image_keyword": item["image_keyword"],
            "status": "unused"
        })

        existing_words.append(japanese)

        added_count += 1

        # stop after 3 unique words
        if added_count >= 3:
            break

# ==================================================
# TAKE 3 UNUSED VOCAB
# ==================================================
unused_rows = []

for row in rows:
    if row["status"] == "unused":
        unused_rows.append(row)

    if len(unused_rows) == 3:
        break

# ======================
# Build Facebook Prompt
# ======================

prompt = """
You are beauty content creator for Myanmar girls living in Japan.

Create ONLY ONE Facebook/TikTok style post.

Use ALL Japanese beauty vocabulary naturally in ONE post.

Style:
- Cute
- Casual Burmese
- Short and clean
- TikTok/Facebook vibe
- Emojis included
- Sound like Myanmar beauty influencer

For each word include:
- Japanese word
- Hiragana reading
- Burmese meaning
- Very short example feeling/situation
- Small image idea

Output format example:

🌸 敏感肌
(びんかんはだ)
= အသားအရေအထိမခံတာ

💬 Example:
ရာသီဥတုပြောင်းရင် အသားယားပြီး sensitive ဖြစ်နေတယ် 🥺

🖼️ Image:
Girl scratching cheek softly

--------------------------------
"""

# add vocab
for row in unused_rows:
    prompt += f"""

Japanese: {row['japanese']}
Reading: {row['reading']}
Meaning: {row['burmese']}
"""

prompt += """

IMPORTANT:
- Make ONE combined post only
- Do NOT create Post 1, Post 2, Post 3
- Keep each vocab section short
- Make it aesthetic and social-media style
- Add hashtags at bottom
- Include #JapanMakeup
"""

# ======================
# Generate Facebook Post
# ======================
response = gemini_client.models.generate_content(
    model="gemini-flash-latest",
    contents=prompt
)

# ======================
# Print result
# ======================
print("========== FACEBOOK POST ==========")
print(response.text)
print("===================================")

# ======================
# Mark as posted
# ======================
for row in unused_rows:
    cell = sheet.find(row["japanese"])
    sheet.update_cell(cell.row, 7, "posted")