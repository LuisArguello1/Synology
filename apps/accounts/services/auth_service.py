"""
Servicio para obtener datos de Synology del usuario actual.
"""

def get_synology_session(request):
    """
    Obtiene SID y Token de la sesión Django.
    
    Returns:
        dict: {'sid': str, 'token': str, 'username': str} o None
    """
    sid = request.session.get('synology_sid')
    token = request.session.get('synology_token')
    username = request.session.get('synology_username')
    
    if sid:
        return {
            'sid': sid,
            'token': token,
            'username': username
        }
    return None


def has_valid_synology_session(request):
    """
    Verifica si el usuario tiene sesión válida de Synology (o al menos SID).
    """
    return request.session.get('synology_sid') is not None
