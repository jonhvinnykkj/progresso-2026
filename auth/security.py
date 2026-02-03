"""
Modulo de seguranca - Hash de senhas
Dashboard Financeiro - Grupo Progresso
"""
import hashlib
import hmac
import os


def gerar_hash_senha(senha: str) -> str:
    """
    Gera hash seguro da senha usando PBKDF2-HMAC-SHA256.
    Salt aleatorio de 32 bytes.
    Retorna string no formato: salt_hex$hash_hex
    """
    salt = os.urandom(32)
    hash_bytes = hashlib.pbkdf2_hmac(
        'sha256',
        senha.encode('utf-8'),
        salt,
        iterations=260000
    )
    return f"{salt.hex()}${hash_bytes.hex()}"


def verificar_senha(senha: str, senha_hash: str) -> bool:
    """
    Verifica se a senha corresponde ao hash armazenado.
    Usa compare_digest para prevenir timing attacks.
    """
    try:
        salt_hex, hash_hex = senha_hash.split('$')
        salt = bytes.fromhex(salt_hex)
        hash_esperado = bytes.fromhex(hash_hex)
        hash_calculado = hashlib.pbkdf2_hmac(
            'sha256',
            senha.encode('utf-8'),
            salt,
            iterations=260000
        )
        return hmac.compare_digest(hash_calculado, hash_esperado)
    except (ValueError, AttributeError):
        return False


def validar_forca_senha(senha: str) -> tuple[bool, str]:
    """
    Valida forca da senha.
    Retorna (valida, mensagem).
    """
    if not senha or len(senha) < 6:
        return False, "A senha deve ter no minimo 6 caracteres."
    return True, ""
