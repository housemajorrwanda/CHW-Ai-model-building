import os
import pandas as pd
from deep_translator import GoogleTranslator

# Path to MedQuAD CSV
MEDQUAD_PATH = 'data/medquad.csv'
OUT_PATH = 'data/medquad_grading_data.csv'

# Load MedQuAD CSV
df_medquad = pd.read_csv(MEDQUAD_PATH)
print(f"Loaded {len(df_medquad)} MedQuAD entries")

# Limit to first 50 entries for translation to avoid API rate limits
MAX_TRANSLATE = 50
examples = []

for i, row in df_medquad.iterrows():
    # Use correct column names from CSV
    q = row['question']
    ref = row['answer']
    
    if not q or not ref or pd.isna(q) or pd.isna(ref):
        continue
    
    # Convert to string if needed
    q = str(q)
    ref = str(ref)
    
    # Simulate user answers
    user_full = ref
    user_partial = ref[:len(ref)//2] if len(ref) > 10 else ref
    user_poor = ref.split('.')[0] if '.' in ref else ref[:10]
    
    # English examples
    examples.append({'question': q, 'reference_answer': ref, 'user_answer': user_full, 'lang': 'en', 'score': 5})
    examples.append({'question': q, 'reference_answer': ref, 'user_answer': user_partial, 'lang': 'en', 'score': 3})
    examples.append({'question': q, 'reference_answer': ref, 'user_answer': user_poor, 'lang': 'en', 'score': 1})
    
    # Limit translation to first MAX_TRANSLATE Q&A for demo
    if i < MAX_TRANSLATE:
        try:
            print(f"Translating entry {i+1}/{MAX_TRANSLATE}...")
            q_ki = GoogleTranslator(source='en', target='rw').translate(q)
            ref_ki = GoogleTranslator(source='en', target='rw').translate(ref)
            user_full_ki = GoogleTranslator(source='en', target='rw').translate(user_full)
            user_partial_ki = GoogleTranslator(source='en', target='rw').translate(user_partial)
            user_poor_ki = GoogleTranslator(source='en', target='rw').translate(user_poor)
            
            examples.append({'question': q_ki, 'reference_answer': ref_ki, 'user_answer': user_full_ki, 'lang': 'ki', 'score': 5})
            examples.append({'question': q_ki, 'reference_answer': ref_ki, 'user_answer': user_partial_ki, 'lang': 'ki', 'score': 3})
            examples.append({'question': q_ki, 'reference_answer': ref_ki, 'user_answer': user_poor_ki, 'lang': 'ki', 'score': 1})
        except Exception as e:
            print(f"Translation failed for entry {i}: {e}")

# Save to CSV
os.makedirs('data', exist_ok=True)
df = pd.DataFrame(examples)
df.to_csv(OUT_PATH, index=False)
print(f"Saved {len(df)} grading examples to {OUT_PATH}")

# Note: Requires 'deep-translator' package. Install with: pip install deep-translator
