# ML-Enhanced Grading System

This grading system has been enhanced with machine learning models trained on the Rwanda exam dataset (`grading_dataset_enhanced.csv`). The ML models improve answer matching accuracy, especially for non-mathematical questions and explanations.

## Features

- **Semantic Similarity Matching**: Uses sentence transformers to understand meaning, not just exact text matches
- **TF-IDF Vectorization**: Analyzes keyword importance for better matching
- **Context-Aware Matching**: Uses question metadata (difficulty, type, keywords, topics) to improve accuracy
- **Hybrid Approach**: Combines ML matching with traditional symbolic math matching for best results

## Training the Model

To train the ML model on the Rwanda dataset:

```bash
cd backend
python train_grading_model.py
```

This will:
1. Load the dataset from `grading_dataset_enhanced.csv`
2. Train TF-IDF vectorizer on question-answer pairs
3. Extract and store question metadata
4. Save the trained model to `backend/grading/models/grading_model.pkl`

## Usage

The ML-enhanced matching is automatically enabled when:
1. The model has been trained (or will use untrained model as fallback)
2. Required dependencies are installed (`sentence-transformers`, `scikit-learn`, `pandas`)

The `MatchingEngine` will automatically use ML matching when available:

```python
from backend.grading.matching_engine import MatchingEngine

# Initialize with ML matching enabled (default)
matcher = MatchingEngine(use_ml=True)

# Match student answer to gold answer
score, strategy = matcher.match(
    student_text="Mitochondrion is the powerhouse of the cell",
    gold_text="The mitochondrion is known as the powerhouse of the cell"
)
# Returns high score with strategy "ml_embedding" or "ml_tfidf"
```

## Matching Strategies

The enhanced matching engine uses multiple strategies in order:

1. **Exact Match**: Perfect text match
2. **Normalized Match**: Match after normalization
3. **ML Semantic Matching**: High-confidence ML matches (>0.75)
4. **Symbolic Math Matching**: For mathematical expressions
5. **Derivation Matching**: For partial math solutions
6. **ML Matching (fallback)**: Lower threshold ML matches
7. **Text Similarity**: Traditional fuzzy matching

## Question Context

You can provide question context to improve matching:

```python
question_context = {
    'difficulty': 'Medium',
    'question_type': 'explanation',
    'keywords': 'cell, organelle, mitochondria',
    'topic': 'Cell Biology',
    'subject': 'Biology'
}

score, strategy = matcher.match(
    student_text=student_answer,
    gold_text=gold_answer,
    question_context=question_context
)
```

## Dependencies

Required packages (already in `requirements.txt`):
- `sentence-transformers>=2.2.0` - For semantic embeddings
- `scikit-learn>=1.3.0` - For TF-IDF vectorization
- `pandas>=2.0.0` - For dataset processing
- `numpy>=1.24.0` - For numerical operations

## Model Files

- **Training Script**: `backend/train_grading_model.py`
- **ML Matcher**: `backend/grading/ml_matcher.py`
- **Enhanced Matching Engine**: `backend/grading/matching_engine.py`
- **Trained Model**: `backend/grading/models/grading_model.pkl` (created after training)

## Performance

The ML-enhanced matching provides:
- Better accuracy for conceptual/explanation questions
- Improved handling of paraphrased answers
- Context-aware matching using question metadata
- Fallback to traditional methods for math problems

## Notes

- The ML model is optional - if not available, the system falls back to traditional matching
- Training is a one-time process (unless you want to retrain with new data)
- The model file is ~10-50MB depending on dataset size
- First-time training may take a few minutes to download the sentence transformer model

