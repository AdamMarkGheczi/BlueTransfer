from hashlib import sha1

def convert_file_size(bytes):
    if bytes < 1024:
        return f"{bytes} B"
    
    bytes = bytes / 1024
    
    if bytes < 1024:
        return f"{(bytes):.2f} KB"
    
    bytes = bytes / 1024
    
    if bytes < 1024:
        return f"{(bytes):.2f} MB"
    
    bytes = bytes / 1024

    if bytes < 1024:
        return f"{(bytes):.2f} GB"
    
    bytes = bytes / 1024
    
    if bytes < 1024:
        return f"{(bytes):.2f} TB"
    
    bytes = bytes / 1024


def sha1_chunks(file_path):
    BUF_SIZE = 65536
    hashing_algo = sha1()
    with open(file_path, 'rb') as f:
        while True:
            data = f.read(BUF_SIZE)
            if not data:
                break
            hashing_algo.update(data)
    
    return hashing_algo.hexdigest()