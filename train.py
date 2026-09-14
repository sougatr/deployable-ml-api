import joblib
from sklearn.datasets import load_iris
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

def train_and_save():
    print("Loading data...")
    data = load_iris()
    X, y = data.data, data.target

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    print("Training Random Forest model...")
    clf = RandomForestClassifier(n_estimators=50, random_state=42)
    clf.fit(X_train, y_train)

    accuracy = clf.score(X_test, y_test)
    print(f"Model test accuracy: {accuracy:.4f}")

    # Save the trained model and target class names
    artifact = {
        "model": clf,
        "target_names": data.target_names.tolist()
    }
    joblib.dump(artifact, "model.joblib")
    print("Model saved to model.joblib successfully.")

if __name__ == "__main__":
    train_and_save()
