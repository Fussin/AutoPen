import re

# Priority levels
CRITICAL = 1
HIGH = 2
MEDIUM = 3
LOW = 4

# These are examples of patterns that could be used to classify assets.
# In a real-world scenario, these would be much more comprehensive.
PRIORITY_PATTERNS = {
    CRITICAL: [
        r'/login', r'/auth', r'/admin', r'/payment', r'/upload',
        r'api/v\d+/users/login', r'api/v\d+/payments'
    ],
    HIGH: [
        r'/search', r'/profile', r'/settings', r'/dashboard',
        r'/api/v\d+/search', r'/api/v\d+/data'
    ],
    MEDIUM: [
        r'/static', r'/info', r'/docs', r'/support', r'/blog',
        r'/\?.*=', # URLs with parameters
    ],
    LOW: [
        r'\.js$', r'\.css$', r'\.png$', r'\.jpg$', r'\.gif$',
        r'/robots\.txt$', r'/sitemap\.xml$'
    ]
}

def classify_asset(asset_value):
    """
    Classifies an asset based on its value (e.g., URL, path) and returns a priority level.

    Args:
        asset_value (str): The value of the asset to classify.

    Returns:
        int: The priority level (1-4).
    """
    for priority, patterns in PRIORITY_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, asset_value, re.IGNORECASE):
                return priority
    return LOW # Default to low priority
