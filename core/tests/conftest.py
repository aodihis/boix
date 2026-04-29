import os
import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def onix3_path() -> str:
    return str(FIXTURES_DIR / "onix3_sample.xml")


@pytest.fixture
def onix3_block_update_path() -> str:
    return str(FIXTURES_DIR / "onix3_block_update.xml")


@pytest.fixture
def onix21_path() -> str:
    return str(FIXTURES_DIR / "onix21_sample.xml")


@pytest.fixture
def onix3_shorttags_path() -> str:
    return str(FIXTURES_DIR / "onix3_shorttags_sample.xml")


@pytest.fixture
def onix21_shorttags_path() -> str:
    return str(FIXTURES_DIR / "onix21_shorttags_sample.xml")


@pytest.fixture(scope="session")
def db_conn():
    if not os.environ.get("DB_HOST"):
        pytest.skip("DB_HOST not set — skipping integration tests")
    import psycopg2
    from dotenv import load_dotenv

    load_dotenv()
    conn = psycopg2.connect(
        host=os.environ["DB_HOST"],
        port=os.environ.get("DB_PORT", "5432"),
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
    )
    yield conn
    conn.close()


@pytest.fixture(scope="session", autouse=True)
def start_stubs():
    if os.environ.get("USE_STUBS", "").lower() != "true":
        return

    from stubs.filemaker_stub import app as fm_app
    from stubs.craftcms_stub import app as craft_app

    fm_port = int(os.environ.get("FM_STUB_PORT", "5001"))
    craft_port = int(os.environ.get("CRAFT_STUB_PORT", "5002"))

    fm_thread = threading.Thread(
        target=lambda: fm_app.run(port=fm_port, use_reloader=False),
        daemon=True,
    )
    craft_thread = threading.Thread(
        target=lambda: craft_app.run(port=craft_port, use_reloader=False),
        daemon=True,
    )
    fm_thread.start()
    craft_thread.start()
