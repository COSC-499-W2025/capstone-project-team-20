from src.managers.ConfigManager import ConfigManager

class ConsentManager:
    """
    Manages user consent for how their files are to be analyzed.

    Consent is stored in the database using ConfigManager under the key "user_consent".
    This class provides methods to check, request, and enforce consent.
    """

    def __init__(self, db_path="config.db"):
        self.manager = ConfigManager(db_path=db_path)

    def set_consent(self, consent: bool):
        self.manager.set("user_consent", bool(consent))

    def has_user_consented(self):
        """
        Check if the user has previously given consent.

        Returns: `True` if the user has consented, `False` otherwise.
        """
        has_consented = self.manager.get("user_consent") 
        return has_consented is True

    def request_consent(self):
        """
        Prompt the user for consent to run the program and record the response.

        Accepts "yes", "y" (case-insensitive) as consent. Any other input is treated as denial.

        Returns: `True` if the user has given consent, `False` otherwise.
        """
        print("Do you give consent to scan your files?")
        answer = input("(yes/no)")
        answer = answer.strip().lower() 
        consent = answer in ("yes", "y")

        self.set_consent(consent) #Updated method for API usage

        if consent:
            print("Consent recorded in ConsentManager. Thankyou!")
        else:
            print("Consent recorded in ConsentManager. Program aborted.")
        return consent
    
    def require_consent(self):
        """
        Ensure that the user has given consent before proceeding.

        The return value can be used to control program flow.

        Returns: `True` if the user has previously consented or has now given consent, `False` otherwise.
        """
        if not self.has_user_consented():
            return self.request_consent()
        return True


    