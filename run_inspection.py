"""Run the inspection web app standalone."""

import uvicorn
from inspection.config import APP_HOST, APP_PORT
from inspection.app import app  # noqa: F401 – triggers db.init_db()

if __name__ == "__main__":
    print(f"Starting inspection app on http://{APP_HOST}:{APP_PORT}")
    uvicorn.run("inspection.app:app", host=APP_HOST, port=APP_PORT, reload=False)
