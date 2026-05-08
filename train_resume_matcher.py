import pandas as pd
import pickle
from sklearn.feature_extraction.text import TfidfVectorizer

def train_and_save_resume_matcher():
    print("Loading jobs_dataset.csv...")
    try:
        df = pd.read_csv("jobs_dataset.csv")
    except Exception as e:
        print(f"Error loading dataset: {e}")
        return

    # The "corpus" is all job descriptions and skills combined
    # This allows the TF-IDF vectorizer to learn the vocabulary and IDF weights of the HR domain
    corpus = df["description"].fillna("") + " " + df["skills"].fillna("")
    
    print(f"Training TF-IDF Vectorizer on {len(corpus)} job documents...")
    vectorizer = TfidfVectorizer(stop_words='english', ngram_range=(1, 2), max_features=5000)
    
    # Fit the vectorizer on the corpus to learn the vocabulary
    vectorizer.fit(corpus)
    
    # Save the trained vectorizer
    with open("tfidf_vectorizer.pkl", "wb") as f:
        pickle.dump(vectorizer, f)
        
    print("TF-IDF Vectorizer successfully trained and saved as tfidf_vectorizer.pkl")
    print(f"Learned vocabulary size: {len(vectorizer.vocabulary_)} terms.")

if __name__ == "__main__":
    train_and_save_resume_matcher()
