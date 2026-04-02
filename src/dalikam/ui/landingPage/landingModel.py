class LandingModel:
    
    def __init__(self):
        self.settings: dict[str,str] = {"test": "True"}
        print("landing page model initialized")

    def get_settings(self) -> dict[str,str]:
        return self.settings