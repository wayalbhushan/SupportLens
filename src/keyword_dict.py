"""
src/keyword_dict.py
-------------------
Keyword dictionary for Baseline 1 (Trivial Keyword Baseline) and weak labeling in Baseline 2.
Derived directly from the "Inclusions" bullets of each intent in LABELING_GUIDE.md v1.2.
"""

from typing import Dict, List

# Keyword lists for each of the 8 taxonomy classes
KEYWORD_DICT: Dict[str, List[str]] = {
    "account_access": [
        "login", "log in", "sign in", "signin", "password", "passwords",
        "locked out", "portal", "my verizon", "my fios app", "reset password",
        "forgot password", "authentication", "authenticate", "smtp", "credentials",
        "username"
    ],
    "appointment_installation": [
        "technician", "tech", "install", "installation", "appointment",
        "dispatch", "setup", "no show", "window", "reschedule", "rescheduling",
        "tech visit", "service tech", "line transfer"
    ],
    "billing_dispute": [
        "bill", "billing", "charge", "charged", "charging", "fee", "fees",
        "cost", "price", "overcharge", "overcharged", "refund", "refunds",
        "credit", "credits", "discount", "discounts", "rate", "rates",
        "promo", "promotional", "double billed", "double charge", "collections",
        "unreturned", "shut off", "shutoff"
    ],
    "tv_content_access": [
        "channel", "channels", "tv", "cable box", "set top", "stb", "dvr",
        "on demand", "ondemand", "univision", "hbo", "red zone", "redzone",
        "recording", "blackout", "guide", "widgets", "pay per view", "ppv"
    ],
    "connectivity_issue": [
        "outage", "slow", "down", "wifi", "wi-fi", "internet", "speed",
        "speeds", "router", "ont", "gateway", "red globe", "blinking",
        "disconnect", "disconnecting", "packet loss", "broadband", "dns",
        "wire down", "wires down", "cable down", "no connection", "cant connect",
        "cannot connect", "wont connect", "no service", "offline", "gigabit",
        "fiber", "fiber-optic", "pole", "leaning pole"
    ],
    "praise_thanks": [
        "thank you", "thanks", "thx", "appreciate", "great service", "awesome",
        "kudos", "props", "best customer service", "shout out", "helpful",
        "sweet", "reliable service", "good vibes"
    ],
    "complaint_no_request": [
        "worst", "garbage", "trash", "terrible", "horrible", "sucks", "suck",
        "useless", "disappointed", "hold", "on hold", "hang up", "hung up",
        "rude", "hate", "unacceptable", "switching", "cancel", "canceling",
        "cancelling", "phd", "disrespected", "shameful", "joke", "bullshit", "fuck"
    ],
    "other": [
        "available in", "availability", "expand", "chicago", "baltimore",
        "spectrum", "comcast", "optimum", "att", "at&t", "tune in",
        "game time", "broadcast", "commercial", "net neutrality", "fcc"
    ],
}

# Priority order: specific technical/account/financial intents tested before
# general sentiment/venting, ensuring stated defects override surface complaints
# per Tie-Break Rule 2 in LABELING_GUIDE.md v1.2.
PRIORITY_ORDER: List[str] = [
    "account_access",
    "appointment_installation",
    "billing_dispute",
    "tv_content_access",
    "connectivity_issue",
    "praise_thanks",
    "complaint_no_request",
    "other",
]
