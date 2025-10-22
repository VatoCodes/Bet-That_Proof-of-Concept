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
from config import get_current_week

app = Flask(__name__)
app.config['SECRET_KEY'] = 'nfl-edge-finder-secret-key-change-in-production'
CORS(app)

# Initialize components
db = DatabaseManager()
week_manager = WeekManager()

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

@app.route('/api/edges')
def api_edges():
    """Get edge opportunities"""
    week = request.args.get('week', get_current_week(), type=int)
    min_edge = request.args.get('min_edge', 0.05, type=float)
    model = request.args.get('model', 'v1', type=str)
    
    # Initialize edge calculator
    calculator = EdgeCalculator(model_version=model)
    
    # Get edges
    edges = calculator.find_edges_for_week(week=week, threshold=min_edge)
    
    return jsonify(edges)

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
    
    return jsonify(stats)

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
