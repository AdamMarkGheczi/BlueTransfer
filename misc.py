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