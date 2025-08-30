import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

os.makedirs('data', exist_ok=True)

# Simulate regions.csv
df_regions = pd.DataFrame([
    {'region': 'North', 'disease_prevalence': 'malaria:0.3,diarrhea:0.2,ARI:0.1'},
    {'region': 'South', 'disease_prevalence': 'malaria:0.1,diarrhea:0.3,ARI:0.2'},
    {'region': 'East',  'disease_prevalence': 'malaria:0.2,diarrhea:0.1,ARI:0.3'},
    {'region': 'West',  'disease_prevalence': 'malaria:0.25,diarrhea:0.15,ARI:0.25'},
    {'region': 'Kigali','disease_prevalence': 'malaria:0.05,diarrhea:0.1,ARI:0.05'},
])
df_regions.to_csv('data/regions.csv', index=False)

# Simulate CHW events
dates = [datetime.now() - timedelta(days=i) for i in range(30)]
chws = [f'CHW_{i:03d}' for i in range(1, 21)]
regions = df_regions['region'].tolist()
events = []
for chw in chws:
    region = np.random.choice(regions)
    for d in dates:
        if np.random.rand() < 0.5:
            session_len = np.random.randint(5, 60)
            quiz_attempts = np.random.randint(0, 3)
            avg_score = np.random.uniform(2, 5) if quiz_attempts else None
            events.append({
                'chw_id': chw,
                'region': region,
                'date': d.strftime('%Y-%m-%d'),
                'session_length_min': session_len,
                'quiz_attempts': quiz_attempts,
                'avg_score': avg_score,
            })
pd.DataFrame(events).to_csv('data/simulated_chw_events.csv', index=False)
print('Synthetic data generated in data/ directory.')

# Generate synthetic grading data
def make_grading_examples():
    grading_examples = []
    # English examples
    for i in range(50):
        q = "What are the main ways to prevent malaria?"
        ref = "Malaria is prevented by sleeping under a mosquito bed net and removing standing water."
        if i < 10:
            user = "I don't know."
            score = 1
        elif i < 20:
            user = "You can use a net."
            score = 2
        elif i < 30:
            user = "Malaria is prevented by using a bed net."
            score = 3
        elif i < 40:
            user = "Malaria is prevented by using a bed net and removing water."
            score = 4
        else:
            user = "Malaria is prevented by sleeping under a mosquito bed net and removing standing water."
            score = 5
        grading_examples.append({
            'question': q,
            'reference_answer': ref,
            'user_answer': user,
            'lang': 'en',
            'score': score
        })
    # Kinyarwanda examples
    for i in range(50):
        q = "Ni izihe nzira nyamukuru zo kwirinda malariya?"
        ref = "Malariya irindwa uryamye mu buriri burimo umusego wica imibu no gukuraho amazi ahagaze."
        if i < 10:
            user = "Simbyumva."
            score = 1
        elif i < 20:
            user = "Ukoresha umusego."
            score = 2
        elif i < 30:
            user = "Malariya irindwa ukoresheje umusego."
            score = 3
        elif i < 40:
            user = "Malariya irindwa ukoresheje umusego no gukuraho amazi."
            score = 4
        else:
            user = "Malariya irindwa uryamye mu buriri burimo umusego wica imibu no gukuraho amazi ahagaze."
            score = 5
        grading_examples.append({
            'question': q,
            'reference_answer': ref,
            'user_answer': user,
            'lang': 'ki',
            'score': score
        })
    df = pd.DataFrame(grading_examples)
    df.to_csv('data/synthetic_grading_data.csv', index=False)
    print('Synthetic grading data generated in data/synthetic_grading_data.csv')

if __name__ == "__main__":
    make_grading_examples()
