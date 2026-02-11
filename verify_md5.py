
import hashlib
import sys

def test_hashing():
    print("Testing MD5 Hashing...")
    password = "my_secure_password"
    expected_hash = hashlib.md5(password.encode()).hexdigest()
    print(f"Password: {password}")
    print(f"Hash: {expected_hash}")
    
    # Simulate Save
    saved_password = hashlib.md5(password.encode()).hexdigest()
    
    # Simulate Check
    input_password = "my_secure_password"
    input_hash = hashlib.md5(input_password.encode()).hexdigest()
    
    if input_hash == saved_password:
        print("PASS: Password verification successful (MD5 match).")
    else:
        print("FAIL: Password verification failed.")
        sys.exit(1)

    # Simulate Legacy Check (Plain text stored)
    legacy_stored = "my_secure_password"
    input_hash = hashlib.md5(input_password.encode()).hexdigest()
    
    if input_hash == legacy_stored:
        print("FAIL: Legacy check shouldn't match hash to plain.") 
    elif input_password == legacy_stored:
        print("PASS: Legacy verification successful (Plain text match).")
    else:
         print("FAIL: Legacy verification failed.")

if __name__ == "__main__":
    test_hashing()
