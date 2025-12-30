"""
ML model training pipeline.

Trains RandomForestRegressor models for each disaster type using synthetic data.
"""

import os
import csv
import joblib
from typing import Dict, List, Tuple
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
from ..features import DisasterType, REQUIRED_FEATURES


class ModelTrainer:
    """
    Trains ML models for disaster impact radius prediction.
    
    Uses RandomForestRegressor with 100 trees and max_depth=10 for each
    disaster type. Evaluates models using train-test split.
    """
    
    def __init__(
        self, 
        n_estimators: int = 100, 
        max_depth: int = 10,
        random_state: int = 42
    ):
        """
        Initialize the model trainer.
        
        Args:
            n_estimators: Number of trees in the forest
            max_depth: Maximum depth of trees
            random_state: Random seed for reproducibility
        """
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.random_state = random_state
    
    def load_training_data(
        self, 
        disaster_type: DisasterType,
        data_dir: str = "Backend/impact_radius/training/data"
    ) -> Tuple[np.ndarray, np.ndarray, List[str]]:
        """
        Load training data from CSV file.
        
        Args:
            disaster_type: Type of disaster
            data_dir: Directory containing CSV files
            
        Returns:
            Tuple of (X features, y targets, feature_names)
        """
        filename = f"{disaster_type.value}_training_data.csv"
        filepath = os.path.join(data_dir, filename)
        
        # Read CSV
        with open(filepath, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            rows = list(reader)
        
        # Extract features and target
        feature_names = REQUIRED_FEATURES[disaster_type]
        X = []
        y = []
        
        for row in rows:
            features = [float(row[fname]) for fname in feature_names]
            target = float(row['radius_km'])
            X.append(features)
            y.append(target)
        
        return np.array(X), np.array(y), feature_names
    
    def train_model(
        self, 
        X: np.ndarray, 
        y: np.ndarray
    ) -> Tuple[RandomForestRegressor, Dict[str, float]]:
        """
        Train a RandomForestRegressor model.
        
        Args:
            X: Feature matrix
            y: Target vector
            
        Returns:
            Tuple of (trained model, evaluation metrics)
        """
        # Split data (80/20)
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=self.random_state
        )
        
        # Train model
        model = RandomForestRegressor(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            random_state=self.random_state,
            n_jobs=-1  # Use all CPU cores
        )
        model.fit(X_train, y_train)
        
        # Evaluate on test set
        y_pred = model.predict(X_test)
        metrics = {
            'rmse': np.sqrt(mean_squared_error(y_test, y_pred)),
            'mae': mean_absolute_error(y_test, y_pred),
            'r2': r2_score(y_test, y_pred),
            'train_samples': len(X_train),
            'test_samples': len(X_test)
        }
        
        return model, metrics
    
    def save_model(
        self, 
        model: RandomForestRegressor,
        disaster_type: DisasterType,
        models_dir: str = "Backend/impact_radius/models"
    ) -> str:
        """
        Save trained model to disk using joblib.
        
        Args:
            model: Trained model
            disaster_type: Type of disaster
            models_dir: Directory to save models
            
        Returns:
            Path to saved model file
        """
        # Create models directory if it doesn't exist
        os.makedirs(models_dir, exist_ok=True)
        
        # Create filename
        filename = f"{disaster_type.value}_model.joblib"
        filepath = os.path.join(models_dir, filename)
        
        # Save model
        joblib.dump(model, filepath)
        
        return filepath
    
    def train_all_models(
        self,
        data_dir: str = "Backend/impact_radius/training/data",
        models_dir: str = "Backend/impact_radius/models"
    ) -> Dict[DisasterType, Dict]:
        """
        Train models for all disaster types.
        
        Args:
            data_dir: Directory containing training data
            models_dir: Directory to save trained models
            
        Returns:
            Dictionary mapping disaster types to training results
        """
        results = {}
        
        for disaster_type in DisasterType:
            print(f"\nTraining model for {disaster_type.value}...")
            
            # Load data
            X, y, feature_names = self.load_training_data(disaster_type, data_dir)
            print(f"  Loaded {len(X)} samples with {len(feature_names)} features")
            
            # Train model
            model, metrics = self.train_model(X, y)
            print(f"  Training complete:")
            print(f"    RMSE: {metrics['rmse']:.3f} km")
            print(f"    MAE: {metrics['mae']:.3f} km")
            print(f"    R²: {metrics['r2']:.3f}")
            
            # Save model
            filepath = self.save_model(model, disaster_type, models_dir)
            print(f"  Model saved to {filepath}")
            
            results[disaster_type] = {
                'model': model,
                'metrics': metrics,
                'filepath': filepath,
                'feature_names': feature_names
            }
        
        return results


def main():
    """Train ML models for all disaster types."""
    trainer = ModelTrainer(n_estimators=100, max_depth=10, random_state=42)
    results = trainer.train_all_models()
    
    print("\n" + "="*60)
    print("Model training complete!")
    print("="*60)
    
    for disaster_type, result in results.items():
        metrics = result['metrics']
        print(f"\n{disaster_type.value.upper()}:")
        print(f"  RMSE: {metrics['rmse']:.3f} km")
        print(f"  MAE: {metrics['mae']:.3f} km")
        print(f"  R²: {metrics['r2']:.3f}")
        print(f"  Model: {result['filepath']}")


if __name__ == "__main__":
    main()
