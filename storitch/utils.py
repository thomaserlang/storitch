import hashlib

def path_from_hash(hash_, levels=2, length=2):
    '''
    1b4f0e9851971998e732078544c96b36c3d01cedf7caa332359d6f1d83567014

    Will give the following path:

        /1b/4f

    We do this to minimize the number of files per folder.

    If we divide each folder with a length of 2 in 2 levels 
    we would get: 256 folders per level. So a total of 
    65,536 folders.

        256*256 = 65,536 folders

    If we store 20,000,000 files there should be an average of 
    305 files per folder
        
        20,000,000/65,536 ≈ 305 files per folder.

    :param hash_: str
    :param levels: int
        the number of sub folders
    :param length: int
        number of chars per folder
    :returns: str
        path to the file:

        Example:

            /1b/4f
    '''
    path = []
    for i in range(0, levels):
        path.append(hash_[i*length:(i*length)+length])
    return '/'.join(path)

def file_sha256(path, chunk_size=128*1024):
    h  = hashlib.sha256()
    b  = bytearray(chunk_size)
    mv = memoryview(b)
    with open(path, 'rb', buffering=0) as f:
        for n in iter(lambda : f.readinto(mv), 0):
            h.update(mv[:n])
    return h.hexdigest()