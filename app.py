import identity.web
import requests
import os
import json
from flask import Flask, redirect, render_template, request, session, url_for
from flask_session import Session
import random

# The following variables are required for the app to run.

with open("secrets.json") as f:
    data = dict(json.load(f))
    CLIENT_ID = data.get("CLIENT_ID")
    CLIENT_SECRET = data.get("CLIENT_SECRET")
    AUTHORITY = data.get("TENANT_ID")

SESSION_SECRET = os.urandom(24).hex()

SCOPES = ["User.Read", "User.ReadBasic.All", "User.ReadWrite"]

REDIRECT_URI = "http://localhost:5000/getAToken"

REDIRECT_PATH = "/getAToken"

app = Flask(__name__)

app.config['SECRET_KEY'] = SESSION_SECRET
app.config['SESSION_TYPE'] = 'filesystem'
app.config['TESTING'] = True
app.config['DEBUG'] = True
Session(app)

# The auth object provide methods for interacting with the Microsoft OpenID service.
# but it's gone unused in this implementation
auth = identity.web.Auth(session=session,
                        authority=AUTHORITY,
                        client_id=CLIENT_ID,
                        client_credential=CLIENT_SECRET)

@app.route("/login")
def login():
    # this doesn't use the auth library due to not being able to find working documentation
    # whilst we found out how to generate the url directly
    auth_url = "".join([
        f"https://login.microsoftonline.com/{AUTHORITY}/oauth2/v2.0/authorize",
        f"?client_id={CLIENT_ID}",
        f"&response_type=code",
        f"&redirect_uri={REDIRECT_URI}",
        f"&response_mode=query",
        f"&scope={' '.join(SCOPES)}",
    ])
    print(auth_url)
    return redirect(auth_url)


@app.route(REDIRECT_PATH)
def auth_response():
    code = request.args.get("code")
    
    token_response = requests.post(
        f"https://login.microsoftonline.com/{AUTHORITY}/oauth2/v2.0/token",
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code",
            "scope": ' '.join(SCOPES)
        }
    )
    
    if token_response.status_code == 200:
        session["access_token"] = token_response.json().get("access_token")
    else:
        return "Error retrieving access token", 400

    return redirect("/")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/")
def index():
    user = None
    greeting = None
    
    if "access_token" in session:
        user = requests.get(
            "https://graph.microsoft.com/v1.0/me",
            headers={"Authorization": f"Bearer {session['access_token']}"}
        ).json()
        
        greeting = random.choice([
            f"Hello {user['displayName']}, it's great to have you here!",
            f"Welcome, {user['displayName']}! Hope you're having a wonderful day!",
            f"Greetings {user['displayName']}! Wonderful to see you!",
            f"Hey {user['displayName']}, welcome aboard!",
            f"Welcome, {user['displayName']}! Let's get started!",
        ])
    
    return render_template('index.html', user=user, greeting=greeting)


@app.route("/profile", methods=["GET"])
def get_profile():
    if "access_token" not in session:
        return render_template('restricted_page.html')

    result = requests.get(
        "https://graph.microsoft.com/v1.0/me",
        headers={'Authorization': f'Bearer {session["access_token"]}'}
    )

    return render_template('profile.html', user=result.json(), result=None)


@app.route("/profile", methods=["POST"])
def post_profile():
    if "access_token" not in session:
        return render_template('restricted_page.html')
    
    ID = requests.get(
        "https://graph.microsoft.com/v1.0/me",
        headers={'Authorization': f'Bearer {session["access_token"]}'}
    ).json().get("id")
    
    # this is terrible, but it works
    if not ID:
        profile = requests.get(
            "https://graph.microsoft.com/v1.0/me",
            headers={'Authorization': f'Bearer {session["access_token"]}'}
        )
        
        return render_template('profile.html',
                        user=profile.json(),
                        result="Failed to fetch your user ID")

        
    result = requests.patch(
        f"https://graph.microsoft.com/v1.0/users/{ID}",
        json=request.form.to_dict(),
        headers={'Authorization': f'Bearer {session["access_token"]}'}
    )

    profile = requests.get(
        "https://graph.microsoft.com/v1.0/me",
        headers={'Authorization': f'Bearer {session["access_token"]}'}
    )
    
    return render_template('profile.html',
                            user=profile.json(),
                            result=result)


@app.route("/users")
def get_users():
    if "access_token" not in session:
        return render_template('restricted_page.html')
    
    result = requests.get(
        "https://graph.microsoft.com/v1.0/users",
        headers={'Authorization': f'Bearer {session["access_token"]}'}
    )
    
    print(result.json())
    return render_template('users.html', result=result.json())


if __name__ == "__main__":
    app.run()
