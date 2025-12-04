# Description Analysis Script for CleanData.csv

import pandas as pd
import string
from collections import Counter
from nltk.corpus import stopwords
from nltk.util import ngrams
import nltk

# Download stopwords if not already
nltk.download('stopwords')

print("=== Starting Job Description Analysis ===")

# === 1. Load data ===
input_file = 'CleanData.csv'
output_file = 'DescriptionsAnalysed.csv'

print(f"Loading data from '{input_file}'...")
# Keep Job ID as string to avoid scientific notation
df = pd.read_csv(input_file, dtype={'Job ID': str})
print(f"Data loaded: {len(df)} rows.")

# Fill missing descriptions
df['Description'] = df['Description'].fillna('').astype(str)

# === 2. Clean and tokenize ===
stop_words = set(stopwords.words('english'))
translator = str.maketrans('', '', string.punctuation)

def clean_text(text):
    text = text.lower().translate(translator)
    tokens = [word for word in text.split() if word not in stop_words]
    return tokens

print("Cleaning and tokenizing descriptions...")
df['Tokens'] = df['Description'].apply(clean_text)

# === 3. Compute per-job top keywords ===
def top_keywords(tokens, n=5):
    counts = Counter(tokens)
    return [word for word, _ in counts.most_common(n)]

df['TopKeywords'] = df['Tokens'].apply(lambda t: top_keywords(t, 5))

# === 4. Compute per-job top bigrams ===
def top_bigrams(tokens, n=5):
    bigram_list = list(ngrams(tokens, 2))
    counts = Counter(bigram_list)
    return [' '.join(b) for b, _ in counts.most_common(n)]

df['TopBigrams'] = df['Tokens'].apply(lambda t: top_bigrams(t, 5))

# === 5. Optional technical score ===
tech_keywords = ['python','java','c#','sql','javascript','react','node','azure','aws','docker','ml','ai','tensorflow','pytorch']

def technical_score(tokens):
    return sum(1 for token in tokens if token.lower() in tech_keywords)

df['TechnicalScore'] = df['Tokens'].apply(technical_score)

# === 6. Save processed CSV ===
df.to_csv(output_file, index=False)
print(f"Processed data saved to '{output_file}'.")
print("=== Analysis Completed ===")


