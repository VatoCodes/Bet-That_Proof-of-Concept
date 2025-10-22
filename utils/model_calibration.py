"""Model Calibration Tools for NFL Edge Detection

This module provides tools for tracking model performance, comparing
predictions vs actual outcomes, and suggesting model improvements.

Classes:
    ModelCalibrator: Tracks prediction accuracy and model performance
    OutcomeTracker: Records actual game outcomes for comparison
    PerformanceAnalyzer: Analyzes model performance metrics
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime, timedelta
import logging
import sys
import os
import json

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.query_tools import DatabaseQueryTools
from config import get_database_path, get_historical_dir

logger = logging.getLogger(__name__)


class OutcomeTracker:
    """Tracks actual game outcomes for model calibration"""
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize outcome tracker
        
        Args:
            db_path: Path to database
        """
        self.db_path = db_path or get_database_path()
        self.historical_dir = get_historical_dir()
        self.outcomes_dir = self.historical_dir / "outcomes"
        self.outcomes_dir.mkdir(parents=True, exist_ok=True)
    
    def record_prediction(self, week: int, qb_name: str, team: str, opponent: str,
                        predicted_prob: float, odds: int, model_version: str,
                        confidence: str = "medium") -> str:
        """
        Record a prediction for future outcome tracking
        
        Args:
            week: NFL week number
            qb_name: QB name
            team: QB's team
            opponent: Opposing team
            predicted_prob: Predicted probability (0-1)
            odds: American odds
            model_version: Model version used
            confidence: Confidence level
            
        Returns:
            Prediction ID for tracking
        """
        prediction_id = f"{week}_{qb_name}_{team}_{opponent}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        prediction = {
            'prediction_id': prediction_id,
            'week': week,
            'qb_name': qb_name,
            'team': team,
            'opponent': opponent,
            'predicted_probability': predicted_prob,
            'odds': odds,
            'model_version': model_version,
            'confidence': confidence,
            'predicted_at': datetime.now().isoformat(),
            'outcome_recorded': False,
            'actual_outcome': None,
            'outcome_recorded_at': None
        }
        
        # Save to weekly predictions file
        predictions_file = self.outcomes_dir / f"predictions_week_{week}.json"
        
        # Load existing predictions
        predictions = []
        if predictions_file.exists():
            try:
                with open(predictions_file, 'r') as f:
                    predictions = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                predictions = []
        
        # Add new prediction
        predictions.append(prediction)
        
        # Save updated predictions
        with open(predictions_file, 'w') as f:
            json.dump(predictions, f, indent=2)
        
        logger.info(f"Recorded prediction: {prediction_id}")
        return prediction_id
    
    def record_outcome(self, prediction_id: str, actual_outcome: bool) -> bool:
        """
        Record actual outcome for a prediction
        
        Args:
            prediction_id: Prediction ID to update
            actual_outcome: True if QB threw 0.5+ TDs, False otherwise
            
        Returns:
            True if successfully recorded
        """
        # Find prediction in all weekly files
        for week_file in self.outcomes_dir.glob("predictions_week_*.json"):
            try:
                with open(week_file, 'r') as f:
                    predictions = json.load(f)
                
                # Find and update prediction
                for i, pred in enumerate(predictions):
                    if pred['prediction_id'] == prediction_id:
                        predictions[i]['outcome_recorded'] = True
                        predictions[i]['actual_outcome'] = actual_outcome
                        predictions[i]['outcome_recorded_at'] = datetime.now().isoformat()
                        
                        # Save updated predictions
                        with open(week_file, 'w') as f:
                            json.dump(predictions, f, indent=2)
                        
                        logger.info(f"Recorded outcome for {prediction_id}: {actual_outcome}")
                        return True
                        
            except (json.JSONDecodeError, FileNotFoundError):
                continue
        
        logger.warning(f"Prediction not found: {prediction_id}")
        return False
    
    def get_predictions_for_week(self, week: int) -> List[Dict]:
        """
        Get all predictions for a specific week
        
        Args:
            week: NFL week number
            
        Returns:
            List of predictions
        """
        predictions_file = self.outcomes_dir / f"predictions_week_{week}.json"
        
        if not predictions_file.exists():
            return []
        
        try:
            with open(predictions_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []
    
    def get_completed_predictions(self, weeks_back: int = 4) -> List[Dict]:
        """
        Get all completed predictions (with outcomes) from recent weeks
        
        Args:
            weeks_back: Number of weeks to look back
            
        Returns:
            List of completed predictions
        """
        completed = []
        
        for week_file in self.outcomes_dir.glob("predictions_week_*.json"):
            try:
                with open(week_file, 'r') as f:
                    predictions = json.load(f)
                
                # Filter for completed predictions
                week_completed = [
                    pred for pred in predictions 
                    if pred.get('outcome_recorded', False)
                ]
                completed.extend(week_completed)
                
            except (json.JSONDecodeError, FileNotFoundError):
                continue
        
        # Sort by prediction date and limit to recent weeks
        completed.sort(key=lambda x: x['predicted_at'], reverse=True)
        return completed[:weeks_back * 10]  # Assume max 10 predictions per week


class PerformanceAnalyzer:
    """Analyzes model performance metrics"""
    
    def __init__(self):
        """Initialize performance analyzer"""
        pass
    
    def calculate_brier_score(self, predictions: List[Dict]) -> float:
        """
        Calculate Brier score for prediction accuracy
        
        Args:
            predictions: List of completed predictions
            
        Returns:
            Brier score (lower is better, 0 = perfect, 1 = worst)
        """
        if not predictions:
            return 0.0
        
        total_score = 0.0
        
        for pred in predictions:
            predicted_prob = pred['predicted_probability']
            actual_outcome = pred['actual_outcome']
            
            # Brier score: (predicted_prob - actual_outcome)^2
            actual_value = 1.0 if actual_outcome else 0.0
            score = (predicted_prob - actual_value) ** 2
            total_score += score
        
        return total_score / len(predictions)
    
    def calculate_calibration_error(self, predictions: List[Dict], bins: int = 10) -> Dict:
        """
        Calculate calibration error across probability bins
        
        Args:
            predictions: List of completed predictions
            bins: Number of probability bins
            
        Returns:
            Dictionary with calibration analysis
        """
        if not predictions:
            return {'bins': [], 'calibration_error': 0.0}
        
        # Create probability bins
        bin_edges = np.linspace(0, 1, bins + 1)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
        
        bin_stats = []
        total_error = 0.0
        
        for i in range(bins):
            bin_min, bin_max = bin_edges[i], bin_edges[i + 1]
            
            # Find predictions in this bin
            bin_predictions = [
                pred for pred in predictions
                if bin_min <= pred['predicted_probability'] < bin_max
            ]
            
            if not bin_predictions:
                bin_stats.append({
                    'bin_min': bin_min,
                    'bin_max': bin_max,
                    'bin_center': bin_centers[i],
                    'count': 0,
                    'predicted_prob': bin_centers[i],
                    'actual_rate': 0.0,
                    'error': 0.0
                })
                continue
            
            # Calculate actual success rate
            successes = sum(1 for pred in bin_predictions if pred['actual_outcome'])
            actual_rate = successes / len(bin_predictions)
            
            # Calculate error
            predicted_prob = bin_centers[i]
            error = abs(predicted_prob - actual_rate)
            total_error += error * len(bin_predictions)
            
            bin_stats.append({
                'bin_min': bin_min,
                'bin_max': bin_max,
                'bin_center': bin_centers[i],
                'count': len(bin_predictions),
                'predicted_prob': predicted_prob,
                'actual_rate': actual_rate,
                'error': error
            })
        
        avg_error = total_error / len(predictions) if predictions else 0.0
        
        return {
            'bins': bin_stats,
            'calibration_error': avg_error,
            'total_predictions': len(predictions)
        }
    
    def calculate_roi(self, predictions: List[Dict], bankroll: float = 1000) -> Dict:
        """
        Calculate ROI based on Kelly Criterion recommendations
        
        Args:
            predictions: List of completed predictions
            bankroll: Starting bankroll amount
            
        Returns:
            Dictionary with ROI analysis
        """
        if not predictions:
            return {'total_bets': 0, 'total_winnings': 0, 'roi': 0.0}
        
        total_bet = 0.0
        total_winnings = 0.0
        
        for pred in predictions:
            # Calculate bet amount using Kelly Criterion
            predicted_prob = pred['predicted_probability']
            odds = pred['odds']
            
            # Convert American odds to decimal
            if odds < 0:
                decimal_odds = (100 / abs(odds)) + 1
            else:
                decimal_odds = (odds / 100) + 1
            
            # Kelly fraction calculation
            b = decimal_odds - 1
            p = predicted_prob
            q = 1 - p
            
            kelly = (b * p - q) / b
            kelly_fraction = max(0, kelly * 0.25)  # 25% Kelly
            kelly_fraction = min(kelly_fraction, 0.05)  # Cap at 5%
            
            bet_amount = bankroll * kelly_fraction
            total_bet += bet_amount
            
            # Calculate winnings
            if pred['actual_outcome']:
                winnings = bet_amount * (decimal_odds - 1)
                total_winnings += winnings
        
        roi = (total_winnings / total_bet) * 100 if total_bet > 0 else 0.0
        
        return {
            'total_bets': total_bet,
            'total_winnings': total_winnings,
            'net_profit': total_winnings - total_bet,
            'roi': roi,
            'num_predictions': len(predictions)
        }


class ModelCalibrator:
    """Main model calibration orchestrator"""
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize model calibrator
        
        Args:
            db_path: Path to database
        """
        self.db_path = db_path or get_database_path()
        self.outcome_tracker = OutcomeTracker(db_path)
        self.performance_analyzer = PerformanceAnalyzer()
    
    def analyze_model_performance(self, weeks_back: int = 4) -> Dict:
        """
        Analyze overall model performance
        
        Args:
            weeks_back: Number of weeks to analyze
            
        Returns:
            Dictionary with performance analysis
        """
        # Get completed predictions
        predictions = self.outcome_tracker.get_completed_predictions(weeks_back)
        
        if not predictions:
            return {
                'status': 'no_data',
                'message': 'No completed predictions found for analysis'
            }
        
        # Calculate metrics
        brier_score = self.performance_analyzer.calculate_brier_score(predictions)
        calibration = self.performance_analyzer.calculate_calibration_error(predictions)
        roi_analysis = self.performance_analyzer.calculate_roi(predictions)
        
        # Model version breakdown
        model_versions = {}
        for pred in predictions:
            version = pred.get('model_version', 'unknown')
            if version not in model_versions:
                model_versions[version] = []
            model_versions[version].append(pred)
        
        # Calculate metrics by model version
        version_metrics = {}
        for version, version_predictions in model_versions.items():
            version_metrics[version] = {
                'brier_score': self.performance_analyzer.calculate_brier_score(version_predictions),
                'roi': self.performance_analyzer.calculate_roi(version_predictions)['roi'],
                'count': len(version_predictions)
            }
        
        return {
            'status': 'success',
            'total_predictions': len(predictions),
            'weeks_analyzed': weeks_back,
            'overall_metrics': {
                'brier_score': brier_score,
                'calibration_error': calibration['calibration_error'],
                'roi': roi_analysis['roi'],
                'net_profit': roi_analysis['net_profit']
            },
            'calibration_analysis': calibration,
            'roi_analysis': roi_analysis,
            'model_version_metrics': version_metrics,
            'recommendations': self._generate_recommendations(brier_score, calibration['calibration_error'], roi_analysis['roi'])
        }
    
    def _generate_recommendations(self, brier_score: float, calibration_error: float, roi: float) -> List[str]:
        """Generate model improvement recommendations"""
        recommendations = []
        
        # Brier score recommendations
        if brier_score > 0.25:
            recommendations.append("High Brier score (>0.25) - Consider improving probability calibration")
        elif brier_score > 0.20:
            recommendations.append("Moderate Brier score (>0.20) - Model accuracy could be improved")
        
        # Calibration recommendations
        if calibration_error > 0.15:
            recommendations.append("High calibration error (>0.15) - Probabilities are poorly calibrated")
        elif calibration_error > 0.10:
            recommendations.append("Moderate calibration error (>0.10) - Consider recalibrating probabilities")
        
        # ROI recommendations
        if roi < -10:
            recommendations.append("Negative ROI (<-10%) - Model may be overconfident or missing key factors")
        elif roi < 0:
            recommendations.append("Negative ROI - Consider reducing bet sizes or improving edge detection")
        elif roi > 20:
            recommendations.append("High ROI (>20%) - Model performing well, consider increasing bet sizes")
        
        # General recommendations
        if not recommendations:
            recommendations.append("Model performing well - Continue current approach")
        
        return recommendations
    
    def export_performance_report(self, weeks_back: int = 4, output_file: Optional[Path] = None) -> Path:
        """
        Export detailed performance report
        
        Args:
            weeks_back: Number of weeks to analyze
            output_file: Output file path (optional)
            
        Returns:
            Path to exported report
        """
        analysis = self.analyze_model_performance(weeks_back)
        
        if output_file is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = self.outcome_tracker.outcomes_dir / f"performance_report_{timestamp}.json"
        
        with open(output_file, 'w') as f:
            json.dump(analysis, f, indent=2)
        
        logger.info(f"Performance report exported to: {output_file}")
        return output_file


def main():
    """CLI interface for model calibration"""
    import argparse
    
    parser = argparse.ArgumentParser(description='NFL Model Calibration Tools')
    parser.add_argument('--analyze', action='store_true', help='Analyze model performance')
    parser.add_argument('--weeks-back', type=int, default=4, help='Weeks to analyze (default: 4)')
    parser.add_argument('--export-report', help='Export performance report to file')
    parser.add_argument('--record-outcome', help='Record outcome for prediction ID')
    parser.add_argument('--outcome', choices=['win', 'loss'], help='Outcome (win/loss)')
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    try:
        calibrator = ModelCalibrator()
        
        if args.analyze:
            analysis = calibrator.analyze_model_performance(args.weeks_back)
            
            print(f"\nModel Performance Analysis ({args.weeks_back} weeks)")
            print("=" * 50)
            
            if analysis['status'] == 'no_data':
                print("No completed predictions found for analysis")
                print("\nTo start tracking:")
                print("1. Make predictions using find_edges.py")
                print("2. Record outcomes after games")
                print("3. Run analysis again")
                return 0
            
            metrics = analysis['overall_metrics']
            print(f"Total Predictions: {analysis['total_predictions']}")
            print(f"Brier Score: {metrics['brier_score']:.3f} (lower is better)")
            print(f"Calibration Error: {metrics['calibration_error']:.3f} (lower is better)")
            print(f"ROI: {metrics['roi']:.1f}%")
            print(f"Net Profit: ${metrics['net_profit']:.2f}")
            
            print(f"\nRecommendations:")
            for rec in analysis['recommendations']:
                print(f"  • {rec}")
            
            # Model version breakdown
            if analysis['model_version_metrics']:
                print(f"\nModel Version Breakdown:")
                for version, metrics in analysis['model_version_metrics'].items():
                    print(f"  {version}: {metrics['count']} predictions, "
                          f"Brier: {metrics['brier_score']:.3f}, ROI: {metrics['roi']:.1f}%")
        
        elif args.record_outcome and args.outcome:
            outcome_bool = args.outcome == 'win'
            success = calibrator.outcome_tracker.record_outcome(args.record_outcome, outcome_bool)
            
            if success:
                print(f"✅ Recorded outcome: {args.outcome}")
            else:
                print(f"❌ Failed to record outcome")
                return 1
        
        elif args.export_report:
            output_file = Path(args.export_report)
            report_path = calibrator.export_performance_report(args.weeks_back, output_file)
            print(f"✅ Report exported to: {report_path}")
        
        else:
            parser.print_help()
        
        return 0
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
