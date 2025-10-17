from src.ConsentManager import ConsentManager

def main():
    consent = ConsentManager()

    # Uncomment two lines below to reset consent for testing
    # from src.ConfigManager import ConfigManager
    # ConfigManager().delete("user_consent")

    if not consent.require_consent():
        print("Consent not given. Exiting program.")
        return
    # if answer is yes, consent persists
    # if answer is no, will re ask for consent each time
    print("Consent confirmed in main.")

    

if __name__ == "__main__":
    main()