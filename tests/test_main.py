from src.main import main

def test_main_runs():
    try:
        main()
        assert True
    except Exception as e:
        assert False, f"main() raised an exception: {e}"