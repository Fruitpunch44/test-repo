import requests
from flask import Flask, render_template
import json
import os
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

ACCESS_TOKEN = os.getenv('AccessToken')
if not ACCESS_TOKEN:
    raise ValueError("environ var not set")


def send_req(subject: str, year: int) -> dict:
    headers = {'Accept': 'application/json',
               'Content-Type': 'application/json',
               'AccessToken': ACCESS_TOKEN}
    try:
        REQUEST = requests.get(f"https://questions.aloc.com.ng/api/v2/q/40?subject={subject}&year={year}",
                               headers=headers)
        if REQUEST.status_code == 200:
            print('success')
            return REQUEST.json()

    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
        print(f'an error {e} occurred')


@app.route('/english')
def index():
    sub = 'english'
    year = 2010
    res = send_req(sub, year)
    return render_template('test.html', data=res)


@app.route('/chemistry')
def chem_page():
    sub = 'chemistry'
    year = 2010
    res = send_req(sub, year)
    return render_template('test.html', data=res)


@app.route('/biology')
def biology_page():
    sub = 'biology'
    year = 2010
    res = send_req(sub, year)
    return render_template('test.html', data=res)


@app.route('/mathematics')
def math_page():
    sub = 'mathematics'
    year = 2010
    res = send_req(sub, year)
    return render_template('test.html', data=res)


if __name__ == "__main__":
    app.run(debug=True)
