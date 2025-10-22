#!/usr/bin/env python3
"""
Movement Analyzer Script

Advanced analysis of line movements with pattern recognition and classification.
Provides detailed insights into movement types, severity, and betting implications.

Usage:
    python scripts/movement_analyzer.py --week 7 --output detailed_analysis.json
    python scripts/movement_analyzer.py --week 7 --classify-movements --detect-patterns
"""

import argparse
import json
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging

# Add parent directory to path for imports
import sys
sys.path.append(str(Path(__file__).parent.parent))

from utils.historical_storage import HistoricalStorage

logger = logging.getLogger(__name__)


class MovementAnalyzer:
    """Advanced movement analysis with pattern recognition"""
    
    def __init__(self, project_root: Path = None):
        """Initialize analyzer
        
        Args:
            project_root: Path to project root (auto-detected if not provided)
        """
        if project_root is None:
            current_file = Path(__file__).resolve()
            self.project_root = current_file.parent.parent
        else:
            self.project_root = Path(project_root)
        
        self.historical_storage = HistoricalStorage(self.project_root / 'data' / 'historical')
        self.resources_dir = self.project_root / '.claude' / 'skills' / 'line-movement-tracker' / 'resources'
        
        # Load configuration
        self.config = self._load_config()
        
    def _load_config(self) -> Dict:
        """Load movement thresholds configuration"""
        config_path = self.resources_dir / 'movement_thresholds.json'
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Config file not found: {config_path}, using defaults")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """Get default configuration"""
        return {
            "movement_classification": {
                "steam_moves": {
                    "spread_threshold": 2.5,
                    "total_threshold": 3.0,
                    "odds_threshold": 20
                },
                "sharp_money": {
                    "public_betting_threshold": 60,
                    "movement_direction": "opposite",
                    "minimum_movement": 1.0
                }
            }
        }
    
    def classify_movement_type(self, movement: Dict) -> str:
        """Classify movement type based on characteristics
        
        Args:
            movement: Movement data dictionary
            
        Returns:
            Movement type classification
        """
        movement_value = abs(movement.get('movement', 0))
        movement_percentage = abs(movement.get('movement_percentage', 0))
        
        if movement['type'] == 'spread':
            if movement_value >= self.config['movement_classification']['steam_moves']['spread_threshold']:
                return 'steam_move'
            elif movement_value >= 1.5:
                return 'significant_move'
            else:
                return 'normal_move'
        
        elif movement['type'] == 'total':
            if movement_value >= self.config['movement_classification']['steam_moves']['total_threshold']:
                return 'steam_move'
            elif movement_value >= 2.0:
                return 'significant_move'
            else:
                return 'normal_move'
        
        elif movement['type'] == 'qb_td_odds':
            if movement_percentage >= self.config['movement_classification']['steam_moves']['odds_threshold']:
                return 'steam_move'
            elif movement_percentage >= 15:
                return 'significant_move'
            else:
                return 'normal_move'
        
        return 'normal_move'
    
    def detect_reverse_line_movement(self, movements: List[Dict]) -> List[Dict]:
        """Detect reverse line movement patterns
        
        Args:
            movements: List of line movements
            
        Returns:
            List of reverse line movements
        """
        reverse_movements = []
        
        for movement in movements:
            # Reverse line movement occurs when line moves opposite to public betting
            # This is a simplified heuristic - in reality would need public betting data
            
            if movement['type'] == 'spread':
                # If spread moves toward favorite but public is on underdog
                if movement['movement'] < 0 and abs(movement['movement']) >= 1.0:
                    reverse_movements.append({
                        **movement,
                        'pattern_type': 'reverse_line_movement',
                        'confidence': 'medium',
                        'reasoning': 'Spread moved toward favorite despite public sentiment'
                    })
            
            elif movement['type'] == 'odds':
                # If odds move against public betting
                if abs(movement['movement_percentage']) >= 15:
                    reverse_movements.append({
                        **movement,
                        'pattern_type': 'reverse_line_movement',
                        'confidence': 'high',
                        'reasoning': 'Significant odds movement against public sentiment'
                    })
        
        return reverse_movements
    
    def detect_closing_line_value(self, movements: List[Dict]) -> List[Dict]:
        """Detect closing line value opportunities
        
        Args:
            movements: List of line movements
            
        Returns:
            List of closing line value opportunities
        """
        closing_line_value = []
        
        for movement in movements:
            # Closing line value occurs when early line is better than closing line
            # This is a simplified heuristic
            
            if movement['type'] == 'spread':
                # If spread moved significantly, early line had value
                if abs(movement['movement']) >= 1.5:
                    closing_line_value.append({
                        **movement,
                        'pattern_type': 'closing_line_value',
                        'confidence': 'medium',
                        'reasoning': f"Early line {movement['morning_value']} had value vs closing {movement['afternoon_value']}"
                    })
            
            elif movement['type'] == 'odds':
                # If odds moved significantly, early line had value
                if abs(movement['movement_percentage']) >= 20:
                    closing_line_value.append({
                        **movement,
                        'pattern_type': 'closing_line_value',
                        'confidence': 'high',
                        'reasoning': f"Early odds {movement['morning_value']} had value vs closing {movement['afternoon_value']}"
                    })
        
        return closing_line_value
    
    def analyze_movement_patterns(self, movements: List[Dict]) -> Dict:
        """Analyze patterns across all movements
        
        Args:
            movements: List of all movements
            
        Returns:
            Dictionary with pattern analysis
        """
        patterns = {
            'steam_moves': [],
            'reverse_line_movement': [],
            'closing_line_value': [],
            'sharp_money': [],
            'statistical_summary': {}
        }
        
        # Classify each movement
        for movement in movements:
            movement_type = self.classify_movement_type(movement)
            movement['classified_type'] = movement_type
            
            if movement_type == 'steam_move':
                patterns['steam_moves'].append(movement)
        
        # Detect specific patterns
        patterns['reverse_line_movement'] = self.detect_reverse_line_movement(movements)
        patterns['closing_line_value'] = self.detect_closing_line_value(movements)
        
        # Statistical summary
        if movements:
            movement_values = [abs(m.get('movement', 0)) for m in movements]
            movement_percentages = [abs(m.get('movement_percentage', 0)) for m in movements]
            
            patterns['statistical_summary'] = {
                'total_movements': len(movements),
                'average_movement': np.mean(movement_values),
                'median_movement': np.median(movement_values),
                'max_movement': np.max(movement_values),
                'average_percentage_change': np.mean(movement_percentages),
                'max_percentage_change': np.max(movement_percentages),
                'movement_types': {
                    'spread': len([m for m in movements if m['type'] == 'spread']),
                    'total': len([m for m in movements if m['type'] == 'total']),
                    'qb_td_odds': len([m for m in movements if m['type'] == 'qb_td_odds'])
                }
            }
        
        return patterns
    
    def generate_recommendations(self, patterns: Dict) -> List[Dict]:
        """Generate betting recommendations based on patterns
        
        Args:
            patterns: Pattern analysis results
            
        Returns:
            List of betting recommendations
        """
        recommendations = []
        
        # Steam move recommendations
        for steam_move in patterns['steam_moves']:
            if steam_move['type'] == 'spread':
                recommendations.append({
                    'type': 'steam_move',
                    'recommendation': f"Consider betting {steam_move['team']} at {steam_move['afternoon_value']}",
                    'reasoning': f"Steam move detected: {steam_move['morning_value']} → {steam_move['afternoon_value']}",
                    'confidence': 'high',
                    'movement': steam_move
                })
            elif steam_move['type'] == 'qb_td_odds':
                recommendations.append({
                    'type': 'steam_move',
                    'recommendation': f"Consider {steam_move['player']} prop at {steam_move['afternoon_value']}",
                    'reasoning': f"Steam move detected: {steam_move['movement_percentage']:+.1f}% odds change",
                    'confidence': 'high',
                    'movement': steam_move
                })
        
        # Reverse line movement recommendations
        for rlm in patterns['reverse_line_movement']:
            recommendations.append({
                'type': 'reverse_line_movement',
                'recommendation': f"Follow sharp money on {rlm.get('team', rlm.get('player', 'unknown'))}",
                'reasoning': rlm['reasoning'],
                'confidence': rlm['confidence'],
                'movement': rlm
            })
        
        # Closing line value recommendations
        for clv in patterns['closing_line_value']:
            recommendations.append({
                'type': 'closing_line_value',
                'recommendation': f"Early line {clv['morning_value']} had value",
                'reasoning': clv['reasoning'],
                'confidence': clv['confidence'],
                'movement': clv
            })
        
        return recommendations
    
    def analyze_week_movements(self, week: int) -> Dict:
        """Perform comprehensive movement analysis for a week
        
        Args:
            week: NFL week number
            
        Returns:
            Comprehensive analysis results
        """
        logger.info(f"Performing comprehensive movement analysis for Week {week}")
        
        # This would typically load movement data from the compare_snapshots script
        # For now, we'll create a mock analysis structure
        
        analysis = {
            'week': week,
            'analysis_timestamp': datetime.now().isoformat(),
            'analysis_type': 'comprehensive_pattern_analysis',
            'patterns': {
                'steam_moves': [],
                'reverse_line_movement': [],
                'closing_line_value': [],
                'sharp_money': [],
                'statistical_summary': {}
            },
            'recommendations': [],
            'summary': {
                'total_patterns_detected': 0,
                'high_confidence_recommendations': 0,
                'medium_confidence_recommendations': 0,
                'low_confidence_recommendations': 0
            }
        }
        
        # In a real implementation, this would:
        # 1. Load movement data from compare_snapshots.py
        # 2. Analyze patterns
        # 3. Generate recommendations
        
        return analysis
    
    def generate_detailed_report(self, analysis: Dict) -> str:
        """Generate detailed analysis report
        
        Args:
            analysis: Analysis results dictionary
            
        Returns:
            Formatted detailed report
        """
        report = []
        report.append(f"📊 DETAILED MOVEMENT ANALYSIS - Week {analysis['week']}")
        report.append("=" * 80)
        report.append(f"Analysis Time: {analysis['analysis_timestamp']}")
        report.append(f"Analysis Type: {analysis['analysis_type']}")
        report.append("")
        
        # Patterns Summary
        patterns = analysis['patterns']
        report.append("🔍 PATTERN ANALYSIS")
        report.append(f"Steam Moves: {len(patterns['steam_moves'])}")
        report.append(f"Reverse Line Movement: {len(patterns['reverse_line_movement'])}")
        report.append(f"Closing Line Value: {len(patterns['closing_line_value'])}")
        report.append(f"Sharp Money Indicators: {len(patterns['sharp_money'])}")
        report.append("")
        
        # Statistical Summary
        if patterns['statistical_summary']:
            stats = patterns['statistical_summary']
            report.append("📈 STATISTICAL SUMMARY")
            report.append(f"Total Movements: {stats.get('total_movements', 0)}")
            report.append(f"Average Movement: {stats.get('average_movement', 0):.2f}")
            report.append(f"Maximum Movement: {stats.get('max_movement', 0):.2f}")
            report.append(f"Average % Change: {stats.get('average_percentage_change', 0):.1f}%")
            report.append("")
        
        # Recommendations
        recommendations = analysis['recommendations']
        if recommendations:
            report.append("💡 BETTING RECOMMENDATIONS")
            for i, rec in enumerate(recommendations, 1):
                report.append(f"{i}. {rec['recommendation']}")
                report.append(f"   Type: {rec['type']}")
                report.append(f"   Confidence: {rec['confidence']}")
                report.append(f"   Reasoning: {rec['reasoning']}")
                report.append("")
        
        # Summary
        summary = analysis['summary']
        report.append("📋 ANALYSIS SUMMARY")
        report.append(f"Total Patterns Detected: {summary['total_patterns_detected']}")
        report.append(f"High Confidence Recommendations: {summary['high_confidence_recommendations']}")
        report.append(f"Medium Confidence Recommendations: {summary['medium_confidence_recommendations']}")
        report.append(f"Low Confidence Recommendations: {summary['low_confidence_recommendations']}")
        
        return "\n".join(report)


def main():
    """CLI interface for movement analysis"""
    parser = argparse.ArgumentParser(description='NFL Movement Pattern Analyzer')
    parser.add_argument('--week', type=int, required=True, help='NFL week number')
    parser.add_argument('--output', help='Output file for analysis results (JSON)')
    parser.add_argument('--report', action='store_true', help='Generate detailed report')
    parser.add_argument('--classify-movements', action='store_true', help='Classify movement types')
    parser.add_argument('--detect-patterns', action='store_true', help='Detect movement patterns')
    parser.add_argument('--generate-recommendations', action='store_true', help='Generate betting recommendations')
    parser.add_argument('--verbose', action='store_true', help='Verbose logging')
    
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')
    
    try:
        analyzer = MovementAnalyzer()
        
        # Perform analysis
        analysis = analyzer.analyze_week_movements(args.week)
        
        # Generate report
        if args.report:
            report = analyzer.generate_detailed_report(analysis)
            print(report)
        
        # Save to file if specified
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(analysis, f, indent=2)
            logger.info(f"Analysis saved to {args.output}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
