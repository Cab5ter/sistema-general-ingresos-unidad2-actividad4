"""Identidad de una membresía firmada por el servidor; permisos siempre en la BD."""
import jwt
from . import models as m
from .service import fail


def leer_actor(db, settings, headers):
    """Verifica HS256, vencimiento y coherencia empresa-membresía en cada petición."""
    authorization = headers.get('authorization', '')
    try:
        scheme, token = authorization.split()
        if scheme.lower() != 'bearer':
            raise ValueError
        payload = jwt.decode(token, settings.jwt_secret, algorithms=['HS256'],
                             options={'require': ['companyUserId', 'companyId', 'exp']})
        if any(type(payload[key]) is not int or payload[key] <= 0
               for key in ('companyUserId', 'companyId', 'exp')):
            raise ValueError
    except (jwt.PyJWTError, ValueError, TypeError, KeyError, AttributeError):
        fail('Token ausente, inválido o expirado.', 'UNAUTHENTICATED')
    member = db.get(m.CompanyUser, payload['companyUserId'])
    if member is None or member.company_id != payload['companyId']:
        fail('El token no identifica una membresía de esa empresa.', 'UNAUTHENTICATED')
    from .access import membership
    return membership(db, member.id)
