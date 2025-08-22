ignore_errors = [
    'length and filesize do not match',
]


def ignore_error(error: str) -> bool:
    return any(err in error.lower() for err in ignore_errors)
