"""
comments.py — generates contextual comments for "tell us why you want to win" fields.
Matches keywords in the sweepstakes name to enthusiasm templates.
Edit COMMENT_TEMPLATES to customize.
"""
import random


COMMENT_TEMPLATES = {
    # Vehicles
    'motorcycle':   ["These motorcycles are the best!", "I've always wanted a bike like this!", "What an incredible motorcycle!"],
    'harley':       ["Harley Davidson is the best!", "Always dreamed of a Harley!", "Harley Davidson — what a legendary brand!"],
    'honcho':       ["Honcho makes amazing bikes!", "Honcho is the best!", "Love everything about Honcho!"],
    'truck':        ["What a fantastic truck!", "This truck would be perfect for me!", "Built tough — love it!"],
    'pickup':       ["This pickup is exactly what I need!", "Love a good pickup truck!", "Perfect work truck!"],
    'jeep':         ["Jeeps are amazing for adventure!", "Always wanted a Jeep!", "Jeep life is the best!"],
    'ford':         ["Ford makes such great vehicles!", "Love Ford trucks!", "Built Ford Tough!"],
    'chevy':        ["Chevy is the best!", "Chevrolet builds great vehicles!", "Love Chevy!"],
    'tesla':        ["Tesla is revolutionary!", "Would love to drive a Tesla!", "Tesla is the future!"],
    'rv':           ["RVs are perfect for family trips!", "Love RV life!", "What an amazing RV!"],

    # Travel
    'vacation':     ["This vacation looks incredible!", "Need this vacation so badly!", "Dream vacation!"],
    'trip':         ["What an amazing trip!", "Bucket list trip for sure!", "Would love this getaway!"],
    'cruise':       ["I've always wanted to go on a cruise!", "Cruises are the best way to travel!", "Dream cruise!"],
    'hawaii':       ["Hawaii is a dream destination!", "Aloha! Would love to visit!", "Hawaii is paradise!"],
    'disney':       ["Disney is magical — would love this!", "Disney trip would be incredible!", "Love Disney!"],
    'beach':        ["Nothing beats a beach getaway!", "Beach time is the best!", "Love the beach!"],
    'resort':       ["This resort looks beautiful!", "Perfect getaway destination!", "Stunning resort!"],

    # Tech
    'iphone':       ["iPhones are the best!", "Would love a new iPhone!", "Apple makes amazing products!"],
    'ipad':         ["iPad is perfect for everything!", "Always wanted an iPad!", "Great for work and play!"],
    'macbook':      ["MacBooks are incredible!", "Would love a new MacBook!", "Apple laptops are the best!"],
    'laptop':       ["A new laptop would be a game-changer!", "Could really use a new laptop!", "Love this laptop!"],
    'tv':           ["What an amazing TV!", "Perfect for movie nights!", "This would upgrade my whole setup!"],
    'gaming':       ["Gaming setup of dreams!", "Love gaming!", "What an awesome gaming prize!"],
    'ps5':          ["PS5 is the ultimate console!", "Would love a PS5!", "PlayStation forever!"],
    'xbox':         ["Xbox is amazing!", "Can't wait to play on Xbox!", "Love Xbox!"],
    'headphones':   ["Great headphones make all the difference!", "Love quality audio!", "Perfect for music lovers!"],

    # Home
    'kitchen':      ["Kitchen upgrade would be incredible!", "Love cooking in a great kitchen!", "Dream kitchen!"],
    'grill':        ["Grilling season is the best!", "Love a good grill!", "Perfect backyard upgrade!"],
    'patio':        ["Perfect for backyard gatherings!", "Patio of my dreams!", "Love outdoor entertaining!"],
    'furniture':    ["Beautiful furniture!", "Would love to upgrade my home!", "Love quality furniture!"],
    'appliance':    ["New appliances would be a dream!", "Time for an upgrade!", "Love new appliances!"],
    'mattress':     ["Great sleep is so important!", "Would love a new mattress!", "Sleep upgrade!"],

    # Food/Beverage
    'coffee':       ["Coffee is life!", "Love a great cup of coffee!", "Coffee makes everything better!"],
    'wine':         ["Great wine selection!", "Love a good glass of wine!", "Wine lovers unite!"],
    'beer':         ["Love craft beer!", "Cheers!", "Great brew!"],
    'restaurant':   ["Always love a good meal out!", "Restaurants are the best!", "Date night sorted!"],
    'food':         ["Food lovers unite!", "Always up for great food!", "Love this!"],

    # Cash / Gift Cards
    'cash':         ["Would put this to great use!", "Cash is always perfect!", "Love it!"],
    'gift card':    ["Love this brand!", "Perfect prize!", "Great gift card!"],
    'amazon':       ["Amazon has everything I need!", "Love shopping on Amazon!", "Perfect prize!"],

    # Outdoor / Recreation
    'camping':      ["Love camping!", "Perfect camping gear!", "Camping is the best!"],
    'fishing':      ["Fishing is my favorite hobby!", "Love being on the water!", "Best fishing setup!"],
    'hunting':      ["Outdoor adventures are the best!", "Love hunting!", "Great gear!"],
    'bike':         ["Biking is my favorite way to stay fit!", "Love cycling!", "Great bike!"],
    'kayak':        ["Kayaking is amazing!", "Love being on the water!", "Perfect for the lake!"],

    # Pets
    'dog':          ["My dog would love this!", "Such a great prize for dog lovers!", "Dogs are the best!"],
    'cat':          ["My cat would love this!", "Cat lovers unite!", "Purr-fect!"],
    'pet':          ["Pets deserve the best!", "My fur baby would love this!", "Love this!"],

    # Music / Entertainment
    'concert':      ["Live music is the best!", "Would love to see this show!", "Can't wait!"],
    'movie':        ["Movie lover here!", "Would love these tickets!", "Movies are the best!"],
    'guitar':       ["Music is everything!", "Love playing guitar!", "Beautiful instrument!"],

    # Sports
    'golf':         ["Golf is my favorite sport!", "Love hitting the course!", "Perfect golf prize!"],
    'fitness':      ["Fitness goals!", "Love staying active!", "Great workout gear!"],
}


GENERIC_FALLBACK = [
    "I'd love to win this!",
    "What an amazing prize!",
    "Such a great giveaway — fingers crossed!",
    "Thanks for the opportunity!",
    "This would be incredible to win!",
    "Awesome prize!",
    "Love this — thanks for hosting!",
    "What a great contest!",
]


def generate_comment(sweepstake_name: str) -> str:
    """Match keywords in the sweepstakes name and return a relevant enthusiastic comment."""
    if not sweepstake_name:
        return random.choice(GENERIC_FALLBACK)

    name_lower = sweepstake_name.lower()
    matches = []
    for keyword, templates in COMMENT_TEMPLATES.items():
        if keyword in name_lower:
            matches.extend(templates)

    if matches:
        return random.choice(matches)
    return random.choice(GENERIC_FALLBACK)


# Field-name patterns that indicate a comment/why-you-want-to-win box
COMMENT_FIELD_KEYWORDS = [
    'comment', 'message', 'feedback', 'why', 'opinion', 'review', 'share',
    'thoughts', 'story', 'reason', 'tellus', 'tell_us', 'tell-us', 'explain',
    'describe', 'essay', 'response', 'answer'
]


def is_comment_field(combined_attrs: str) -> bool:
    """Check if a textarea/input looks like a comment field based on its attributes."""
    if not combined_attrs:
        return False
    combined = combined_attrs.lower()
    # Exclude address-like fields that might also have 'message' in them
    if any(skip in combined for skip in ['address', 'street_2', 'address2', 'apt']):
        return False
    return any(k in combined for k in COMMENT_FIELD_KEYWORDS)
