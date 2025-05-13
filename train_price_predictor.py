import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import joblib

# Load and clean
df = pd.read_csv("sentiment_history.csv", parse_dates=["Timestamp"])
df = df[df["Coin"] == "Bitcoin"]  # start with Bitcoin
df = df.sort_values("Timestamp")

# Combine Reddit + News sentiment
sentiment_avg = (
    df.groupby("Timestamp")
      .agg({"Sentiment": "mean", "PriceUSD": "mean"})
      .rename(columns={"Sentiment": "AvgSentiment", "PriceUSD": "Price"})
)

# Add target: future price delta
sentiment_avg["FuturePrice"] = sentiment_avg["Price"].shift(-1)
sentiment_avg["Target"] = (sentiment_avg["FuturePrice"] > sentiment_avg["Price"]).astype(int)
sentiment_avg.dropna(inplace=True)

# Features & labels
X = sentiment_avg[["AvgSentiment"]]
y = sentiment_avg["Target"]

# Split & train
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)

model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# Save model
joblib.dump(model, "price_predictor.pkl")

# Report
y_pred = model.predict(X_test)
print(classification_report(y_test, y_pred))
