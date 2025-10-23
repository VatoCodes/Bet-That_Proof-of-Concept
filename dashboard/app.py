"""Flask Dashboard for NFL Edge Finder"""

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from pathlib import Path
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from utils.db_manager import DatabaseManager
from utils.query_tools import DatabaseQueryTools
from utils.edge_calculator import EdgeCalculator
from utils.week_manager import WeekManager
from utils.data_validator import DataValidator
from utils.data_quality_validator import DataQualityValidator
from utils.strategy_aggregator import StrategyAggregator
from config import get_current_week
import importlib.util
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'nfl-edge-finder-secret-key-change-in-production'
CORS(app)

# Initialize components
db = DatabaseManager()
week_manager = WeekManager()
strategy_aggregator = StrategyAggregator()  # NEW: Multi-strategy edge aggregator

@app.route('/')
def index():
    """Main dashboard page"""
    current_week = get_current_week()
    return render_template('index.html', current_week=current_week)

@app.route('/api/current-week')
def api_current_week():
    """Get current week"""
    week = get_current_week()
    return jsonify({'week': week})

@app.route('/api/edges', methods=['GET'])
def api_edges():
    """
    Get betting edges for a given week.

    Query Parameters:
        week (int): NFL week number (1-18)
        strategy (str): Filter by strategy - 'all', 'first_half', 'qb_td_v1', 'qb_td_v2', 'kicker' (default: 'all')
        min_edge (float): Minimum edge percentage (default: 5.0)
        season (int): NFL season year (default: 2024)

        # Legacy parameters (for backward compatibility):
        model (str): 'v1' or 'v2' (deprecated, use strategy='qb_td_v1' or 'qb_td_v2')

    Returns:
        JSON with edges, count, metadata
    """
    try:
        # Get parameters
        week = request.args.get('week', type=int)
        strategy = request.args.get('strategy', 'all')  # NEW
        min_edge = request.args.get('min_edge', 5.0, type=float)
        season = request.args.get('season', 2024, type=int)

        # Legacy support for 'model' parameter
        model = request.args.get('model')
        if model:
            logger.warning(f"Legacy 'model' parameter used: {model}. Use 'strategy' instead.")
            # Map old model param to new strategy param
            if model == 'v1':
                strategy = 'qb_td_v1'
            elif model == 'v2':
                strategy = 'qb_td_v2'

        # Validate week
        if not week or week < 1 or week > 18:
            return jsonify({'error': 'Invalid week. Must be 1-18.'}), 400

        # Validate strategy
        valid_strategies = ['all', 'first_half', 'qb_td_v1', 'qb_td_v2', 'kicker']
        if strategy not in valid_strategies:
            return jsonify({'error': f'Invalid strategy. Must be one of: {valid_strategies}'}), 400

        # Get edges using aggregator
        logger.info(f"Fetching edges: week={week}, strategy={strategy}, min_edge={min_edge}")
        edges = strategy_aggregator.get_all_edges(
            week=week,
            season=season,
            min_edge=min_edge,
            strategy=strategy if strategy != 'all' else None
        )

        # Group edges by strategy for response metadata
        strategy_breakdown = {}
        for edge in edges:
            strat = edge.get('strategy', 'Unknown')
            strategy_breakdown[strat] = strategy_breakdown.get(strat, 0) + 1

        return jsonify({
            'edges': edges,
            'count': len(edges),
            'week': week,
            'season': season,
            'strategy_filter': strategy,
            'min_edge': min_edge,
            'strategy_breakdown': strategy_breakdown,
            'success': True
        })

    except Exception as e:
        logger.error(f"Error fetching edges: {str(e)}")
        return jsonify({
            'error': 'Failed to fetch edges',
            'message': str(e),
            'success': False
        }), 500

@app.route('/api/edges/counts', methods=['GET'])
def api_edge_counts():
    """
    Get quick edge counts per strategy (for tab badges).

    Query Parameters:
        week (int): NFL week number (1-18)
        season (int): NFL season year (default: 2024)

    Returns:
        JSON: {"counts": {"first_half": 3, "qb_td_v2": 5, "kicker": 0, "total": 8}, ...}
    """
    try:
        # Get parameters
        week = request.args.get('week', type=int)
        season = request.args.get('season', 2024, type=int)

        # Validate week
        if not week or week < 1 or week > 18:
            return jsonify({'error': 'Invalid week. Must be 1-18.'}), 400

        # Get counts using aggregator
        logger.info(f"Fetching edge counts: week={week}, season={season}")
        counts = strategy_aggregator.get_edge_counts(week=week, season=season)

        return jsonify({
            'counts': counts,
            'week': week,
            'season': season,
            'success': True
        })

    except Exception as e:
        logger.error(f"Error fetching edge counts: {str(e)}")
        return jsonify({
            'error': 'Failed to fetch edge counts',
            'message': str(e),
            'success': False
        }), 500

@app.route('/api/week-range')
def api_week_range():
    """Get available week range for filters"""
    current_week = get_current_week()

    # Provide current week and next 3 weeks
    # Filter out weeks beyond the regular season (18 weeks)
    weeks = []
    for i in range(4):
        week_num = current_week + i
        if week_num <= 18:
            weeks.append(week_num)

    return jsonify({
        'current_week': current_week,
        'available_weeks': weeks
    })

@app.route('/api/weak-defenses')
def api_weak_defenses():
    """Get weak defenses"""
    week = request.args.get('week', get_current_week(), type=int)
    threshold = request.args.get('threshold', 1.7, type=float)
    
    with DatabaseQueryTools() as query_db:
        defenses = query_db.get_weak_defenses(week=week, threshold=threshold)
    
    return jsonify(defenses.to_dict('records'))

@app.route('/api/stats/summary')
def api_stats_summary():
    """Get database statistics summary"""
    db.connect()
    stats = db.get_database_stats()
    db.close()

    # Transform nested structure to flat structure expected by frontend
    flat_stats = {
        'defense_stats': stats['tables'].get('defense_stats', {}).get('row_count', 0),
        'qb_stats': stats['tables'].get('qb_stats', {}).get('row_count', 0),
        'matchups': stats['tables'].get('matchups', {}).get('row_count', 0),
        'odds_spreads': stats['tables'].get('odds_spreads', {}).get('row_count', 0),
        'odds_totals': stats['tables'].get('odds_totals', {}).get('row_count', 0),
        'qb_props': stats['tables'].get('qb_props', {}).get('row_count', 0),
        'database_size_mb': stats.get('database_size_mb', 0),
        'database_path': stats.get('database_path', '')
    }

    return jsonify(flat_stats)

@app.route('/edges')
def edges_page():
    """Edges page with filters"""
    current_week = get_current_week()
    return render_template('edges.html', current_week=current_week)

@app.route('/stats')
def stats_page():
    """Stats and analytics page"""
    current_week = get_current_week()
    return render_template('stats.html', current_week=current_week)

@app.route('/tracker')
def tracker_page():
    """Bet tracker page"""
    current_week = get_current_week()
    return render_template('tracker.html', current_week=current_week)

@app.route('/data-quality')
def data_quality_page():
    """Data Quality Monitoring Dashboard"""
    current_week = get_current_week()
    return render_template('data_quality.html', current_week=current_week)

@app.route('/api/data-quality')
def api_data_quality():
    """Get comprehensive data quality metrics for monitoring dashboard"""
    try:
        import sqlite3
        from datetime import datetime

        db.connect()
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()

        # Query qb_stats_enhanced completeness
        cursor.execute("SELECT COUNT(*) FROM qb_stats_enhanced")
        total_qbs = cursor.fetchone()[0]

        qb_stats_metrics = {}
        if total_qbs > 0:
            metrics = [
                'passing_tds_per_game',
                'deep_ball_completion_pct',
                'pressured_completion_pct',
                'clean_pocket_accuracy',
                'red_zone_accuracy_rating'
            ]

            for metric in metrics:
                cursor.execute(f"SELECT COUNT(*) FROM qb_stats_enhanced WHERE {metric} IS NOT NULL AND {metric} > 0")
                count = cursor.fetchone()[0]
                percentage = (count / total_qbs) * 100
                qb_stats_metrics[metric] = {
                    'count': count,
                    'total': total_qbs,
                    'percentage': round(percentage, 1)
                }

        # Query play_by_play qb_name population
        cursor.execute("SELECT COUNT(*) FROM play_by_play")
        total_plays = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM play_by_play WHERE qb_name IS NOT NULL AND qb_name != ''")
        qb_name_populated = cursor.fetchone()[0]
        qb_name_percentage = (qb_name_populated / total_plays * 100) if total_plays > 0 else 0

        conn.close()
        db.close()

        # Calculate overall health score
        completeness_scores = [m['percentage'] for m in qb_stats_metrics.values()]
        completeness_scores.append(qb_name_percentage)
        overall_health = sum(completeness_scores) / len(completeness_scores) if completeness_scores else 0

        return jsonify({
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'overall_health_score': round(overall_health, 1),
            'qb_stats_enhanced': {
                'total_qbs': total_qbs,
                'metrics': qb_stats_metrics
            },
            'play_by_play': {
                'total_records': total_plays,
                'qb_name_populated': qb_name_populated,
                'qb_name_percentage': round(qb_name_percentage, 1)
            },
            'sql_errors': [
                {
                    'file': 'qb_td_calculator_v2.py',
                    'line': 193,
                    'incorrect': 'rushing_or_passing_touchdown',
                    'correct': 'is_touchdown',
                    'status': 'UNRESOLVED'
                },
                {
                    'file': 'qb_td_calculator_v2.py',
                    'line': 196,
                    'incorrect': 'qb',
                    'correct': 'qb_name',
                    'status': 'UNRESOLVED'
                }
            ],
            'defense_layers': {
                'layer1_pre_deployment': {
                    'status': 'NOT_IMPLEMENTED',
                    'components': ['Calculator SQL Validator', 'Schema validation', 'Dry-run query tests']
                },
                'layer2_data_validator': {
                    'status': 'PARTIAL',
                    'components': ['Column completeness validation', 'Calculator dependency validation', 'Enhanced stats quality scoring', 'Cross-table consistency checks']
                },
                'layer3_integration_testing': {
                    'status': 'MISSING',
                    'components': ['v2 calculator tests', 'SQL query validation tests', 'Edge differentiation tests']
                },
                'layer4_continuous_monitoring': {
                    'status': 'NOT_ACTIVE',
                    'components': ['Daily data quality checks', 'Alert system', 'Quality score tracking']
                },
                'layer5_fallback_transparency': {
                    'status': 'IMPLEMENTED',
                    'components': ['v2 fallback to v1', 'Strategy label shows (limited data)', 'Frontend hides redundant comparisons']
                }
            }
        })

    except Exception as e:
        logger.error(f"Error fetching data quality metrics: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/data-status')
def api_data_status():
    """Get current data validation status"""
    validator = DataValidator()
    results = validator.validate_all()

    status = {
        'status': 'healthy' if not validator.issues else 'critical',
        'issues': validator.issues,
        'warnings': validator.warnings,
        'configured_week': results['week_mismatch']['configured'],
        'has_data': results['week_mismatch']['has_configured_week'],
        'qb_props_count': results['qb_props']['unique_qbs'],
        'completeness': {
            table: data['count']
            for table, data in results['completeness'].items()
        }
    }

    return jsonify(status)

@app.route('/api/health')
def api_health():
    """
    Health check endpoint for monitoring
    Returns system health status
    """
    try:
        quality_validator = DataQualityValidator()
        current_week = get_current_week()

        is_valid, issues = quality_validator.validate_week(current_week)

        status_code = 200 if is_valid else 503

        from datetime import datetime

        response = {
            'healthy': is_valid,
            'current_week': current_week,
            'issues': issues,
            'timestamp': datetime.now().isoformat()
        }

        return jsonify(response), status_code

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'healthy': False,
            'error': str(e)
        }), 503


@app.route('/api/edge/explain/<edge_id>')
async def api_explain_edge(edge_id):
    # Dynamically load orchestrator from .claude directory to avoid import issues
    orchestrator_path = Path(__file__).parent.parent / '.claude' / 'skills_orchestrator.py'
    spec = importlib.util.spec_from_file_location("skills_orchestrator", orchestrator_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    BetThatSkillsOrchestrator = getattr(module, 'BetThatSkillsOrchestrator')
    orchestrator = BetThatSkillsOrchestrator()
    result = await orchestrator.execute_skill("edge_explanation_service", "format_for_dashboard", edge_id=edge_id, style='simple')
    return jsonify(result)

def validate_data_on_startup():
    """Validate data before starting dashboard"""
    print("\n🔍 Validating data before starting dashboard...")

    validator = DataValidator()
    results = validator.validate_all()

    # Critical issues prevent startup
    if validator.issues:
        print("\n❌ CRITICAL ISSUES FOUND - Dashboard cannot start")
        print("   Issues:")
        for issue in validator.issues:
            print(f"      - {issue}")
        print("\n   💡 Run: python3 utils/data_validator.py --fix")
        print()
        sys.exit(1)

    # Warnings don't prevent startup
    if validator.warnings:
        print("\n⚠️  WARNINGS FOUND - Dashboard will start but data may be incomplete")
        for warning in validator.warnings:
            print(f"   - {warning}")
        print("   💡 Run: python3 utils/data_validator.py --check")

    print("✅ Data validation passed!\n")

if __name__ == '__main__':
    # Validate data before starting
    validate_data_on_startup()

    print("\n🎯 NFL Edge Finder Dashboard")
    print("=" * 50)
    print(f"📅 Current Week: {get_current_week()}")
    print(f"🌐 URL: http://localhost:5001")
    print(f"📊 Database: {db.db_path}")
    print("=" * 50)
    print("\n✅ Dashboard running! Press Ctrl+C to stop.\n")

    app.run(debug=True, host='0.0.0.0', port=5001)
