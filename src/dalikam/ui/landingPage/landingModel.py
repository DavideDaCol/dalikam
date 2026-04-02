class landingModel:
    
    def __init__(self):
        self.settings: dict = {"test": "True"}
        print("landing page model initialized")

    def get_settings(self) -> dict:
        return self.settings