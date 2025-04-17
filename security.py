from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes
import os
import platform
import hashlib
import stat

class SecurityManager:
    def __init__(self):
        self.key_location = self._get_key_location()
        
    def _get_key_location(self):
        """Returns obfuscated path to encryption key based on OS"""
        if platform.system() == 'Windows':
            base_dir = os.path.join(os.environ['USERPROFILE'], 'AppData', 'Local')
            hidden_dir = os.path.join(base_dir, 'sys_' + hashlib.md5(b'secure_store').hexdigest()[:8])
        else:  # Linux/Mac
            base_dir = os.path.join(os.path.expanduser('~'), '.config')
            hidden_dir = os.path.join(base_dir, '.' + hashlib.md5(b'secure_store').hexdigest()[:8])
        
        return os.path.join(hidden_dir, '.env_' + hashlib.md5(b'key').hexdigest()[:8])

    def _ensure_key_directory_exists(self):
        """Creates secure directory for key storage"""
        dir_path = os.path.dirname(self.key_location)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path, mode=0o700)
            if platform.system() != 'Windows':
                os.chmod(dir_path, 0o700)

    def generate_key(self):
        """Generates and stores a new encryption key"""
        self._ensure_key_directory_exists()
        key = get_random_bytes(32)
        
        with open(self.key_location, 'wb') as f:
            f.write(key)
        
        if platform.system() != 'Windows':
            os.chmod(self.key_location, 0o600)
        
        return key

    def get_key(self):
        """Retrieves the encryption key, generates if missing"""
        if not os.path.exists(self.key_location):
            return self.generate_key()
        
        with open(self.key_location, 'rb') as f:
            return f.read()

    def encrypt(self, data: str) -> str:
        """Encrypts data using AES-CBC with proper encoding"""
        key = self.get_key()
        cipher = AES.new(key, AES.MODE_CBC)
        
        # Ensure data is properly padded before encryption
        data_bytes = data.encode('utf-8')
        ct_bytes = cipher.encrypt(pad(data_bytes, AES.block_size))
        
        # Return IV + ciphertext as hex string
        return cipher.iv.hex() + ct_bytes.hex()

    def decrypt(self, encrypted_data: str) -> str:
        """Decrypts AES-CBC encrypted data"""
        try:
            key = self.get_key()

            # Split IV and ciphertext
            iv = bytes.fromhex(encrypted_data[:32])
            ct = bytes.fromhex(encrypted_data[32:])

            cipher = AES.new(key, AES.MODE_CBC, iv)
            return unpad(cipher.decrypt(ct), AES.block_size).decode('utf-8')
        except Exception as e:
            print(f"Decryption failed: {str(e)}")
            raise
    
    def rotate_key(self):
        """Generate new encryption key (destroys old encrypted values)"""
        self.generate_key()
        print("New encryption key generated. All existing encrypted values must be re-encrypted.")

    def test_encryption(self):
        """Test encryption/decryption roundtrip"""
        test_string = "TEST_STRING_123"
        encrypted = self.encrypt(test_string)
        decrypted = self.decrypt(encrypted)
        return decrypted == test_string