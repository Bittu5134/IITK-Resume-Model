import pymupdf
import json

# ── 1. Extract raw text ──────────────────────────────────────────────────────
doc = pymupdf.open("IITK Campus Lingo.pdf")
full_text = ""
for page in doc:
    full_text += page.get_text("text") + "\n"
doc.close()

# Write to a text file so we can read it safely
with open("lingo_raw.txt", "w", encoding="utf-8") as f:
    f.write(full_text)

print(f"Extracted {len(full_text)} characters, {len(full_text.splitlines())} lines")
print("Written to lingo_raw.txt")
