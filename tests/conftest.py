"""Shared fixtures: an offline fake OpenAI client and an isolated inspection log."""

from unittest.mock import MagicMock

import pytest

from src.logger import InspectionLogger


@pytest.fixture
def fake_client() -> MagicMock:
    """client.chat.completions.create (Actor) and .parse (Critic) are configurable mocks."""
    return MagicMock()


@pytest.fixture
def log(tmp_path) -> InspectionLogger:
    """An inspection log in a temp dir, so tests never touch logs/inspection_log.json."""
    return InspectionLogger(tmp_path / "nested" / "inspection_log.json")
