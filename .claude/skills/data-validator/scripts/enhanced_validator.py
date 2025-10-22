#!/usr/bin/env python3
"""
Enhanced Data Validator with ML-Powered Anomaly Detection

This module provides comprehensive data validation for the Bet-That system,
including schema validation, anomaly detection, and quality scoring.
"""

import json
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
import sys
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import DBSCAN
import warnings
warnings.filterwarnings('ignore')

# Add parent directories to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from utils.data_validator import DataValidator
from utils.db_manager import DatabaseManager
from utils.query_tools import DatabaseQueryTools
from config import get_database_path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedDataValidator:
    """
    Enhanced data validator with ML-powered anomaly detection.
    
    This class extends the existing data validator with advanced anomaly detection,
    quality scoring, and comprehensive validation rules.
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """Initialize the enhanced data validator."""
        self.db_path = db_path if db_path else get_database_path()
        
        # Initialize core components
        self.base_validator = DataValidator(db_path=self.db_path)
        self.db_manager = DatabaseManager(db_path=self.db_path)
        self.query_tools = DatabaseQueryTools(db_path=self.db_path)
        
        # Load validation rules and configuration
        self.validation_rules = self._load_validation_rules()
        self.anomaly_config = self._load_anomaly_config()
        
        # Initialize ML models
        self.isolation_forest = IsolationForest(contamination=0.1, random_state=42)
        self.scaler = StandardScaler()
        self.dbscan = DBSCAN(eps=0.5, min_samples=3)
        
        # Validation results storage
        self.validation_results = {}
        self.anomaly_results = {}
        self.quality_scores = {}
        
    def _load_validation_rules(self) -> Dict[str, Any]:
        """Load validation rules from validation_rules.json."""
        rules_path = Path(__file__).parent / "resources" / "validation_rules.json"
        try:
            with open(rules_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Validation rules file not found: {rules_path}")
            return self._get_default_validation_rules()
    
    def _load_anomaly_config(self) -> Dict[str, Any]:
        """Load anomaly detection configuration."""
        return {
            "isolation_forest": {
                "contamination": 0.1,
                "random_state": 42
            },
            "dbscan": {
                "eps": 0.5,
                "min_samples": 3
            },
            "thresholds": {
                "outlier_threshold": 0.1,
                "cluster_threshold": 0.05,
                "quality_threshold": 0.8
            }
        }
    
    def _get_default_validation_rules(self) -> Dict[str, Any]:
        """Get default validation rules if config file is not found."""
        return {
            "schema_validation": {
                "required_fields": {
                    "qb_stats": ["qb_name", "team", "week", "tds", "attempts"],
                    "defense_stats": ["team", "week", "tds_allowed", "attempts_faced"],
                    "odds": ["qb_name", "team", "week", "over_odds", "under_odds"],
                    "matchups": ["home_team", "away_team", "week", "game_time"]
                },
                "data_types": {
                    "tds": "integer",
                    "attempts": "integer",
                    "over_odds": "float",
                    "under_odds": "float"
                },
                "value_ranges": {
                    "tds": {"min": 0, "max": 10},
                    "attempts": {"min": 0, "max": 100},
                    "over_odds": {"min": -1000, "max": 1000},
                    "under_odds": {"min": -1000, "max": 1000}
                }
            },
            "quality_scoring": {
                "weights": {
                    "completeness": 0.3,
                    "consistency": 0.25,
                    "accuracy": 0.25,
                    "timeliness": 0.2
                },
                "thresholds": {
                    "excellent": 0.9,
                    "good": 0.8,
                    "fair": 0.7,
                    "poor": 0.6
                }
            }
        }
    
    def validate_all(self) -> Dict[str, Any]:
        """
        Perform comprehensive data validation.
        
        Returns:
            Dictionary with validation results, anomaly detection, and quality scores
        """
        try:
            logger.info("Starting comprehensive data validation...")
            
            # Run base validation
            base_results = self.base_validator.validate_all()
            
            # Run enhanced validation
            enhanced_results = self._run_enhanced_validation()
            
            # Run anomaly detection
            anomaly_results = self._run_anomaly_detection()
            
            # Calculate quality scores
            quality_scores = self._calculate_quality_scores(base_results, enhanced_results, anomaly_results)
            
            # Combine all results
            comprehensive_results = {
                "timestamp": datetime.now().isoformat(),
                "base_validation": base_results,
                "enhanced_validation": enhanced_results,
                "anomaly_detection": anomaly_results,
                "quality_scores": quality_scores,
                "overall_status": self._determine_overall_status(quality_scores),
                "recommendations": self._generate_recommendations(enhanced_results, anomaly_results, quality_scores)
            }
            
            # Store results
            self.validation_results = comprehensive_results
            
            logger.info("Comprehensive data validation completed")
            return comprehensive_results
            
        except Exception as e:
            logger.error(f"Error in comprehensive validation: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "status": "failed"
            }
    
    def _run_enhanced_validation(self) -> Dict[str, Any]:
        """Run enhanced validation rules."""
        try:
            enhanced_results = {
                "schema_validation": self._validate_schema(),
                "data_consistency": self._validate_data_consistency(),
                "business_rules": self._validate_business_rules(),
                "cross_table_validation": self._validate_cross_table_consistency()
            }
            
            return enhanced_results
            
        except Exception as e:
            logger.error(f"Error in enhanced validation: {e}")
            return {"error": str(e)}
    
    def _validate_schema(self) -> Dict[str, Any]:
        """Validate data schema against defined rules."""
        try:
            schema_results = {}
            rules = self.validation_rules.get("schema_validation", {})
            
            # Get all tables
            tables = ["qb_stats", "defense_stats", "odds", "matchups"]
            
            for table in tables:
                try:
                    # Get table data
                    df = self.query_tools.get_table_data(table)
                    
                    if df.empty:
                        schema_results[table] = {
                            "status": "warning",
                            "message": f"No data found in {table}",
                            "issues": []
                        }
                        continue
                    
                    # Check required fields
                    required_fields = rules.get("required_fields", {}).get(table, [])
                    missing_fields = [field for field in required_fields if field not in df.columns]
                    
                    # Check data types
                    type_issues = []
                    data_types = rules.get("data_types", {})
                    for field, expected_type in data_types.items():
                        if field in df.columns:
                            if expected_type == "integer" and not pd.api.types.is_integer_dtype(df[field]):
                                type_issues.append(f"{field} should be integer")
                            elif expected_type == "float" and not pd.api.types.is_numeric_dtype(df[field]):
                                type_issues.append(f"{field} should be float")
                    
                    # Check value ranges
                    range_issues = []
                    value_ranges = rules.get("value_ranges", {})
                    for field, range_config in value_ranges.items():
                        if field in df.columns:
                            min_val = range_config.get("min")
                            max_val = range_config.get("max")
                            if min_val is not None and df[field].min() < min_val:
                                range_issues.append(f"{field} has values below minimum {min_val}")
                            if max_val is not None and df[field].max() > max_val:
                                range_issues.append(f"{field} has values above maximum {max_val}")
                    
                    # Determine status
                    all_issues = missing_fields + type_issues + range_issues
                    status = "pass" if not all_issues else "fail"
                    
                    schema_results[table] = {
                        "status": status,
                        "issues": all_issues,
                        "row_count": len(df),
                        "column_count": len(df.columns)
                    }
                    
                except Exception as e:
                    schema_results[table] = {
                        "status": "error",
                        "error": str(e)
                    }
            
            return schema_results
            
        except Exception as e:
            logger.error(f"Error in schema validation: {e}")
            return {"error": str(e)}
    
    def _validate_data_consistency(self) -> Dict[str, Any]:
        """Validate data consistency within tables."""
        try:
            consistency_results = {}
            
            # Check QB stats consistency
            qb_df = self.query_tools.get_table_data("qb_stats")
            if not qb_df.empty:
                qb_issues = []
                
                # Check for duplicate QB-week combinations
                duplicates = qb_df.duplicated(subset=['qb_name', 'week'], keep=False)
                if duplicates.any():
                    qb_issues.append(f"Duplicate QB-week combinations found: {duplicates.sum()}")
                
                # Check for impossible TD rates
                if 'tds' in qb_df.columns and 'attempts' in qb_df.columns:
                    impossible_rates = qb_df[qb_df['tds'] > qb_df['attempts']]
                    if not impossible_rates.empty:
                        qb_issues.append(f"Impossible TD rates found: {len(impossible_rates)} records")
                
                consistency_results["qb_stats"] = {
                    "status": "pass" if not qb_issues else "fail",
                    "issues": qb_issues
                }
            
            # Check defense stats consistency
            defense_df = self.query_tools.get_table_data("defense_stats")
            if not defense_df.empty:
                defense_issues = []
                
                # Check for duplicate team-week combinations
                duplicates = defense_df.duplicated(subset=['team', 'week'], keep=False)
                if duplicates.any():
                    defense_issues.append(f"Duplicate team-week combinations found: {duplicates.sum()}")
                
                consistency_results["defense_stats"] = {
                    "status": "pass" if not defense_issues else "fail",
                    "issues": defense_issues
                }
            
            return consistency_results
            
        except Exception as e:
            logger.error(f"Error in data consistency validation: {e}")
            return {"error": str(e)}
    
    def _validate_business_rules(self) -> Dict[str, Any]:
        """Validate business rules specific to NFL betting."""
        try:
            business_results = {}
            
            # Check odds consistency
            odds_df = self.query_tools.get_table_data("odds")
            if not odds_df.empty:
                odds_issues = []
                
                # Check for missing odds
                missing_over = odds_df['over_odds'].isna().sum()
                missing_under = odds_df['under_odds'].isna().sum()
                if missing_over > 0:
                    odds_issues.append(f"Missing over odds: {missing_over} records")
                if missing_under > 0:
                    odds_issues.append(f"Missing under odds: {missing_under} records")
                
                # Check for extreme odds values
                extreme_over = odds_df[(odds_df['over_odds'] < -1000) | (odds_df['over_odds'] > 1000)]
                extreme_under = odds_df[(odds_df['under_odds'] < -1000) | (odds_df['under_odds'] > 1000)]
                if not extreme_over.empty:
                    odds_issues.append(f"Extreme over odds values: {len(extreme_over)} records")
                if not extreme_under.empty:
                    odds_issues.append(f"Extreme under odds values: {len(extreme_under)} records")
                
                business_results["odds"] = {
                    "status": "pass" if not odds_issues else "fail",
                    "issues": odds_issues
                }
            
            return business_results
            
        except Exception as e:
            logger.error(f"Error in business rules validation: {e}")
            return {"error": str(e)}
    
    def _validate_cross_table_consistency(self) -> Dict[str, Any]:
        """Validate consistency across different tables."""
        try:
            cross_results = {}
            
            # Check QB stats vs odds consistency
            qb_df = self.query_tools.get_table_data("qb_stats")
            odds_df = self.query_tools.get_table_data("odds")
            
            if not qb_df.empty and not odds_df.empty:
                # Find QBs in stats but not in odds
                qb_stats_qbs = set(qb_df['qb_name'].unique())
                odds_qbs = set(odds_df['qb_name'].unique())
                
                missing_in_odds = qb_stats_qbs - odds_qbs
                missing_in_stats = odds_qbs - qb_stats_qbs
                
                cross_issues = []
                if missing_in_odds:
                    cross_issues.append(f"QBs in stats but not in odds: {len(missing_in_odds)}")
                if missing_in_stats:
                    cross_issues.append(f"QBs in odds but not in stats: {len(missing_in_stats)}")
                
                cross_results["qb_odds_consistency"] = {
                    "status": "pass" if not cross_issues else "fail",
                    "issues": cross_issues
                }
            
            return cross_results
            
        except Exception as e:
            logger.error(f"Error in cross-table validation: {e}")
            return {"error": str(e)}
    
    def _run_anomaly_detection(self) -> Dict[str, Any]:
        """Run ML-powered anomaly detection."""
        try:
            anomaly_results = {}
            
            # Detect anomalies in QB stats
            qb_anomalies = self._detect_qb_anomalies()
            if qb_anomalies:
                anomaly_results["qb_stats"] = qb_anomalies
            
            # Detect anomalies in defense stats
            defense_anomalies = self._detect_defense_anomalies()
            if defense_anomalies:
                anomaly_results["defense_stats"] = defense_anomalies
            
            # Detect anomalies in odds
            odds_anomalies = self._detect_odds_anomalies()
            if odds_anomalies:
                anomaly_results["odds"] = odds_anomalies
            
            return anomaly_results
            
        except Exception as e:
            logger.error(f"Error in anomaly detection: {e}")
            return {"error": str(e)}
    
    def _detect_qb_anomalies(self) -> Dict[str, Any]:
        """Detect anomalies in QB statistics."""
        try:
            qb_df = self.query_tools.get_table_data("qb_stats")
            if qb_df.empty:
                return {"status": "no_data"}
            
            # Prepare features for anomaly detection
            features = ['tds', 'attempts', 'completions', 'passing_yards']
            available_features = [f for f in features if f in qb_df.columns]
            
            if not available_features:
                return {"status": "insufficient_features"}
            
            # Create feature matrix
            X = qb_df[available_features].fillna(0)
            
            # Scale features
            X_scaled = self.scaler.fit_transform(X)
            
            # Detect outliers using Isolation Forest
            outlier_labels = self.isolation_forest.fit_predict(X_scaled)
            outliers = qb_df[outlier_labels == -1]
            
            # Detect clusters using DBSCAN
            cluster_labels = self.dbscan.fit_predict(X_scaled)
            unique_clusters = np.unique(cluster_labels)
            
            anomaly_results = {
                "status": "completed",
                "outliers": {
                    "count": len(outliers),
                    "percentage": len(outliers) / len(qb_df) * 100,
                    "records": outliers.to_dict('records') if not outliers.empty else []
                },
                "clusters": {
                    "count": len(unique_clusters) - (1 if -1 in unique_clusters else 0),
                    "labels": cluster_labels.tolist()
                },
                "features_used": available_features
            }
            
            return anomaly_results
            
        except Exception as e:
            logger.error(f"Error detecting QB anomalies: {e}")
            return {"error": str(e)}
    
    def _detect_defense_anomalies(self) -> Dict[str, Any]:
        """Detect anomalies in defense statistics."""
        try:
            defense_df = self.query_tools.get_table_data("defense_stats")
            if defense_df.empty:
                return {"status": "no_data"}
            
            # Prepare features for anomaly detection
            features = ['tds_allowed', 'attempts_faced', 'completions_allowed', 'passing_yards_allowed']
            available_features = [f for f in features if f in defense_df.columns]
            
            if not available_features:
                return {"status": "insufficient_features"}
            
            # Create feature matrix
            X = defense_df[available_features].fillna(0)
            
            # Scale features
            X_scaled = self.scaler.fit_transform(X)
            
            # Detect outliers using Isolation Forest
            outlier_labels = self.isolation_forest.fit_predict(X_scaled)
            outliers = defense_df[outlier_labels == -1]
            
            anomaly_results = {
                "status": "completed",
                "outliers": {
                    "count": len(outliers),
                    "percentage": len(outliers) / len(defense_df) * 100,
                    "records": outliers.to_dict('records') if not outliers.empty else []
                },
                "features_used": available_features
            }
            
            return anomaly_results
            
        except Exception as e:
            logger.error(f"Error detecting defense anomalies: {e}")
            return {"error": str(e)}
    
    def _detect_odds_anomalies(self) -> Dict[str, Any]:
        """Detect anomalies in odds data."""
        try:
            odds_df = self.query_tools.get_table_data("odds")
            if odds_df.empty:
                return {"status": "no_data"}
            
            # Prepare features for anomaly detection
            features = ['over_odds', 'under_odds']
            available_features = [f for f in features if f in odds_df.columns]
            
            if not available_features:
                return {"status": "insufficient_features"}
            
            # Create feature matrix
            X = odds_df[available_features].fillna(0)
            
            # Scale features
            X_scaled = self.scaler.fit_transform(X)
            
            # Detect outliers using Isolation Forest
            outlier_labels = self.isolation_forest.fit_predict(X_scaled)
            outliers = odds_df[outlier_labels == -1]
            
            anomaly_results = {
                "status": "completed",
                "outliers": {
                    "count": len(outliers),
                    "percentage": len(outliers) / len(odds_df) * 100,
                    "records": outliers.to_dict('records') if not outliers.empty else []
                },
                "features_used": available_features
            }
            
            return anomaly_results
            
        except Exception as e:
            logger.error(f"Error detecting odds anomalies: {e}")
            return {"error": str(e)}
    
    def _calculate_quality_scores(self, base_results: Dict, enhanced_results: Dict, 
                                 anomaly_results: Dict) -> Dict[str, Any]:
        """Calculate comprehensive quality scores."""
        try:
            quality_scores = {}
            
            # Calculate completeness score
            completeness_score = self._calculate_completeness_score(base_results, enhanced_results)
            
            # Calculate consistency score
            consistency_score = self._calculate_consistency_score(enhanced_results)
            
            # Calculate accuracy score
            accuracy_score = self._calculate_accuracy_score(anomaly_results)
            
            # Calculate timeliness score
            timeliness_score = self._calculate_timeliness_score()
            
            # Calculate overall score
            weights = self.validation_rules.get("quality_scoring", {}).get("weights", {
                "completeness": 0.3,
                "consistency": 0.25,
                "accuracy": 0.25,
                "timeliness": 0.2
            })
            
            overall_score = (
                completeness_score * weights["completeness"] +
                consistency_score * weights["consistency"] +
                accuracy_score * weights["accuracy"] +
                timeliness_score * weights["timeliness"]
            )
            
            quality_scores = {
                "completeness": completeness_score,
                "consistency": consistency_score,
                "accuracy": accuracy_score,
                "timeliness": timeliness_score,
                "overall": overall_score,
                "grade": self._get_quality_grade(overall_score)
            }
            
            return quality_scores
            
        except Exception as e:
            logger.error(f"Error calculating quality scores: {e}")
            return {"error": str(e)}
    
    def _calculate_completeness_score(self, base_results: Dict, enhanced_results: Dict) -> float:
        """Calculate data completeness score."""
        try:
            # Count total fields and missing fields
            total_fields = 0
            missing_fields = 0
            
            # Check base validation results
            if "issues" in base_results:
                for issue in base_results["issues"]:
                    if "missing" in issue.lower():
                        missing_fields += 1
                    total_fields += 1
            
            # Check enhanced validation results
            if "schema_validation" in enhanced_results:
                for table, result in enhanced_results["schema_validation"].items():
                    if "issues" in result:
                        for issue in result["issues"]:
                            if "missing" in issue.lower():
                                missing_fields += 1
                            total_fields += 1
            
            if total_fields == 0:
                return 1.0
            
            completeness_score = 1.0 - (missing_fields / total_fields)
            return max(0.0, min(1.0, completeness_score))
            
        except Exception as e:
            logger.error(f"Error calculating completeness score: {e}")
            return 0.5
    
    def _calculate_consistency_score(self, enhanced_results: Dict) -> float:
        """Calculate data consistency score."""
        try:
            consistency_issues = 0
            total_checks = 0
            
            # Check data consistency
            if "data_consistency" in enhanced_results:
                for table, result in enhanced_results["data_consistency"].items():
                    total_checks += 1
                    if result.get("status") == "fail":
                        consistency_issues += len(result.get("issues", []))
            
            # Check cross-table consistency
            if "cross_table_validation" in enhanced_results:
                for check, result in enhanced_results["cross_table_validation"].items():
                    total_checks += 1
                    if result.get("status") == "fail":
                        consistency_issues += len(result.get("issues", []))
            
            if total_checks == 0:
                return 1.0
            
            consistency_score = 1.0 - (consistency_issues / total_checks)
            return max(0.0, min(1.0, consistency_score))
            
        except Exception as e:
            logger.error(f"Error calculating consistency score: {e}")
            return 0.5
    
    def _calculate_accuracy_score(self, anomaly_results: Dict) -> float:
        """Calculate data accuracy score based on anomaly detection."""
        try:
            total_records = 0
            anomalous_records = 0
            
            for table, result in anomaly_results.items():
                if "outliers" in result:
                    outliers = result["outliers"]
                    anomalous_records += outliers.get("count", 0)
                    total_records += outliers.get("count", 0) + 100  # Estimate total records
            
            if total_records == 0:
                return 1.0
            
            accuracy_score = 1.0 - (anomalous_records / total_records)
            return max(0.0, min(1.0, accuracy_score))
            
        except Exception as e:
            logger.error(f"Error calculating accuracy score: {e}")
            return 0.5
    
    def _calculate_timeliness_score(self) -> float:
        """Calculate data timeliness score."""
        try:
            # Check if data is recent (within last 24 hours)
            current_time = datetime.now()
            
            # Get latest data timestamps
            latest_qb = self.query_tools.get_latest_data_timestamp("qb_stats")
            latest_defense = self.query_tools.get_latest_data_timestamp("defense_stats")
            latest_odds = self.query_tools.get_latest_data_timestamp("odds")
            
            timestamps = [latest_qb, latest_defense, latest_odds]
            timestamps = [ts for ts in timestamps if ts is not None]
            
            if not timestamps:
                return 0.0
            
            # Calculate time differences
            time_diffs = [(current_time - ts).total_seconds() / 3600 for ts in timestamps]
            avg_hours_old = sum(time_diffs) / len(time_diffs)
            
            # Score based on recency (24 hours = 1.0, 48 hours = 0.5, etc.)
            timeliness_score = max(0.0, 1.0 - (avg_hours_old / 24))
            return min(1.0, timeliness_score)
            
        except Exception as e:
            logger.error(f"Error calculating timeliness score: {e}")
            return 0.5
    
    def _get_quality_grade(self, score: float) -> str:
        """Get quality grade based on score."""
        thresholds = self.validation_rules.get("quality_scoring", {}).get("thresholds", {
            "excellent": 0.9,
            "good": 0.8,
            "fair": 0.7,
            "poor": 0.6
        })
        
        if score >= thresholds["excellent"]:
            return "A"
        elif score >= thresholds["good"]:
            return "B"
        elif score >= thresholds["fair"]:
            return "C"
        elif score >= thresholds["poor"]:
            return "D"
        else:
            return "F"
    
    def _determine_overall_status(self, quality_scores: Dict) -> str:
        """Determine overall validation status."""
        try:
            overall_score = quality_scores.get("overall", 0)
            grade = quality_scores.get("grade", "F")
            
            if grade in ["A", "B"]:
                return "excellent"
            elif grade == "C":
                return "good"
            elif grade == "D":
                return "fair"
            else:
                return "poor"
                
        except Exception as e:
            logger.error(f"Error determining overall status: {e}")
            return "unknown"
    
    def _generate_recommendations(self, enhanced_results: Dict, anomaly_results: Dict, 
                                 quality_scores: Dict) -> List[str]:
        """Generate recommendations based on validation results."""
        try:
            recommendations = []
            
            # Check quality scores
            overall_score = quality_scores.get("overall", 0)
            if overall_score < 0.8:
                recommendations.append("Data quality is below optimal levels. Consider data cleaning and validation improvements.")
            
            # Check for anomalies
            for table, result in anomaly_results.items():
                if "outliers" in result:
                    outlier_count = result["outliers"].get("count", 0)
                    if outlier_count > 0:
                        recommendations.append(f"Found {outlier_count} anomalous records in {table}. Review for data quality issues.")
            
            # Check for consistency issues
            if "data_consistency" in enhanced_results:
                for table, result in enhanced_results["data_consistency"].items():
                    if result.get("status") == "fail":
                        recommendations.append(f"Data consistency issues found in {table}. Review duplicate records and data integrity.")
            
            # Check for schema issues
            if "schema_validation" in enhanced_results:
                for table, result in enhanced_results["schema_validation"].items():
                    if result.get("status") == "fail":
                        recommendations.append(f"Schema validation issues found in {table}. Review data types and required fields.")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return ["Error generating recommendations"]
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """Get a summary of validation results."""
        try:
            if not self.validation_results:
                return {"status": "no_validation_run"}
            
            return {
                "timestamp": self.validation_results.get("timestamp"),
                "overall_status": self.validation_results.get("overall_status"),
                "quality_grade": self.validation_results.get("quality_scores", {}).get("grade"),
                "overall_score": self.validation_results.get("quality_scores", {}).get("overall"),
                "recommendations_count": len(self.validation_results.get("recommendations", [])),
                "anomalies_detected": sum(
                    result.get("outliers", {}).get("count", 0) 
                    for result in self.validation_results.get("anomaly_detection", {}).values()
                    if "outliers" in result
                )
            }
            
        except Exception as e:
            logger.error(f"Error getting validation summary: {e}")
            return {"error": str(e)}

def main():
    """Main function for testing the enhanced data validator."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Enhanced Data Validator")
    parser.add_argument('--summary-only', action='store_true',
                       help='Show only summary statistics')
    parser.add_argument('--anomaly-only', action='store_true',
                       help='Run only anomaly detection')
    parser.add_argument('--export', type=str,
                       help='Export results to JSON file')
    
    args = parser.parse_args()
    
    # Initialize validator
    validator = EnhancedDataValidator()
    
    if args.anomaly_only:
        # Run only anomaly detection
        anomaly_results = validator._run_anomaly_detection()
        print("🔍 Anomaly Detection Results:")
        print(json.dumps(anomaly_results, indent=2, default=str))
    else:
        # Run full validation
        results = validator.validate_all()
        
        if args.summary_only:
            summary = validator.get_validation_summary()
            print("📊 Validation Summary:")
            print(json.dumps(summary, indent=2, default=str))
        else:
            print("📊 Comprehensive Validation Results:")
            print(json.dumps(results, indent=2, default=str))
        
        if args.export:
            with open(args.export, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"Results exported to {args.export}")

if __name__ == "__main__":
    main()
