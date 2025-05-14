import hashlib

senha = "Senha@123"
hash_md5 = hashlib.md5(senha.encode('utf-8')).hexdigest()

print(hash_md5)