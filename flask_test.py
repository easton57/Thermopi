from flask import Flask, request, json, render_template

app = Flask(__name__, template_folder='templates')


@app.route('/')
def index():
    return render_template('index.html')


if __name__ == '__main__':
    app.run(debug=True, port=5757, host='0.0.0.0', ssl_context='adhoc')