"""Execute the real Streamlit app and exercise meaningful widget changes."""

from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_dashboard_default_and_scenario():
    app = AppTest.from_file(str(Path(__file__).parents[1] / "app.py")).run(timeout=30)
    assert not app.exception
    assert len(app.metric) >= 5
    assert app.metric[4].value == "+0.00"
    app.slider[2].set_value(100).run(timeout=30)
    assert not app.exception
    assert app.metric[4].value.startswith("-")
    app.slider[0].set_value(10)
    app.slider[1].set_value(0.0)
    app.selectbox[0].set_value(4).run(timeout=30)
    assert not app.exception
