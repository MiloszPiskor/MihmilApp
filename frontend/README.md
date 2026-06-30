# Frontend

This React application depends on the Flask backend exposing CORS for the frontend origin. Ensure Flask is configured with `flask-cors` or equivalent middleware so the browser can perform requests to the backend.

Example Flask CORS setup:

```python
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
```
