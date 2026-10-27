"""TTS-only pronunciations; displayed text and captions retain brand spelling."""
import re

def chinese_clock_number(value):
    if not 0<=value<=59:raise ValueError('Clock number out of range')
    digits='零一二三四五六七八九'
    if value<10:return digits[value]
    tens,ones=divmod(value,10)
    return (digits[tens] if tens>1 else '')+'十'+(digits[ones] if ones else '')

def spoken_clock_times(text):
    def convert(match):
        hour,minute=int(match.group(1)),int(match.group(2))
        if hour>23 or minute>59:return match.group(0)
        if minute==0:return chinese_clock_number(hour)+'点整'
        return chinese_clock_number(hour)+'点'+('零' if minute<10 else '')+chinese_clock_number(minute)+'分'
    text=re.sub(r'(?<!\d)(\d{1,2})\s*点\s*(\d{1,2})\s*分',convert,text)
    return re.sub(r'(?<![\d:])(\d{1,2}):(\d{2})(?![\d:])',convert,text)

def spoken_text(text,rules):
    for word,replacement in sorted(rules.items(),key=lambda row:len(row[0]),reverse=True):
        text=re.sub(r'(?<![A-Za-z])'+re.escape(word)+r'(?![A-Za-z])',lambda _:replacement,text)
    # AI remains one uninterrupted English token, never A-I / A, I / A. I.
    return spoken_clock_times(re.sub(r'\bA\s+I\b','AI',text))
