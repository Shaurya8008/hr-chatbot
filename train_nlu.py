import json
import os
import pickle
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import make_pipeline

def train_and_save_model():
    print("Loading dataset: hr_intents.json...")
    
    with open("hr_intents.json", "r") as f:
        data = json.load(f)
        
    X = []
    y = []
    
    for intent_data in data["intents"]:
        intent = intent_data["intent"]
        for phrase in intent_data["phrases"]:
            X.append(phrase)
            y.append(intent)
            
    print(f"Loaded {len(X)} training samples across {len(set(y))} intents.")
    
    print("Training TF-IDF + Naive Bayes Pipeline...")
    model = make_pipeline(TfidfVectorizer(ngram_range=(1, 2)), MultinomialNB())
    model.fit(X, y)
    
    # Evaluate simply
    accuracy = model.score(X, y)
    print(f"Training Accuracy: {accuracy * 100:.2f}%")
    
    # Save the model
    with open("intent_model.pkl", "wb") as f:
        pickle.dump(model, f)
        
    print("Model saved successfully as intent_model.pkl")

if __name__ == "__main__":
    train_and_save_model()
