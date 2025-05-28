import os
import pytz
from dotenv import load_dotenv

load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
TRACKER_API_KEY = os.getenv('TRACKER_API_KEY')
ALLOWED_GUILD_IDS = {899978176355266580, 989558855023362110}
WEATHER_API_KEY = os.getenv('WEATHER_API_KEY')
TIMEZONES = sorted(pytz.all_timezones)
DATA_FOLDER = "data"
ALERTS_FILE = f"{DATA_FOLDER}/alerts.json"
SCORES_FILE = f"{DATA_FOLDER}/trivia_scores.json"

SUPPORTED_TZ = {
        # US Timezones
        "EST": "America/New_York",
        "EDT": "America/New_York",
        "CST": "America/Chicago",
        "CDT": "America/Chicago",
        "MST": "America/Denver",
        "MDT": "America/Denver",
        "PST": "America/Los_Angeles",
        "PDT": "America/Los_Angeles",
        "AKST": "America/Anchorage",
        "AKDT": "America/Anchorage",
        "HST": "Pacific/Honolulu",

        # Europe
        "GMT": "Etc/GMT",
        "BST": "Europe/London",
        "CET": "Europe/Paris",
        "CEST": "Europe/Paris",
        "EET": "Europe/Athens",
        "EEST": "Europe/Athens",
        "WET": "Europe/Lisbon",
        "WEST": "Europe/Lisbon",

        # Asia
        "IST": "Asia/Kolkata",
        "KST": "Asia/Seoul",
        "SGT": "Asia/Singapore",
        "HKT": "Asia/Hong_Kong",

        # Australia
        "AEST": "Australia/Sydney",
        "AEDT": "Australia/Sydney",
        "ACST": "Australia/Adelaide",
        "ACDT": "Australia/Adelaide",
        "AWST": "Australia/Perth",

        # New Zealand
        "NZST": "Pacific/Auckland",
        "NZDT": "Pacific/Auckland",

        # Common UTC variants
        "UTC": "UTC",
        "Z": "UTC",

    }

#images
image_urls = [
    "https://i.imgur.com/3ZIBxuh.png",
    "https://i.imgur.com/fafftDC.jpeg",
    "https://i.imgur.com/iUjJyba.png",
    "https://i.imgur.com/wltqqd0.jpeg",
    "https://i.imgur.com/rC6bxUS.jpeg",
    "https://i.imgur.com/UAlUh4W.jpeg",
    "https://i.imgur.com/K60KP2c.jpeg",
    "https://i.imgur.com/2slTvIy.jpeg",
    "https://i.imgur.com/tpr9aoW.png",
    "https://i.imgur.com/wSFVwgg.jpeg",
    "https://i.imgur.com/y3BlmVT.jpeg",
    "https://i.imgur.com/MDp5v9G.jpeg",
    "https://i.imgur.com/OB9X52Y.png",
    "https://ibb.co/QFzhXkHy",
    "https://i.imgur.com/jSbZjnG.jpeg",
    "https://i.imgur.com/AA6zTQ7.jpeg",
    "https://i.imgur.com/im4dYj2.jpeg",
    "https://i.imgur.com/sdkffat.png",
    "https://i.imgur.com/zho3DZM.png",
    "https://i.imgur.com/4PRVmsz.png",
    "https://i.imgur.com/yGfu5OD.png",
    "https://i.imgur.com/KLTuASH.jpeg",
    "https://i.imgur.com/FDog6KT.png",

]

#clancy
clancy_images = [
    "https://i.imgur.com/1cuthyS.jpeg",
    "https://i.imgur.com/3QqKqky.jpeg",
    "https://i.imgur.com/Pypy5Um.jpeg",
    "https://i.imgur.com/pTxuW0k.jpeg",
    "https://i.imgur.com/5N5SICy.jpeg",
    "https://i.imgur.com/lAAkcZv.jpeg",
    "https://i.imgur.com/1gRZP6B.jpeg",
    "https://i.imgur.com/1Zmsj69.jpeg",
    "https://i.imgur.com/T86njLU.jpeg",
    "https://i.imgur.com/HWqnDQV.jpeg",
    "https://i.imgur.com/9sRRahk.jpeg",
    "https://i.imgur.com/FZdxbbg.jpeg",
    "https://i.imgur.com/k9U1xsD.jpeg",
    "https://i.imgur.com/Eb57KeJ.jpeg",
    "https://i.imgur.com/KhiDgPa.jpeg",
    "https://i.imgur.com/lL9YYDe.jpeg",
    "https://i.imgur.com/CunLaFJ.jpeg",
    "https://i.imgur.com/Eo0RxHB.jpeg",
    "https://i.imgur.com/4ETJuvy.jpeg",

]

#quote list
quotes = [
    "Birthdays. Proposals. These should be surprises. No one wants a grenade to the face.",
    "Is there sarcasm in this?",
    "Remember, I can't fix you like I fix your cars.",
    "I'm an engineer, not a medic!",
    "You can stop worrying about grenades now!",
    "Your plan is as good as your intel!",
    "Before we start, does anyone want to bail out?",
    "I would not have said it like that, but, it is cool.",
    "Stay alert and watch for trouble, yes?",
    "Just let me know when grenades start flying.",
    "Someone owes me a steak dinner!",
    "They said it could not be done. They said it was designed for tanks. They said, I could not make it smaller and more accurate. They were wrong.",
    "One of my better tactical strategies is to stay alive. So far, so good.",
]