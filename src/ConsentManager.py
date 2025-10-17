from src.ConfigManager import ConfigManager

class ConsentManager:

    def __init__(self, db_path="config.db"):
        self.manager = ConfigManager(db_path=db_path)

    def has_user_consented(self):
        #check if user has previously consented to allowing program to run
        has_consented = self.manager.get("user_consent") 
        return has_consented is True

    def request_consent(self):
        print("Do you give consent to scan your files?")
        answer = input("(yes/no)")
        answer = answer.strip().lower() 
        #allows yes, y and strips leading/trailing characters from String entered
        consent = answer in ("yes", "y")

        self.manager.set("user_consent", consent)
        if consent:
            print("Consent recorded in ConsentManager. Thankyou!")
        else:
            print("Consent recorded in ConsentManager. Program aborted.")
        return consent
    
    def require_consent(self):
        if not self.has_user_consented():
            return self.request_consent()
        return True


    