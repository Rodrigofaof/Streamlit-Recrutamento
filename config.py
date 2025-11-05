import os, json
from dotenv import load_dotenv

load_dotenv()

def _parse_list(raw: str):
    """Aceita JSON list, CSV ou string única. Retorna sempre lista de strings sem vazios."""
    if not raw:
        return []
    s = raw.strip()

    # JSON list/tuple
    if (s.startswith("[") and s.endswith("]")) or (s.startswith("(") and s.endswith(")")):
        try:
            data = json.loads(s)
            if isinstance(data, (list, tuple)):
                return [str(x).strip() for x in data if str(x).strip()]
        except Exception:
            pass

    # Fallback CSV / espaços / ponto e vírgula
    out = []
    for sep in [",", ";"]:
        s = s.replace(sep, " ")
    for token in s.split():
        token = token.strip()
        if token:
            out.append(token)
    return out

DB = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
}

# Compat: se EMAIL_TO vazio, tenta EMAIL_RECIPIENT (legado)
_email_to = os.getenv("EMAIL_TO", "") or os.getenv("EMAIL_RECIPIENT", "")

EMAIL = {
    "sender": os.getenv("EMAIL_SENDER"),
    "password": os.getenv("EMAIL_APP_PASSWORD"),
    "to": _parse_list(_email_to),
    "cc": _parse_list(os.getenv("EMAIL_CC", "")),
    "bcc": _parse_list(os.getenv("EMAIL_BCC", "")),
    "subject": os.getenv("EMAIL_SUBJECT", "Recruitment Needs"),
}

PATHS = {
    "locals_csv": os.getenv("LOCALS_CSV", "Locals.csv"),
}

CURRENCY = {
    "api_key": os.getenv("CURRENCY_API_KEY"),
    "base_url": os.getenv("CURRENCY_API_BASE", "http://apilayer.net/api/live"),
}
