import firebase

# Firebase configuration
config = {
    "apiKey": "AIzaSyBX_nGfqOKq9t4G1200krLBsmm3XscJGsI",
    "authDomain": "gothub-dataengine.firebaseapp.com",
    "databaseURL": "https://gothub-dataengine-default-rtdb.firebaseio.com",
    "projectId": "gothub-dataengine",
    "storageBucket": "gothub-dataengine.appspot.com",
    "messagingSenderId": "752753357845",
    "appId": "1:752753357845:web:dbb61366b8df0c67440a1c",
    "measurementId": "G-TYR0BJFRTG",
}


# Instantiates a Firebase app
app = firebase.initialize_app(config)


auth = app.auth()
db = app.database()
firestore = app.firestore()
