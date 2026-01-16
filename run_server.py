from flask import Flask, jsonify
from flask_cors import CORS
import re

app = Flask(__name__)
CORS(app, origins=re.compile(r'http://localhost:\d+|http://127\.0\.0\.1:\d+'))


@app.route('/api/news')
def get_news():
    return jsonify({'news': ['News 1', 'News 2', 'News 3']})


if __name__ == "__main__":
    app.run(port=5000, debug=True)
