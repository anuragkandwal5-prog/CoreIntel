def get_targets(q):
    return [
        ("GitHub", f"https://api.github.com/users/{q}"),
        ("Reddit", f"https://www.reddit.com/user/{q}/about.json"),
        ("Gravatar", f"https://en.gravatar.com/{q}.json"),
        ("Vimeo", f"https://vimeo.com/{q}"),
        ("Pinterest", f"https://www.pinterest.com/{q}/")
        # बाद में आप यहाँ और भी लिंक जोड़ सकते हैं
    ]
