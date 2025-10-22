#!/usr/bin/env python3
"""
Conversational Analyzer for Bet Edge Analysis

This module provides natural language analysis of betting opportunities,
integrating with the existing edge calculator to provide detailed explanations
and recommendations in conversational format.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import sys

# Add parent directories to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from utils.edge_calculator import EdgeCalculator
from utils.query_tools import DatabaseQueryTools
from utils.db_manager import DatabaseManager
from config import get_database_path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConversationalAnalyzer:
    """
    Provides conversational analysis of betting opportunities.
    
    This class integrates with the existing edge calculator to provide
    natural language explanations of betting opportunities, including
    detailed analysis of probabilities, edge calculations, and recommendations.
    """
    
    def __init__(self, model_version: str = "v2", db_path: Optional[Path] = None):
        """Initialize the conversational analyzer."""
        self.model_version = model_version
        self.db_path = db_path if db_path else get_database_path()
        
        # Initialize core components
        self.edge_calculator = EdgeCalculator(model_version=model_version, db_path=self.db_path)
        self.query_tools = DatabaseQueryTools(db_path=self.db_path)
        self.db_manager = DatabaseManager(db_path=self.db_path)
        
        # Load configuration
        self.config = self._load_config()
        
        # Analysis templates
        self.templates = self._load_templates()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from model_configs.json."""
        config_path = Path(__file__).parent / "resources" / "model_configs.json"
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Config file not found: {config_path}")
            return {}
    
    def _load_templates(self) -> Dict[str, str]:
        """Load analysis templates."""
        return {
            "edge_summary": """
## 🎯 Betting Edge Analysis: {qb_name} vs {defense_name}

**Week {week} | {game_time}**

### 📊 Edge Summary
- **True Probability**: {true_prob:.1%}
- **Implied Odds**: {implied_prob:.1%}
- **Edge**: {edge_percent:.1%} ({edge_status})
- **Confidence**: {confidence_level}

### 💰 Bet Recommendation
- **Action**: {recommendation}
- **Bet Size**: {bet_size:.1%} of bankroll (${bet_amount:.2f})
- **Expected Value**: ${expected_value:.2f}

### 🔍 Analysis Breakdown
{analysis_breakdown}

### ⚠️ Risk Factors
{risk_factors}

### 📈 Historical Context
{historical_context}
""",
            
            "probability_breakdown": """
**Probability Calculation Breakdown:**

1. **Base QB Performance**: {qb_base_prob:.1%}
   - Season TD Rate: {qb_td_rate:.2f} TDs/game
   - Recent Form: {qb_recent_form}

2. **Defense Adjustment**: {defense_adjustment:+.1%}
   - Defense TD Rate: {defense_td_rate:.2f} TDs/game
   - Recent Performance: {defense_recent_performance}

3. **Matchup Context**: {context_adjustment:+.1%}
   - Home/Away: {home_away}
   - Weather: {weather_impact}
   - Rest Days: {rest_days}

4. **Model Confidence**: {model_confidence:.1%}
""",
            
            "risk_assessment": """
**Risk Assessment:**

- **Data Quality**: {data_quality}
- **Sample Size**: {sample_size}
- **Model Reliability**: {model_reliability}
- **Market Efficiency**: {market_efficiency}
- **External Factors**: {external_factors}
""",
            
            "historical_context": """
**Historical Context:**

- **QB vs Defense**: {qb_vs_defense_history}
- **Similar Matchups**: {similar_matchups}
- **Trend Analysis**: {trend_analysis}
- **Market Movement**: {market_movement}
"""
        }
    
    def analyze_edge_opportunity(self, edge_data: Dict[str, Any]) -> str:
        """
        Provide conversational analysis of a single edge opportunity.
        
        Args:
            edge_data: Edge opportunity data from EdgeCalculator
            
        Returns:
            Formatted conversational analysis
        """
        try:
            # Extract key information
            qb_name = edge_data.get('qb_name', 'Unknown QB')
            defense_name = edge_data.get('defense_name', 'Unknown Defense')
            week = edge_data.get('week', 'Unknown')
            game_time = edge_data.get('game_time', 'Unknown')
            
            # Calculate derived metrics
            true_prob = edge_data.get('true_probability', 0)
            implied_prob = edge_data.get('implied_probability', 0)
            edge_percent = edge_data.get('edge_percentage', 0)
            
            # Determine edge status
            if edge_percent >= 0.15:
                edge_status = "🔥 EXCELLENT"
            elif edge_percent >= 0.10:
                edge_status = "✅ STRONG"
            elif edge_percent >= 0.05:
                edge_status = "⚠️ MODERATE"
            else:
                edge_status = "❌ WEAK"
            
            # Get confidence level
            confidence_level = edge_data.get('confidence_level', 'low')
            confidence_emoji = {
                'high': '🟢',
                'medium': '🟡',
                'low': '🔴'
            }.get(confidence_level, '🔴')
            
            # Generate recommendation
            recommendation, bet_size, bet_amount, expected_value = self._generate_recommendation(edge_data)
            
            # Generate detailed analysis
            analysis_breakdown = self._generate_probability_breakdown(edge_data)
            risk_factors = self._generate_risk_assessment(edge_data)
            historical_context = self._generate_historical_context(edge_data)
            
            # Format the analysis
            analysis = self.templates["edge_summary"].format(
                qb_name=qb_name,
                defense_name=defense_name,
                week=week,
                game_time=game_time,
                true_prob=true_prob,
                implied_prob=implied_prob,
                edge_percent=edge_percent * 100,
                edge_status=edge_status,
                confidence_level=f"{confidence_emoji} {confidence_level.upper()}",
                recommendation=recommendation,
                bet_size=bet_size * 100,
                bet_amount=bet_amount,
                expected_value=expected_value,
                analysis_breakdown=analysis_breakdown,
                risk_factors=risk_factors,
                historical_context=historical_context
            )
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing edge opportunity: {e}")
            return f"❌ Error analyzing edge opportunity: {str(e)}"
    
    def _generate_recommendation(self, edge_data: Dict[str, Any]) -> Tuple[str, float, float, float]:
        """Generate betting recommendation with Kelly Criterion sizing."""
        try:
            edge_percent = edge_data.get('edge_percentage', 0)
            true_prob = edge_data.get('true_probability', 0)
            implied_prob = edge_data.get('implied_probability', 0)
            bankroll = edge_data.get('bankroll', 1000)
            
            # Kelly Criterion calculation
            if implied_prob > 0 and true_prob > implied_prob:
                kelly_fraction = (true_prob * (1 - implied_prob) - (1 - true_prob) * implied_prob) / (1 - implied_prob)
                kelly_fraction = max(0, min(kelly_fraction, 0.25))  # Cap at 25%
            else:
                kelly_fraction = 0
            
            bet_amount = bankroll * kelly_fraction
            expected_value = bet_amount * edge_percent
            
            # Determine recommendation
            if edge_percent >= 0.15 and kelly_fraction >= 0.05:
                recommendation = "🎯 STRONG BET - High edge with good Kelly sizing"
            elif edge_percent >= 0.10 and kelly_fraction >= 0.03:
                recommendation = "✅ MODERATE BET - Good edge with reasonable sizing"
            elif edge_percent >= 0.05 and kelly_fraction >= 0.01:
                recommendation = "⚠️ SMALL BET - Moderate edge with conservative sizing"
            else:
                recommendation = "❌ NO BET - Insufficient edge or Kelly sizing"
            
            return recommendation, kelly_fraction, bet_amount, expected_value
            
        except Exception as e:
            logger.error(f"Error generating recommendation: {e}")
            return "❌ Error generating recommendation", 0, 0, 0
    
    def _generate_probability_breakdown(self, edge_data: Dict[str, Any]) -> str:
        """Generate detailed probability breakdown."""
        try:
            # This would integrate with the actual probability calculation logic
            # For now, provide a template structure
            
            qb_stats = edge_data.get('qb_stats', {})
            defense_stats = edge_data.get('defense_stats', {})
            matchup_context = edge_data.get('matchup_context', {})
            
            qb_base_prob = qb_stats.get('td_rate', 0.15)
            defense_adjustment = -defense_stats.get('td_rate', 0.15) * 0.1
            context_adjustment = matchup_context.get('home_advantage', 0.02)
            model_confidence = edge_data.get('model_confidence', 0.75)
            
            return self.templates["probability_breakdown"].format(
                qb_base_prob=qb_base_prob,
                qb_td_rate=qb_stats.get('td_rate', 0.15),
                qb_recent_form=qb_stats.get('recent_form', 'Average'),
                defense_adjustment=defense_adjustment * 100,
                defense_td_rate=defense_stats.get('td_rate', 0.15),
                defense_recent_performance=defense_stats.get('recent_performance', 'Average'),
                context_adjustment=context_adjustment * 100,
                home_away=matchup_context.get('home_away', 'Neutral'),
                weather_impact=matchup_context.get('weather', 'Normal'),
                rest_days=matchup_context.get('rest_days', 'Normal'),
                model_confidence=model_confidence * 100
            )
            
        except Exception as e:
            logger.error(f"Error generating probability breakdown: {e}")
            return "❌ Error generating probability breakdown"
    
    def _generate_risk_assessment(self, edge_data: Dict[str, Any]) -> str:
        """Generate risk assessment."""
        try:
            # Assess various risk factors
            data_quality = "🟢 High" if edge_data.get('data_quality', 0.8) > 0.7 else "🟡 Medium" if edge_data.get('data_quality', 0.8) > 0.5 else "🔴 Low"
            sample_size = "🟢 Large" if edge_data.get('sample_size', 8) > 6 else "🟡 Medium" if edge_data.get('sample_size', 8) > 3 else "🔴 Small"
            model_reliability = "🟢 High" if edge_data.get('model_reliability', 0.8) > 0.7 else "🟡 Medium" if edge_data.get('model_reliability', 0.8) > 0.5 else "🔴 Low"
            market_efficiency = "🟢 Efficient" if edge_data.get('market_efficiency', 0.8) > 0.7 else "🟡 Moderate" if edge_data.get('market_efficiency', 0.8) > 0.5 else "🔴 Inefficient"
            external_factors = "🟢 Minimal" if edge_data.get('external_factors', 0.2) < 0.3 else "🟡 Moderate" if edge_data.get('external_factors', 0.2) < 0.6 else "🔴 High"
            
            return self.templates["risk_assessment"].format(
                data_quality=data_quality,
                sample_size=sample_size,
                model_reliability=model_reliability,
                market_efficiency=market_efficiency,
                external_factors=external_factors
            )
            
        except Exception as e:
            logger.error(f"Error generating risk assessment: {e}")
            return "❌ Error generating risk assessment"
    
    def _generate_historical_context(self, edge_data: Dict[str, Any]) -> str:
        """Generate historical context analysis."""
        try:
            # This would integrate with historical data analysis
            # For now, provide a template structure
            
            qb_vs_defense_history = "No direct history available"
            similar_matchups = "Limited similar matchup data"
            trend_analysis = "QB showing consistent TD production"
            market_movement = "Odds stable, no significant movement"
            
            return self.templates["historical_context"].format(
                qb_vs_defense_history=qb_vs_defense_history,
                similar_matchups=similar_matchups,
                trend_analysis=trend_analysis,
                market_movement=market_movement
            )
            
        except Exception as e:
            logger.error(f"Error generating historical context: {e}")
            return "❌ Error generating historical context"
    
    def analyze_week_edges(self, week: int, threshold: float = 0.05, 
                          min_confidence: str = "low") -> str:
        """
        Provide conversational analysis of all edges for a given week.
        
        Args:
            week: NFL week to analyze
            threshold: Minimum edge percentage threshold
            min_confidence: Minimum confidence level
            
        Returns:
            Formatted analysis of all edges for the week
        """
        try:
            # Get edges for the week
            edges = self.edge_calculator.find_edges_for_week(
                week=week,
                threshold=threshold,
                min_confidence=min_confidence
            )
            
            if not edges:
                return f"## 📊 Week {week} Edge Analysis\n\n❌ No betting edges found above {threshold:.1%} threshold."
            
            # Generate analysis for each edge
            analyses = []
            for i, edge in enumerate(edges, 1):
                analysis = self.analyze_edge_opportunity(edge)
                analyses.append(f"### Edge #{i}\n{analysis}")
            
            # Create summary
            total_edges = len(edges)
            avg_edge = sum(e.get('edge_percentage', 0) for e in edges) / total_edges
            max_edge = max(e.get('edge_percentage', 0) for e in edges)
            
            summary = f"""
## 📊 Week {week} Edge Analysis Summary

**Total Edges Found**: {total_edges}
**Average Edge**: {avg_edge:.1%}
**Maximum Edge**: {max_edge:.1%}
**Threshold**: {threshold:.1%}
**Min Confidence**: {min_confidence}

---

"""
            
            return summary + "\n\n".join(analyses)
            
        except Exception as e:
            logger.error(f"Error analyzing week edges: {e}")
            return f"❌ Error analyzing week {week} edges: {str(e)}"
    
    def get_edge_summary(self, week: int) -> Dict[str, Any]:
        """
        Get a summary of edge opportunities for a given week.
        
        Args:
            week: NFL week to analyze
            
        Returns:
            Dictionary with edge summary statistics
        """
        try:
            edges = self.edge_calculator.find_edges_for_week(week=week, threshold=0.01)
            
            if not edges:
                return {
                    "week": week,
                    "total_edges": 0,
                    "average_edge": 0,
                    "maximum_edge": 0,
                    "total_expected_value": 0,
                    "recommended_bets": 0
                }
            
            total_edges = len(edges)
            average_edge = sum(e.get('edge_percentage', 0) for e in edges) / total_edges
            maximum_edge = max(e.get('edge_percentage', 0) for e in edges)
            
            # Calculate total expected value
            total_expected_value = 0
            recommended_bets = 0
            
            for edge in edges:
                edge_percent = edge.get('edge_percentage', 0)
                if edge_percent >= 0.05:  # Only count edges above 5%
                    recommended_bets += 1
                    total_expected_value += edge.get('expected_value', 0)
            
            return {
                "week": week,
                "total_edges": total_edges,
                "average_edge": average_edge,
                "maximum_edge": maximum_edge,
                "total_expected_value": total_expected_value,
                "recommended_bets": recommended_bets
            }
            
        except Exception as e:
            logger.error(f"Error getting edge summary: {e}")
            return {
                "week": week,
                "error": str(e)
            }

def main():
    """Main function for testing the conversational analyzer."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Conversational Bet Edge Analyzer")
    parser.add_argument('--week', type=int, required=True, help='NFL week to analyze')
    parser.add_argument('--model', type=str, default='v2', choices=['v1', 'v2'],
                       help='Probability model version')
    parser.add_argument('--threshold', type=float, default=0.05,
                       help='Minimum edge percentage threshold')
    parser.add_argument('--min-confidence', type=str, default='low',
                       choices=['low', 'medium', 'high'],
                       help='Minimum confidence level')
    parser.add_argument('--summary-only', action='store_true',
                       help='Show only summary statistics')
    
    args = parser.parse_args()
    
    # Initialize analyzer
    analyzer = ConversationalAnalyzer(model_version=args.model)
    
    if args.summary_only:
        # Show summary only
        summary = analyzer.get_edge_summary(args.week)
        print(f"\n📊 Week {args.week} Edge Summary:")
        print(f"Total Edges: {summary.get('total_edges', 0)}")
        print(f"Average Edge: {summary.get('average_edge', 0):.1%}")
        print(f"Maximum Edge: {summary.get('maximum_edge', 0):.1%}")
        print(f"Recommended Bets: {summary.get('recommended_bets', 0)}")
        print(f"Total Expected Value: ${summary.get('total_expected_value', 0):.2f}")
    else:
        # Show full analysis
        analysis = analyzer.analyze_week_edges(
            week=args.week,
            threshold=args.threshold,
            min_confidence=args.min_confidence
        )
        print(analysis)

if __name__ == "__main__":
    main()