import os
import re
import time


def extract_yt_term(command):
    # Support "play [song] on youtube" or just "play [song]"
    patterns = [
        r'(?:play|bajao)\s+(.*?)\s+on\s+youtube',
        r'(?:play|bajao)\s+(.*)'
    ]
    for pattern in patterns:
        match = re.search(pattern, command, re.IGNORECASE)
        if match:
            term = match.group(1).strip()
            # If the term contains "on youtube", it was likely a fuzzy match from the second pattern
            term = term.replace("on youtube", "").strip()
            if term:
                return term
    return None


def remove_words(input_string, words_to_remove):
    # Split the input string into words
    words = input_string.split()

    # Remove unwanted words
    filtered_words = [word for word in words if word.lower() not in words_to_remove]

    # Join the remaining words back into a string
    result_string = ' '.join(filtered_words)

    return result_string



# key events like receive call, stop call, go back
def keyEvent(key_code):
    command =  f'adb shell input keyevent {key_code}'
    os.system(command)
    time.sleep(1)

# Tap event used to tap anywhere on screen
def tapEvents(x, y):
    command =  f'adb shell input tap {x} {y}'
    os.system(command)
    time.sleep(1)

# Input Event is used to insert text in mobile
def adbInput(message):
    command =  f'adb shell input text "{message}"'
    os.system(command)
    time.sleep(1)

# to go complete back
def goback(key_code):
    for _ in range(6):
        keyEvent(key_code)

# To replace space in string with %s for complete message send
def replace_spaces_with_percent_s(input_string):
    return input_string.replace(' ', '%s')
