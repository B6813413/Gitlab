from flask import Flask, render_template

app = Flask(__name__)


@app.get("/")
def index():
    return render_template("index.html", values={"vbe": "0.7"}, errors=None, result=None)


if __name__ == "__main__":
    app.run(debug=True)
