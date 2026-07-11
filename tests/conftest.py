import pytest
import importlib.util

@pytest.fixture
def tmp(tmp_path):
    return str(tmp_path)

@pytest.fixture
def orig(request):
    try:
        return request.module.load_original()
    except Exception as e:
        pytest.skip(f"Original factory script not found: {e}")
