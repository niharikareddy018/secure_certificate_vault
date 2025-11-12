from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Hello from Flask on Vercel!"

# for Vercel
def handler(event, context):
    return app(event, context)
