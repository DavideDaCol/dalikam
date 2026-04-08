import os

class FileViewModel:

    def path_validity_check(self,path: str) -> bool:
            return os.path.exists(path)

    def page_loaded(self):
        print("yep")