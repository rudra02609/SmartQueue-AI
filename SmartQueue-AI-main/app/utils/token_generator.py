import uuid

def generate_token(domain: str, service_code: str) -> str:
    """
    Example:
    Healthcare OPD -> H-O-123
    Banking Cash -> B-C-045
    """
    short_id = str(uuid.uuid4().int)[-3:]
    return f"{domain[0].upper()}-{service_code.upper()}-{short_id}"
