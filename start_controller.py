# controller/start_controller.py

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


import uvicorn

if __name__ == "__main__":
    uvicorn.run("api.main:app", host="0.0.0.0", port=9000, reload=True, workers=1)
