"""
Synthetic data generation for ML model training.

Generates training data by using the rule engine to create base predictions,
then adding Gaussian noise to simulate real-world variability.
"""

import os
import csv
import random
import numpy as np
from typing import Dict, List
from ..features import DisasterType, REQUIRED_FEATURES, FEATURE_BOUNDS
from ..rule_engine import RuleEngine


class SyntheticDataGenerator:
    """
    Generates synthetic training data for ML models.
    
    Uses the rule engine as a baseline and adds realistic noise to simulate
    real-world measurement variability and prediction uncertainty.
    """
    
    def __init__(self, seed: int = 42):
        """
        Initialize the synthetic data generator.
        
        Args:
            seed: Random seed for reproducibility
        """
        self.rule_engine = RuleEngine()
        random.seed(seed)
        np.random.seed(seed)
    
    def generate_random_features(self, disaster_type: DisasterType) -> Dict[str, float]:
        """
        Generate random feature values within valid bounds for a disaster type.
        
        Args:
            disaster_type: Type of disaster
            
        Returns:
            Dictionary of feature names to random values
        """
        features = {}
        required = REQUIRED_FEATURES[disaster_type]
        
        for feature_name in required:
            min_val, max_val = FEATURE_BOUNDS[feature_name]
            # Generate random value within bounds
            features[feature_name] = random.uniform(min_val, max_val)
        
        return features
    
    def generate_samples(
        self, 
        disaster_type: DisasterType, 
        num_samples: int = 1000
    ) -> List[Dict[str, float]]:
        """
        Generate synthetic training samples for a disaster type.
        
        Args:
            disaster_type: Type of disaster
            num_samples: Number of samples to generate
            
        Returns:
            List of samples, each containing features and noisy target radius
        """
        samples = []
        
        for _ in range(num_samples):
            # Generate random features
            features = self.generate_random_features(disaster_type)
            
            # Get rule-based prediction
            rule_prediction = self.rule_engine.predict(disaster_type, features)
            
            # Add Gaussian noise (mean=0, std=0.15 * rule_prediction)
            noise = np.random.normal(0, 0.15 * rule_prediction)
            noisy_radius = max(0.1, rule_prediction + noise)  # Ensure positive
            
            # Create sample with features and target
            sample = features.copy()
            sample['radius_km'] = noisy_radius
            samples.append(sample)
        
        return samples
    
    def save_to_csv(
        self, 
        samples: List[Dict[str, float]], 
        disaster_type: DisasterType,
        output_dir: str = "Backend/impact_radius/training/data"
    ) -> str:
        """
        Save samples to CSV file.
        
        Args:
            samples: List of sample dictionaries
            disaster_type: Type of disaster
            output_dir: Directory to save CSV files
            
        Returns:
            Path to saved CSV file
        """
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Create filename
        filename = f"{disaster_type.value}_training_data.csv"
        filepath = os.path.join(output_dir, filename)
        
        # Write to CSV
        if samples:
            fieldnames = list(samples[0].keys())
            with open(filepath, 'w', newline='') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(samples)
        
        return filepath
    
    def generate_all_datasets(
        self, 
        num_samples_per_type: int = 1000,
        output_dir: str = "Backend/impact_radius/training/data"
    ) -> Dict[DisasterType, str]:
        """
        Generate synthetic datasets for all disaster types.
        
        Args:
            num_samples_per_type: Number of samples per disaster type
            output_dir: Directory to save CSV files
            
        Returns:
            Dictionary mapping disaster types to CSV file paths
        """
        file_paths = {}
        
        for disaster_type in DisasterType:
            print(f"Generating {num_samples_per_type} samples for {disaster_type.value}...")
            samples = self.generate_samples(disaster_type, num_samples_per_type)
            filepath = self.save_to_csv(samples, disaster_type, output_dir)
            file_paths[disaster_type] = filepath
            print(f"  Saved to {filepath}")
        
        return file_paths


def main():
    """Generate synthetic training data for all disaster types."""
    generator = SyntheticDataGenerator(seed=42)
    file_paths = generator.generate_all_datasets(num_samples_per_type=1000)
    
    print("\nSynthetic data generation complete!")
    print(f"Generated {len(file_paths)} datasets:")
    for disaster_type, filepath in file_paths.items():
        print(f"  - {disaster_type.value}: {filepath}")


if __name__ == "__main__":
    main()
