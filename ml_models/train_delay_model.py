import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import joblib, random

random.seed(42)
np.random.seed(42)

origins = ['KGL', 'NBO', 'ADD', 'JNB', 'DXB', 'CDG', 'LHR', 'AMS']
destinations = ['KGL', 'NBO', 'ADD', 'JNB', 'DXB', 'CDG', 'LHR', 'AMS']
aircraft_types = ['B737', 'A320', 'B777', 'A350', 'E190']

N = 5000
rows = []
for _ in range(N):
    origin = random.choice(origins)
    destination = random.choice([d for d in destinations if d != origin])
    day_of_week = random.randint(0, 6)
    hour = random.randint(0, 23)
    aircraft_age = random.randint(0, 25)
    weather_severity = random.randint(0, 5)  # 0 = clear, 5 = severe

    # Synthetic ground truth: delays more likely with bad weather, peak hours, old aircraft
    delay_score = (weather_severity * 0.18 + (1 if hour in [6, 7, 17, 18, 19] else 0) * 0.15 +
                   (aircraft_age / 25) * 0.12 + (1 if day_of_week in [4, 5] else 0) * 0.08 +
                   random.uniform(0, 0.3))
    delayed = 1 if delay_score > 0.45 else 0
    rows.append([origin, destination, day_of_week, hour, aircraft_age, weather_severity, delayed])

df = pd.DataFrame(rows, columns=['origin', 'destination', 'day_of_week', 'hour',
                                  'aircraft_age', 'weather_severity', 'delayed'])

le_origin = LabelEncoder().fit(df['origin'])
le_dest = LabelEncoder().fit(df['destination'])
df['origin_enc'] = le_origin.transform(df['origin'])
df['dest_enc'] = le_dest.transform(df['destination'])

X = df[['origin_enc', 'dest_enc', 'day_of_week', 'hour', 'aircraft_age', 'weather_severity']]
y = df['delayed']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

model = RandomForestClassifier(n_estimators=200, max_depth=8, random_state=42)
model.fit(X_train, y_train)

y_pred = model.predict(X_test)
print("Accuracy :", accuracy_score(y_test, y_pred))
print("Precision:", precision_score(y_test, y_pred))
print("Recall :", recall_score(y_test, y_pred))
print("F1 score :", f1_score(y_test, y_pred))

joblib.dump(model, 'ml_models/delay_model.joblib')
joblib.dump({'origin': le_origin, 'destination': le_dest}, 'ml_models/delay_encoders.joblib')

print("Model and encoders saved to ml_models/")