#!/usr/bin/env python3
import os
import stat

secret = os.urandom(16).hex()
with open("/tmp/gen-secret.txt", "w") as f:
    f.write(secret + "\n")
    f.flush()
    os.fsync(f.fileno())
os.chmod("/tmp/gen-secret.txt", stat.S_IRUSR | stat.S_IWUSR)
print("SECRET=" + secret)
print("len=" + str(len(secret)))