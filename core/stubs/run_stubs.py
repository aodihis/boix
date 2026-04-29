import os
import threading

from dotenv import load_dotenv

load_dotenv()


def run_stubs() -> None:
    fm_port = int(os.environ.get("FM_STUB_PORT", "5001"))
    craft_port = int(os.environ.get("CRAFT_STUB_PORT", "5002"))

    from stubs.filemaker_stub import app as fm_app
    from stubs.craftcms_stub import app as craft_app

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

    print(f"FileMaker stub running on port {fm_port}")
    print(f"Craft CMS stub running on port {craft_port}")

    threading.Event().wait()


if __name__ == "__main__":
    run_stubs()
