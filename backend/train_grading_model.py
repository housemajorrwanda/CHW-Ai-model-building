"""
Training script for ML-enhanced grading model using Rwanda exam dataset
"""
import os
import sys
import logging
from pathlib import Path

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from grading.ml_matcher import MLMatcher

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Train the ML grading model on the Rwanda dataset"""
    
    # Paths
    script_dir = Path(__file__).parent
    dataset_path = script_dir.parent / "grading_dataset_enhanced.csv"
    model_path = script_dir / "grading" / "models" / "grading_model.pkl"
    
    # Create models directory if it doesn't exist
    model_path.parent.mkdir(parents=True, exist_ok=True)
    
    if not dataset_path.exists():
        logger.error(f"Dataset not found at {dataset_path}")
        logger.info("Please ensure grading_dataset_enhanced.csv is in the project root")
        return
    
    logger.info("=" * 70)
    logger.info("Training ML-Enhanced Grading Model")
    logger.info("=" * 70)
    logger.info(f"Dataset: {dataset_path}")
    logger.info(f"Model output: {model_path}")
    logger.info("")
    
    try:
        # Initialize matcher
        logger.info("Initializing ML matcher...")
        matcher = MLMatcher(
            use_embeddings=True,
            similarity_threshold=0.6
        )
        
        # Train on dataset
        logger.info("Training on dataset...")
        matcher.train_on_dataset(str(dataset_path))
        
        # Save model
        logger.info("Saving trained model...")
        matcher.save_model(str(model_path))
        
        logger.info("")
        logger.info("=" * 70)
        logger.info("Training completed successfully!")
        logger.info("=" * 70)
        logger.info(f"Model saved to: {model_path}")
        logger.info("")
        logger.info("The enhanced matching engine is now ready to use.")
        logger.info("It will automatically load this model when initialized.")
        
    except Exception as e:
        logger.error(f"Training failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

