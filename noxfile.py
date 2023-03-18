# Third Party
import nox


@nox.session(python=["3.7", "3.8", "3.9", "3.10", "3.11"])
@nox.parametrize("wagtail", ["4.1", "4.2"])
@nox.parametrize("django", ["3.2", "4.0", "4.1"])
def test_compatibility(session, wagtail, django):
    session.install("-r", "requirements.txt")
    session.install("-r", "requirements.dev.txt")
    session.install(f"wagtail=={wagtail}")
    session.install(f"django=={django}")
    session.run("pytest")
