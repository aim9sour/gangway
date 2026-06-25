from gangway.main import hello


def test_hello():
    assert hello() == "Hello from gangway! The smart Agent-to-Server Bridge."
