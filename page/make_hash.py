import bcrypt

pw = input("Password:").encode("utf-8")
hashed = bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8")
print("bcrypt hash:\n", hashed)