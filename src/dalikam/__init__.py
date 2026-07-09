from dalikam.tools.utils import get_root

"""
    Gets rid of the temporary folder if the program isn't shut down gracefully 
"""
root = get_root()
old_tmp = root / ".tmp"
if old_tmp.exists():
    for file in old_tmp.glob("*"):
        file.unlink()
    old_tmp.rmdir()