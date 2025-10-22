#!/usr/bin/env python3
"""
NFL Edge Finder - Command Line Interface

This tool finds betting edges in NFL QB TD props by comparing our calculated
probabilities to implied odds from sportsbooks.

Usage:
    python find_edges.py --week 8
    python find_edges.py --week 8 --threshold 10 --bankroll 1000
    python find_edges.py --week 8 --advanced --export edges_week8.csv
    python find_edges.py --week 8 --model v2 --min-confidence high
"""

import argparse
import pandas as pd
import sys
import os
from pathlib import Path
from datetime import datetime
import logging

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.edge_calculator import EdgeCalculator
from utils.query_tools import DatabaseQueryTools
from config import get_database_path

logger = logging.getLogger(__name__)


def format_currency(amount: float) -> str:
    """Format currency amount"""
    return f"${amount:,.2f}"


def format_percentage(value: float) -> str:
    """Format percentage value"""
    return f"{value:.1f}%"


def get_edge_emoji(edge_pct: float) -> str:
    """Get emoji based on edge percentage"""
    if edge_pct >= 20:
        return "🔥"  # Fire for exceptional edges
    elif edge_pct >= 15:
        return "⭐"  # Star for strong edges
    elif edge_pct >= 10:
        return "💎"  # Diamond for good edges
    elif edge_pct >= 5:
        return "📈"  # Chart for small edges
    else:
        return "❌"  # X for no edge


def get_tier_color(tier: str) -> str:
    """Get color code for tier (for terminal output)"""
    colors = {
        "STRONG EDGE": "\033[92m",  # Green
        "GOOD EDGE": "\033[94m",    # Blue
        "SMALL EDGE": "\033[93m",   # Yellow
        "PASS": "\033[91m"          # Red
    }
    return colors.get(tier, "")


def print_edge_opportunity(edge: dict, index: int, bankroll: float):
    """Print formatted edge opportunity"""
    tier = edge['bet_recommendation']['tier']
    color = get_tier_color(tier)
    reset_color = "\033[0m"
    
    print(f"{index}. {edge['qb_name']} ({edge['qb_team']}) vs {edge['opponent']}")
    print(f"   Prop: Over 0.5 TD @ {edge['odds']} ({edge['sportsbook']})")
    print(f"   Implied: {format_percentage(edge['implied_probability'] * 100)}")
    print(f"   True Prob: {format_percentage(edge['true_probability'] * 100)} (confidence: {edge['confidence']})")
    
    edge_emoji = get_edge_emoji(edge['edge_percentage'])
    print(f"   Edge: {edge['edge_percentage']:+.1f}% {edge_emoji} {color}{tier}{reset_color}")
    
    bet_rec = edge['bet_recommendation']
    if bet_rec['recommended_bet'] > 0:
        print(f"   Recommendation: {format_currency(bet_rec['recommended_bet'])} ({bet_rec['bankroll_percentage']:.1f}% of bankroll)")
        print(f"   Kelly Fraction: {bet_rec['kelly_fraction']:.1%} Kelly (conservative)")
    else:
        print(f"   Recommendation: PASS (insufficient edge)")
    
    # Show key stats
    print(f"   Stats:")
    print(f"   - {edge['qb_name']}: {edge['qb_td_per_game']:.1f} TD/game ({edge.get('games_played', 'N/A')} games)")
    print(f"   - {edge['opponent']} Defense: {edge['defense_tds_per_game']:.1f} TD/game allowed")
    
    if edge.get('home_field_advantage', 0) > 0:
        print(f"   - Home field advantage: +{format_percentage(edge['home_field_advantage'] * 100)}")
    
    print()


def export_edges_to_csv(edges: list, filename: str):
    """Export edges to CSV file"""
    if not edges:
        print("No edges to export")
        return
    
    # Flatten edge data for CSV
    flattened_edges = []
    for edge in edges:
        flat_edge = {
            'qb_name': edge['qb_name'],
            'qb_team': edge['qb_team'],
            'opponent': edge['opponent'],
            'sportsbook': edge['sportsbook'],
            'odds': edge['odds'],
            'implied_probability': edge['implied_probability'],
            'true_probability': edge['true_probability'],
            'edge_percentage': edge['edge_percentage'],
            'confidence': edge['confidence'],
            'model_version': edge['model_version'],
            'tier': edge['bet_recommendation']['tier'],
            'recommended_bet': edge['bet_recommendation']['recommended_bet'],
            'kelly_fraction': edge['bet_recommendation']['kelly_fraction'],
            'bankroll_percentage': edge['bet_recommendation']['bankroll_percentage'],
            'qb_td_per_game': edge['qb_td_per_game'],
            'defense_tds_per_game': edge['defense_tds_per_game'],
            'game_date': edge.get('game_date', ''),
            'scraped_at': datetime.now().isoformat()
        }
        flattened_edges.append(flat_edge)
    
    df = pd.DataFrame(flattened_edges)
    df.to_csv(filename, index=False)
    print(f"✅ Exported {len(edges)} edges to {filename}")


def filter_by_confidence(edges: list, min_confidence: str) -> list:
    """Filter edges by minimum confidence level"""
    confidence_levels = {'low': 1, 'medium': 2, 'high': 3}
    min_level = confidence_levels.get(min_confidence.lower(), 2)
    
    filtered_edges = []
    for edge in edges:
        edge_level = confidence_levels.get(edge['confidence'].lower(), 2)
        if edge_level >= min_level:
            filtered_edges.append(edge)
    
    return filtered_edges


def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(
        description='NFL Edge Finder - Find betting edges in QB TD props',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python find_edges.py --week 8
  python find_edges.py --week 8 --threshold 10 --bankroll 1000
  python find_edges.py --week 8 --advanced --export edges_week8.csv
  python find_edges.py --week 8 --model v2 --min-confidence high
        """
    )
    
    parser.add_argument('--week', type=int, required=True, help='NFL week number')
    parser.add_argument('--threshold', type=float, default=5.0, 
                       help='Minimum edge percentage (default: 5.0)')
    parser.add_argument('--bankroll', type=float, default=1000,
                       help='Bankroll amount for bet sizing (default: 1000)')
    parser.add_argument('--model', choices=['v1', 'v2'], default='v1',
                       help='Probability model version (default: v1)')
    parser.add_argument('--advanced', action='store_true',
                       help='Use advanced model (same as --model v2)')
    parser.add_argument('--min-confidence', choices=['low', 'medium', 'high'], 
                       default='medium', help='Minimum confidence level (default: medium)')
    parser.add_argument('--export', help='Export results to CSV file')
    parser.add_argument('--quiet', action='store_true', help='Suppress detailed output')
    parser.add_argument('--db-path', help='Path to database file')
    
    args = parser.parse_args()
    
    # Use advanced model if requested
    if args.advanced:
        args.model = 'v2'
    
    # Configure logging
    log_level = logging.WARNING if args.quiet else logging.INFO
    logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')
    
    try:
        # Initialize edge calculator
        db_path = Path(args.db_path) if args.db_path else None
        calculator = EdgeCalculator(model_version=args.model, db_path=db_path)
        
        # Find edges
        edges = calculator.find_edges_for_week(args.week, args.threshold)
        
        # Filter by confidence if specified
        if args.min_confidence != 'medium':
            edges = filter_by_confidence(edges, args.min_confidence)
        
        # Print header
        if not args.quiet:
            print("=" * 60)
            print(f"NFL EDGE FINDER - Week {args.week}")
            print("=" * 60)
            print(f"Bankroll: {format_currency(args.bankroll)}")
            print(f"Model: {args.model.upper()}")
            print(f"Threshold: {format_percentage(args.threshold)} edge minimum")
            print(f"Min Confidence: {args.min_confidence.upper()}")
            print()
        
        # Print results
        if not edges:
            print("No edge opportunities found")
            print("\nTry:")
            print("- Lowering the threshold (--threshold 3)")
            print("- Using advanced model (--model v2)")
            print("- Lowering confidence requirement (--min-confidence low)")
            return 0
        
        if not args.quiet:
            print(f"EDGE OPPORTUNITIES FOUND: {len(edges)}\n")
            
            for i, edge in enumerate(edges, 1):
                print_edge_opportunity(edge, i, args.bankroll)
        
        # Export to CSV if requested
        if args.export:
            export_edges_to_csv(edges, args.export)
        
        # Summary statistics
        if not args.quiet and len(edges) > 0:
            total_recommended = sum(edge['bet_recommendation']['recommended_bet'] for edge in edges)
            avg_edge = sum(edge['edge_percentage'] for edge in edges) / len(edges)
            
            print("=" * 60)
            print("SUMMARY")
            print("=" * 60)
            print(f"Total recommended bets: {format_currency(total_recommended)}")
            print(f"Percentage of bankroll: {format_percentage((total_recommended / args.bankroll) * 100)}")
            print(f"Average edge: {format_percentage(avg_edge)}")
            
            # Tier breakdown
            tiers = {}
            for edge in edges:
                tier = edge['bet_recommendation']['tier']
                tiers[tier] = tiers.get(tier, 0) + 1
            
            print(f"\nTier breakdown:")
            for tier, count in tiers.items():
                print(f"  {tier}: {count}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Error: {e}")
        if not args.quiet:
            print(f"\n❌ Error: {e}")
            print("\nTroubleshooting:")
            print("- Ensure database exists: python utils/db_manager.py --init")
            print("- Check week has data: python utils/query_tools.py --week {args.week} --matchups")
            print("- Verify database path: python utils/db_manager.py --stats")
        return 1


if __name__ == "__main__":
    exit(main())
