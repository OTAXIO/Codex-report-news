"""TTS-only pronunciations; displayed text and captions retain brand spelling."""
import re

def spoken_text(text,rules):
    for word,replacement in sorted(rules.items(),key=lambda row:len(row[0]),reverse=True):
        text=re.sub(r'(?<![A-Za-z])'+re.escape(word)+r'(?![A-Za-z])',lambda _:replacement,text)
    # AI remains one uninterrupted English token, never A-I / A, I / A. I.
    return re.sub(r'\bA\s+I\b','AI',text)
