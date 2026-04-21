import re
import socket
import logging

logger = logging.getLogger(__name__)

# Regex RFC 5322 simplificada: local@dominio.tld (con posibilidad de subdominios)
# - local: letras, numeros y . _ % + -
# - dominio: letras, numeros y . -
# - tld: minimo 2 letras
EMAIL_REGEX = re.compile(
    r'^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$'
)

# Longitud maxima razonable
EMAIL_MAX_LEN = 254

# Dominios tipograficamente comunes que suelen ser errores
# (no los bloqueamos, pero los detectamos para sugerir correccion)
COMMON_TYPOS = {
    'gmial.com': 'gmail.com',
    'gmai.com': 'gmail.com',
    'gmal.com': 'gmail.com',
    'hotmial.com': 'hotmail.com',
    'hotnail.com': 'hotmail.com',
    'outlok.com': 'outlook.com',
    'yhaoo.com': 'yahoo.com',
    'yaho.com': 'yahoo.com',
}


def validate_email_format(email: str) -> tuple[bool, str]:
    """Valida que el email tenga formato valido.
    Devuelve (True, '') si es valido, (False, mensaje) si no."""
    if not email or not isinstance(email, str):
        return False, 'Email requerido'

    email = email.strip()

    if len(email) > EMAIL_MAX_LEN:
        return False, 'Email demasiado largo'

    if '@' not in email:
        return False, 'El email debe contener @'

    if email.count('@') != 1:
        return False, 'El email tiene un formato invalido'

    local, _, domain = email.partition('@')

    if not local:
        return False, 'Falta el usuario antes de la @'

    if not domain:
        return False, 'Falta el dominio despues de la @'

    if '.' not in domain:
        return False, 'El dominio debe contener un punto (ej: gmail.com)'

    if not EMAIL_REGEX.match(email):
        return False, 'El email tiene un formato invalido'

    # Detectar typos comunes y sugerir
    if domain.lower() in COMMON_TYPOS:
        return False, f'Quizas quisiste decir: {local}@{COMMON_TYPOS[domain.lower()]}'

    # TLD minimo de 2 letras
    tld = domain.rsplit('.', 1)[-1]
    if len(tld) < 2:
        return False, 'La extension del dominio debe tener al menos 2 letras'

    return True, ''


def validate_email_domain(email: str, timeout: float = 5.0, do_smtp_check: bool = False) -> tuple[bool, str]:

    if '@' not in email:
        return False, 'Email invalido'

    local_part, _, domain = email.partition('@')
    domain = domain.strip().lower()
    local_part = local_part.strip()

    # 1) Dominios desechables / temporales (ampliable)
    DISPOSABLE = {
        '10minutemail.com', '10minutemail.net', 'mailinator.com',
        'guerrillamail.com', 'guerrillamail.net', 'guerrillamail.org',
        'sharklasers.com', 'yopmail.com', 'trashmail.com',
        'tempmail.com', 'temp-mail.org', 'temp-mail.io',
        'dispostable.com', 'throwawaymail.com', 'getnada.com',
        'maildrop.cc', 'mintemail.com', 'mohmal.com',
        'emailondeck.com', 'fakemailgenerator.com', 'fakeinbox.com',
    }
    if domain in DISPOSABLE:
        return False, 'No se permiten correos temporales/desechables'

    # 2) MX lookup con dnspython
    mx_hosts = []
    try:
        import dns.resolver
        resolver = dns.resolver.Resolver()
        resolver.lifetime = timeout
        resolver.timeout = timeout
        try:
            answers = resolver.resolve(domain, 'MX')
            mx_hosts = sorted(
                [(r.preference, str(r.exchange).rstrip('.')) for r in answers]
            )
            if not mx_hosts:
                return False, f'El dominio "{domain}" no recibe correos'
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
            # Sin MX: probamos A como fallback
            try:
                resolver.resolve(domain, 'A')
                mx_hosts = [(0, domain)]
            except Exception:
                return False, f'El dominio "{domain}" no existe o no recibe correos'
        except dns.resolver.Timeout:
            logger.warning('DNS timeout al verificar dominio %s', domain)
            return True, ''  # no bloquear por timeout
    except ImportError:
        # dnspython no esta: solo fallback getaddrinfo
        pass
    except Exception as e:
        logger.warning('Error MX lookup %s: %s', domain, e)

    # 3) Fallback getaddrinfo si no se resolvieron MX
    if not mx_hosts:
        try:
            socket.setdefaulttimeout(timeout)
            socket.getaddrinfo(domain, None)
            mx_hosts = [(0, domain)]
        except socket.gaierror:
            return False, f'El dominio "{domain}" no existe'
        except Exception as e:
            logger.warning('Error resolviendo %s: %s', domain, e)
            return True, ''
        finally:
            socket.setdefaulttimeout(None)

    # 4) SMTP RCPT TO check (best-effort, puede devolver "desconocido")
    if do_smtp_check:
        ok_smtp, msg_smtp = _smtp_mailbox_check(mx_hosts, local_part, domain, timeout)
        if ok_smtp is False:
            return False, msg_smtp
        # ok_smtp == True o None (desconocido) -> aceptamos

    return True, ''


def _smtp_mailbox_check(mx_hosts, local_part, domain, timeout):
    import smtplib
    sender = 'verify@example.com'
    rcpt = f'{local_part}@{domain}'

    for preference, host in sorted(mx_hosts):
        try:
            server = smtplib.SMTP(timeout=timeout)
            server.connect(host, 25)
            server.helo('example.com')
            server.mail(sender)
            code, msg = server.rcpt(rcpt)
            try:
                server.quit()
            except Exception:
                pass

            # 250: buzon aceptado
            # 251: user not local, pero forwarding -> aceptado
            # 550/551/553: mailbox unavailable / no such user
            # 552: storage full
            # 450/451/452: problemas temporales
            if code in (250, 251):
                return True, ''
            if code in (550, 551, 553):
                txt = (msg.decode('utf-8', errors='ignore') if isinstance(msg, bytes) else str(msg)).lower()
                if any(kw in txt for kw in ('no such user', 'user unknown', 'mailbox unavailable',
                                            'recipient rejected', 'does not exist', 'user not found',
                                            'no mailbox', 'invalid recipient', 'address rejected')):
                    return False, 'El correo electronico no existe'
                return False, 'El correo electronico fue rechazado por el servidor destino'
            # Cualquier otro codigo: no concluyente
            return None, ''
        except (smtplib.SMTPConnectError, smtplib.SMTPServerDisconnected,
                smtplib.SMTPHeloError, ConnectionRefusedError,
                TimeoutError, OSError) as e:
            logger.debug('SMTP check fallo con %s: %s', host, e)
            continue
        except Exception as e:
            logger.warning('SMTP check inesperado %s: %s', host, e)
            continue

    # Ningun MX respondio: no concluyente (pero no bloqueamos)
    return None, ''


def validate_password_strength(password: str) -> tuple[bool, str, dict]:
    details = {
        'min_length': False,
        'has_lower': False,
        'has_upper': False,
        'has_digit': False,
        'has_symbol': False,
        'not_common': True,
    }

    if not password or not isinstance(password, str):
        return False, 'Contrasena requerida', details

    if password != password.strip():
        return False, 'La contrasena no puede empezar o terminar con espacios', details

    details['min_length'] = len(password) >= 8
    details['has_lower'] = bool(re.search(r'[a-z]', password))
    details['has_upper'] = bool(re.search(r'[A-Z]', password))
    details['has_digit'] = bool(re.search(r'[0-9]', password))
    details['has_symbol'] = bool(re.search(r'[^A-Za-z0-9]', password))

    common_passwords = {
        'password', '12345678', 'qwerty12', 'password1', 'password123',
        'admin123', 'abc12345', 'iloveyou', 'welcome1', 'letmein1',
        'contrasena', 'contrasena1', 'contrasena123',
        'biblioteca', 'biblioteca1', 'biblioteca123',
    }
    if password.lower() in common_passwords:
        details['not_common'] = False
        return False, 'Esta contrasena es demasiado comun. Elige una mas segura.', details

    if not details['min_length']:
        return False, 'La contrasena debe tener minimo 8 caracteres', details
    if not details['has_lower']:
        return False, 'La contrasena debe contener al menos una letra minuscula', details
    if not details['has_upper']:
        return False, 'La contrasena debe contener al menos una letra mayuscula', details
    if not details['has_digit']:
        return False, 'La contrasena debe contener al menos un numero', details
    if not details['has_symbol']:
        return False, 'La contrasena debe contener al menos un simbolo (ej: !@#$%)', details

    return True, '', details
