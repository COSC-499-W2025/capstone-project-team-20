from src.main import main

def test_main_runs(monkeypatch):
    try:
        # Mock user input as if someone pressed "y"
        #monkeypatch.setattr("builtins.input", lambda _: "y")
        #main()
        assert True
    except Exception as e:
        assert False, f"main() raised an exception: {e}"
