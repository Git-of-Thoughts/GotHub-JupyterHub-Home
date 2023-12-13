import firebase

# Firebase configuration
config = {
    "apiKey": "apiKey",
    "authDomain": "projectId.firebaseapp.com",
    "databaseURL": "https://databaseName.firebaseio.com",
    "projectId": "projectId",
    "storageBucket": "projectId.appspot.com",
    "messagingSenderId": "messagingSenderId",
    "appId": "appId",
}

# Instantiates a Firebase app
app = firebase.initialize_app(config)


# Firebase Authentication
auth = app.auth()
