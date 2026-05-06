# create_user.py
# Herramienta de línea de comandos para agregar usuarios al diccionario USERS_DB
# Uso: python create_user.py
#
# En producción, reemplaza USERS_DB por una tabla en tu base de datos SQL Server.

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

if __name__ == "__main__":
    username = input("Nombre de usuario: ").strip()
    password = input("Contraseña: ").strip()
    role = input("Rol (admin/user) [user]: ").strip() or "user"

    hashed = pwd_context.hash(password)
    print("\n--- Copia esta entrada en el diccionario USERS_DB de main.py ---")
    print(f"""
    "{username}": UserInDB(
        username="{username}",
        hashed_password="{hashed}",
        role="{role}",
    ),
""")