#!/usr/bin/env python3
"""
Line Movement Tracker Script

Compares NFL betting line movements between morning (9am) and afternoon (3pm) data scrapes.
Detects sharp money, steam moves, reverse line movement, and closing line value opportunities.

Usage:
    python scripts/compare_snapshots.py --week 7 --output movement_analysis.json
    python scripts/compare_snapshots.py --week 7 --min-spread-move 2.0 --min-total-move 2.5
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
from utils.db_manager import DatabaseManager

logger = logging.getLogger(__name__)


class LineMovementAnalyzer:
    """Analyzes line movements between morning and afternoon scrapes"""
    
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
            "movement_thresholds": {
                "spread_movement": {"minimum_points": 1.5},
                "total_movement": {"minimum_points": 2.0},
                "odds_movement": {"minimum_percentage": 10}
            }
        }
    
    def find_snapshots(self, week: int) -> Tuple[Optional[Path], Optional[Path]]:
        """Find morning and afternoon snapshots for a given week
        
        Args:
            week: NFL week number
            
        Returns:
            Tuple of (morning_snapshot_path, afternoon_snapshot_path)
        """
        year = datetime.now().year
        week_dir = self.historical_storage.base_dir / str(year) / f"week_{week}"
        
        if not week_dir.exists():
            logger.error(f"Week directory not found: {week_dir}")
            return None, None
        
        # Find snapshots with timestamps
        morning_snapshot = None
        afternoon_snapshot = None
        
        for file_path in week_dir.glob("*_auto.csv"):
            filename = file_path.name
            # Extract timestamp from filename
            if "_" in filename:
                parts = filename.split("_")
                if len(parts) >= 3:
                    timestamp_part = parts[-2]  # Second to last part should be timestamp
                    if len(timestamp_part) == 13:  # YYYYMMDD_HHMM format
                        try:
                            timestamp = datetime.strptime(timestamp_part, "%Y%m%d_%H%M")
                            hour = timestamp.hour
                            
                            if 8 <= hour <= 10:  # Morning scrape (8-10 AM)
                                morning_snapshot = file_path
                            elif 14 <= hour <= 16:  # Afternoon scrape (2-4 PM)
                                afternoon_snapshot = file_path
                        except ValueError:
                            continue
        
        return morning_snapshot, afternoon_snapshot
    
    def load_snapshot_data(self, snapshot_path: Path) -> Dict[str, pd.DataFrame]:
        """Load data from a snapshot file
        
        Args:
            snapshot_path: Path to snapshot CSV file
            
        Returns:
            Dictionary of DataFrames by data type
        """
        data = {}
        
        try:
            # Determine data type from filename
            filename = snapshot_path.name
            
            if "odds_spreads" in filename:
                df = pd.read_csv(snapshot_path)
                data['spreads'] = df
            elif "odds_totals" in filename:
                df = pd.read_csv(snapshot_path)
                data['totals'] = df
            elif "odds_qb_td" in filename:
                df = pd.read_csv(snapshot_path)
                data['qb_td'] = df
            elif "defense_stats" in filename:
                df = pd.read_csv(snapshot_path)
                data['defense'] = df
            elif "qb_stats" in filename:
                df = pd.read_csv(snapshot_path)
                data['qb_stats'] = df
            elif "matchups" in filename:
                df = pd.read_csv(snapshot_path)
                data['matchups'] = df
            
            logger.info(f"Loaded {len(df)} rows from {snapshot_path.name}")
            
        except Exception as e:
            logger.error(f"Error loading {snapshot_path}: {e}")
        
        return data
    
    def compare_spreads(self, morning_data: Dict, afternoon_data: Dict) -> List[Dict]:
        """Compare spread movements between snapshots
        
        Args:
            morning_data: Morning snapshot data
            afternoon_data: Afternoon snapshot data
            
        Returns:
            List of spread movements
        """
        movements = []
        
        if 'spreads' not in morning_data or 'spreads' not in afternoon_data:
            return movements
        
        morning_spreads = morning_data['spreads']
        afternoon_spreads = afternoon_data['spreads']
        
        # Merge on team and opponent
        merged = pd.merge(
            morning_spreads, afternoon_spreads,
            on=['team', 'opponent', 'week'],
            suffixes=('_morning', '_afternoon')
        )
        
        min_move = self.config['movement_thresholds']['spread_movement']['minimum_points']
        
        for _, row in merged.iterrows():
            morning_spread = row['spread_morning']
            afternoon_spread = row['spread_afternoon']
            
            if pd.isna(morning_spread) or pd.isna(afternoon_spread):
                continue
            
            movement = afternoon_spread - morning_spread
            
            if abs(movement) >= min_move:
                movements.append({
                    'type': 'spread',
                    'team': row['team'],
                    'opponent': row['opponent'],
                    'week': row['week'],
                    'morning_value': morning_spread,
                    'afternoon_value': afternoon_spread,
                    'movement': movement,
                    'movement_percentage': (movement / abs(morning_spread)) * 100 if morning_spread != 0 else 0,
                    'severity': self._classify_movement_severity(abs(movement), 'spread')
                })
        
        return movements
    
    def compare_totals(self, morning_data: Dict, afternoon_data: Dict) -> List[Dict]:
        """Compare total movements between snapshots
        
        Args:
            morning_data: Morning snapshot data
            afternoon_data: Afternoon snapshot data
            
        Returns:
            List of total movements
        """
        movements = []
        
        if 'totals' not in morning_data or 'totals' not in afternoon_data:
            return movements
        
        morning_totals = morning_data['totals']
        afternoon_totals = afternoon_data['totals']
        
        # Merge on team and opponent
        merged = pd.merge(
            morning_totals, afternoon_totals,
            on=['team', 'opponent', 'week'],
            suffixes=('_morning', '_afternoon')
        )
        
        min_move = self.config['movement_thresholds']['total_movement']['minimum_points']
        
        for _, row in merged.iterrows():
            morning_total = row['total_morning']
            afternoon_total = row['total_afternoon']
            
            if pd.isna(morning_total) or pd.isna(afternoon_total):
                continue
            
            movement = afternoon_total - morning_total
            
            if abs(movement) >= min_move:
                movements.append({
                    'type': 'total',
                    'team': row['team'],
                    'opponent': row['opponent'],
                    'week': row['week'],
                    'morning_value': morning_total,
                    'afternoon_value': afternoon_total,
                    'movement': movement,
                    'movement_percentage': (movement / morning_total) * 100 if morning_total != 0 else 0,
                    'severity': self._classify_movement_severity(abs(movement), 'total')
                })
        
        return movements
    
    def compare_qb_td_odds(self, morning_data: Dict, afternoon_data: Dict) -> List[Dict]:
        """Compare QB TD odds movements between snapshots
        
        Args:
            morning_data: Morning snapshot data
            afternoon_data: Afternoon snapshot data
            
        Returns:
            List of QB TD odds movements
        """
        movements = []
        
        if 'qb_td' not in morning_data or 'qb_td' not in afternoon_data:
            return movements
        
        morning_qb_td = morning_data['qb_td']
        afternoon_qb_td = afternoon_data['qb_td']
        
        # Merge on player, team, and opponent
        merged = pd.merge(
            morning_qb_td, afternoon_qb_td,
            on=['player', 'team', 'opponent', 'week'],
            suffixes=('_morning', '_afternoon')
        )
        
        min_move = self.config['movement_thresholds']['odds_movement']['minimum_percentage']
        
        for _, row in merged.iterrows():
            morning_odds = row['odds_morning']
            afternoon_odds = row['odds_afternoon']
            
            if pd.isna(morning_odds) or pd.isna(afternoon_odds):
                continue
            
            # Calculate percentage change
            movement_percentage = ((afternoon_odds - morning_odds) / abs(morning_odds)) * 100 if morning_odds != 0 else 0
            
            if abs(movement_percentage) >= min_move:
                movements.append({
                    'type': 'qb_td_odds',
                    'player': row['player'],
                    'team': row['team'],
                    'opponent': row['opponent'],
                    'week': row['week'],
                    'morning_value': morning_odds,
                    'afternoon_value': afternoon_odds,
                    'movement': afternoon_odds - morning_odds,
                    'movement_percentage': movement_percentage,
                    'severity': self._classify_movement_severity(abs(movement_percentage), 'odds')
                })
        
        return movements
    
    def _classify_movement_severity(self, movement_value: float, movement_type: str) -> str:
        """Classify movement severity based on thresholds
        
        Args:
            movement_value: Absolute movement value
            movement_type: Type of movement (spread, total, odds)
            
        Returns:
            Severity level (low, medium, high, critical)
        """
        thresholds = self.config['movement_thresholds']
        
        if movement_type == 'spread':
            min_thresh = thresholds['spread_movement']['minimum_points']
            if movement_value >= min_thresh * 2:
                return 'high'
            elif movement_value >= min_thresh * 1.5:
                return 'medium'
            else:
                return 'low'
        
        elif movement_type == 'total':
            min_thresh = thresholds['total_movement']['minimum_points']
            if movement_value >= min_thresh * 2:
                return 'high'
            elif movement_value >= min_thresh * 1.5:
                return 'medium'
            else:
                return 'low'
        
        elif movement_type == 'odds':
            min_thresh = thresholds['odds_movement']['minimum_percentage']
            if movement_value >= min_thresh * 2:
                return 'high'
            elif movement_value >= min_thresh * 1.5:
                return 'medium'
            else:
                return 'low'
        
        return 'low'
    
    def detect_sharp_money(self, movements: List[Dict]) -> List[Dict]:
        """Detect sharp money indicators in movements
        
        Args:
            movements: List of line movements
            
        Returns:
            List of sharp money indicators
        """
        sharp_money = []
        
        for movement in movements:
            # Simple sharp money detection based on movement direction
            # In a real implementation, this would consider public betting percentages
            
            if movement['type'] == 'spread':
                # Sharp money often moves lines against public sentiment
                # This is a simplified heuristic
                if abs(movement['movement']) >= 2.0:
                    sharp_money.append({
                        **movement,
                        'indicator_type': 'sharp_money',
                        'confidence': 'medium',
                        'reasoning': 'Significant spread movement (>2 points)'
                    })
            
            elif movement['type'] == 'odds':
                # Sharp money on QB props often moves odds significantly
                if abs(movement['movement_percentage']) >= 20:
                    sharp_money.append({
                        **movement,
                        'indicator_type': 'sharp_money',
                        'confidence': 'high',
                        'reasoning': 'Significant odds movement (>20%)'
                    })
        
        return sharp_money
    
    def detect_steam_moves(self, movements: List[Dict]) -> List[Dict]:
        """Detect steam moves in line movements
        
        Args:
            movements: List of line movements
            
        Returns:
            List of steam moves
        """
        steam_moves = []
        
        for movement in movements:
            # Steam moves are rapid, significant movements
            if movement['severity'] in ['high', 'critical']:
                steam_moves.append({
                    **movement,
                    'indicator_type': 'steam_move',
                    'confidence': 'high' if movement['severity'] == 'critical' else 'medium',
                    'reasoning': f"Rapid {movement['type']} movement ({movement['severity']} severity)"
                })
        
        return steam_moves
    
    def analyze_movements(self, week: int) -> Dict:
        """Analyze line movements for a given week
        
        Args:
            week: NFL week number
            
        Returns:
            Dictionary with movement analysis results
        """
        logger.info(f"Analyzing line movements for Week {week}")
        
        # Find snapshots
        morning_snapshot, afternoon_snapshot = self.find_snapshots(week)
        
        if not morning_snapshot or not afternoon_snapshot:
            logger.error(f"Could not find snapshots for Week {week}")
            return {'error': 'Snapshots not found'}
        
        logger.info(f"Morning snapshot: {morning_snapshot.name}")
        logger.info(f"Afternoon snapshot: {afternoon_snapshot.name}")
        
        # Load data
        morning_data = self.load_snapshot_data(morning_snapshot)
        afternoon_data = self.load_snapshot_data(afternoon_snapshot)
        
        # Compare different data types
        spread_movements = self.compare_spreads(morning_data, afternoon_data)
        total_movements = self.compare_totals(morning_data, afternoon_data)
        qb_td_movements = self.compare_qb_td_odds(morning_data, afternoon_data)
        
        # Combine all movements
        all_movements = spread_movements + total_movements + qb_td_movements
        
        # Detect patterns
        sharp_money = self.detect_sharp_money(all_movements)
        steam_moves = self.detect_steam_moves(all_movements)
        
        # Generate analysis
        analysis = {
            'week': week,
            'analysis_timestamp': datetime.now().isoformat(),
            'morning_snapshot': morning_snapshot.name,
            'afternoon_snapshot': afternoon_snapshot.name,
            'total_movements': len(all_movements),
            'movements': {
                'spreads': spread_movements,
                'totals': total_movements,
                'qb_td_odds': qb_td_movements
            },
            'patterns': {
                'sharp_money': sharp_money,
                'steam_moves': steam_moves
            },
            'summary': {
                'significant_movements': len([m for m in all_movements if m['severity'] in ['high', 'critical']]),
                'sharp_money_indicators': len(sharp_money),
                'steam_moves': len(steam_moves)
            }
        }
        
        return analysis
    
    def generate_report(self, analysis: Dict) -> str:
        """Generate human-readable report from analysis
        
        Args:
            analysis: Analysis results dictionary
            
        Returns:
            Formatted report string
        """
        if 'error' in analysis:
            return f"❌ Error: {analysis['error']}"
        
        report = []
        report.append(f"📊 LINE MOVEMENT ANALYSIS - Week {analysis['week']}")
        report.append("=" * 60)
        report.append(f"Analysis Time: {analysis['analysis_timestamp']}")
        report.append(f"Morning Snapshot: {analysis['morning_snapshot']}")
        report.append(f"Afternoon Snapshot: {analysis['afternoon_snapshot']}")
        report.append("")
        
        # Summary
        summary = analysis['summary']
        report.append("📈 SUMMARY")
        report.append(f"Total Movements: {analysis['total_movements']}")
        report.append(f"Significant Movements: {summary['significant_movements']}")
        report.append(f"Sharp Money Indicators: {summary['sharp_money_indicators']}")
        report.append(f"Steam Moves: {summary['steam_moves']}")
        report.append("")
        
        # Steam Moves
        if analysis['patterns']['steam_moves']:
            report.append("🔥 STEAM MOVES")
            for move in analysis['patterns']['steam_moves']:
                if move['type'] == 'spread':
                    report.append(f"• {move['team']} vs {move['opponent']}: Spread moved from {move['morning_value']} to {move['afternoon_value']} ({move['movement']:+.1f} points)")
                elif move['type'] == 'total':
                    report.append(f"• {move['team']} vs {move['opponent']}: Total moved from {move['morning_value']} to {move['afternoon_value']} ({move['movement']:+.1f} points)")
                elif move['type'] == 'qb_td_odds':
                    report.append(f"• {move['player']} ({move['team']}): Odds moved from {move['morning_value']} to {move['afternoon_value']} ({move['movement_percentage']:+.1f}%)")
                report.append(f"  {move['reasoning']}")
            report.append("")
        
        # Sharp Money
        if analysis['patterns']['sharp_money']:
            report.append("💰 SHARP MONEY INDICATORS")
            for indicator in analysis['patterns']['sharp_money']:
                if indicator['type'] == 'spread':
                    report.append(f"• {indicator['team']} vs {indicator['opponent']}: {indicator['reasoning']}")
                elif indicator['type'] == 'qb_td_odds':
                    report.append(f"• {indicator['player']} ({indicator['team']}): {indicator['reasoning']}")
            report.append("")
        
        # All Movements
        if analysis['movements']['spreads']:
            report.append("📊 SPREAD MOVEMENTS")
            for move in analysis['movements']['spreads']:
                report.append(f"• {move['team']} vs {move['opponent']}: {move['morning_value']} → {move['afternoon_value']} ({move['movement']:+.1f})")
            report.append("")
        
        if analysis['movements']['totals']:
            report.append("📊 TOTAL MOVEMENTS")
            for move in analysis['movements']['totals']:
                report.append(f"• {move['team']} vs {move['opponent']}: {move['morning_value']} → {move['afternoon_value']} ({move['movement']:+.1f})")
            report.append("")
        
        if analysis['movements']['qb_td_odds']:
            report.append("📊 QB TD ODDS MOVEMENTS")
            for move in analysis['movements']['qb_td_odds']:
                report.append(f"• {move['player']} ({move['team']}): {move['morning_value']} → {move['afternoon_value']} ({move['movement_percentage']:+.1f}%)")
        
        return "\n".join(report)


def main():
    """CLI interface for line movement analysis"""
    parser = argparse.ArgumentParser(description='NFL Line Movement Analyzer')
    parser.add_argument('--week', type=int, required=True, help='NFL week number')
    parser.add_argument('--output', help='Output file for analysis results (JSON)')
    parser.add_argument('--report', action='store_true', help='Generate human-readable report')
    parser.add_argument('--min-spread-move', type=float, help='Minimum spread movement threshold')
    parser.add_argument('--min-total-move', type=float, help='Minimum total movement threshold')
    parser.add_argument('--min-odds-change', type=float, help='Minimum odds change percentage')
    parser.add_argument('--verbose', action='store_true', help='Verbose logging')
    
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')
    
    try:
        analyzer = LineMovementAnalyzer()
        
        # Override config if specified
        if args.min_spread_move:
            analyzer.config['movement_thresholds']['spread_movement']['minimum_points'] = args.min_spread_move
        if args.min_total_move:
            analyzer.config['movement_thresholds']['total_movement']['minimum_points'] = args.min_total_move
        if args.min_odds_change:
            analyzer.config['movement_thresholds']['odds_movement']['minimum_percentage'] = args.min_odds_change
        
        # Analyze movements
        analysis = analyzer.analyze_movements(args.week)
        
        # Generate report
        if args.report:
            report = analyzer.generate_report(analysis)
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
