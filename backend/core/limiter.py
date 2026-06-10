from slowapi import Limiter
from slowapi.util import get_remote_address

# Limiter global, cheie = adresa IP a clientului (storage in-memory).
# Modul separat pentru a evita importurile circulare: atât main.py cât și
# api/auth.py au nevoie de aceeași instanță.
limiter = Limiter(key_func=get_remote_address)
