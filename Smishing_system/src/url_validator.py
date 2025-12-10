"""
URL Validator Module
Validate và parse URLs

Functions:
- validate_url(url)
- extract_domain(url)
- get_tld(domain)
"""

import re
from urllib.parse import urlparse

def extract_domain(url):
    """Extract domain from URL"""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path
        return domain
    except:
        return None

# TODO: Add more validation functions
