from unittest.mock import MagicMock, patch

from sqlmodel import select

from app.backend_pre_start import init


def test_init_successful_connection() -> None:
    engine_mock = MagicMock()
    session_mock = MagicMock()
    session_mock.__enter__.return_value = session_mock

    with patch(
        "app.backend_pre_start.Session", return_value=session_mock
    ) as session_factory:
        init(engine_mock)

    session_factory.assert_called_once_with(engine_mock)
    session_mock.exec.assert_called_once()
    statement = session_mock.exec.call_args.args[0]
    assert statement.compare(select(1))
