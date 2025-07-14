import tomllib


def test_version():
    from src.main import __version__

    with open("pyproject.toml", "rb") as f:
        pyproject = tomllib.load(f)
    project_version = pyproject["project"]["version"]
    assert project_version == __version__
