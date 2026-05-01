from core.security import hash_password, verify_password

hashed = hash_password("anjay17768")

print(hashed)  # hash panjang

print(verify_password("anjay17768", hashed))  # True
print(verify_password("salah", hashed))   # False