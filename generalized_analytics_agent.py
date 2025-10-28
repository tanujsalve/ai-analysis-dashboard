#!/usr/bin/env python3
"""
Generalized Analytics Agent for User Dashboard
This agent can analyze any uploaded Excel/CSV data and provide insights
"""

import pandas as pd
import numpy as np
import json
import io
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
import re
from datetime import datetime

@dataclass
class DataInsight:
    """Represents a data insight"""
    insight_type: str  # "statistical", "pattern", "anomaly", "trend", "correlation"
    title: str
    description: str
    confidence: float
    data_points: List[Any]
    visualization_suggestion: Optional[str] = None

class GeneralizedAnalyticsAgent:
    """Generalized agent that can analyze any structured data"""
    
    def __init__(self):
        self.data_cache = {}
        self.analysis_history = []
        
    def analyze_data(self, data: Union[pd.DataFrame, str], filename: str = None) -> Dict[str, Any]:
        """
        Main entry point for data analysis
        
        Args:
            data: DataFrame or file path to analyze
            filename: Optional filename for context
            
        Returns:
            Dictionary containing analysis results
        """
        try:
            # Convert data to DataFrame if needed
            if isinstance(data, str):
                df = self._load_data_from_path(data)
            else:
                df = data.copy()
            
            if df is None or df.empty:
                return {
                    "success": False,
                    "error": "No data to analyze",
                    "summary": "The uploaded file appears to be empty or invalid."
                }
            
            # Store data in cache
            self.data_cache[filename or "current_data"] = df
            
            # Perform comprehensive analysis
            analysis_results = {
                "success": True,
                "data_summary": self._get_data_summary(df),
                "statistical_insights": self._get_statistical_insights(df),
                "data_quality": self._get_data_quality_analysis(df),
                "pattern_analysis": self._get_pattern_analysis(df),
                "visualization_suggestions": self._get_visualization_suggestions(df),
                "recommendations": self._get_recommendations(df),
                "sample_data": df.head(10).to_dict('records') if len(df) > 0 else []
            }
            
            # Store analysis in history
            self.analysis_history.append({
                "timestamp": datetime.now().isoformat(),
                "filename": filename,
                "summary": analysis_results["data_summary"]
            })
            
            return analysis_results
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "summary": f"Analysis failed: {str(e)}"
            }
    
    def _load_data_from_path(self, file_path: str) -> Optional[pd.DataFrame]:
        """Load data from file path"""
        try:
            if file_path.endswith('.csv'):
                return pd.read_csv(file_path)
            elif file_path.endswith(('.xlsx', '.xls')):
                return pd.read_excel(file_path)
            else:
                # Try to detect format
                try:
                    return pd.read_csv(file_path)
                except:
                    return pd.read_excel(file_path)
        except Exception as e:
            print(f"Error loading file: {e}")
            return None
    
    def _get_data_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Get basic data summary"""
        return {
            "total_rows": len(df),
            "total_columns": len(df.columns),
            "column_names": list(df.columns),
            "data_types": df.dtypes.astype(str).to_dict(),
            "memory_usage": f"{df.memory_usage(deep=True).sum() / 1024:.2f} KB",
            "date_range": self._get_date_range(df) if self._has_date_columns(df) else None
        }
    
    def _get_statistical_insights(self, df: pd.DataFrame) -> List[DataInsight]:
        """Generate statistical insights"""
        insights = []
        
        # Numeric columns analysis
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        
        for col in numeric_cols:
            if df[col].notna().sum() > 0:
                stats = df[col].describe()
                
                # High variance detection
                if stats['std'] > stats['mean'] * 0.5:
                    insights.append(DataInsight(
                        insight_type="statistical",
                        title=f"High Variance in {col}",
                        description=f"Column '{col}' shows high variability (std: {stats['std']:.2f}, mean: {stats['mean']:.2f})",
                        confidence=0.8,
                        data_points=[stats['std'], stats['mean']],
                        visualization_suggestion="histogram"
                    ))
                
                # Outlier detection
                Q1 = stats['25%']
                Q3 = stats['75%']
                IQR = Q3 - Q1
                outliers = df[(df[col] < Q1 - 1.5*IQR) | (df[col] > Q3 + 1.5*IQR)]
                
                if len(outliers) > 0:
                    insights.append(DataInsight(
                        insight_type="anomaly",
                        title=f"Outliers Detected in {col}",
                        description=f"Found {len(outliers)} outliers in column '{col}'",
                        confidence=0.9,
                        data_points=list(outliers[col].values),
                        visualization_suggestion="boxplot"
                    ))
        
        # Categorical columns analysis
        categorical_cols = df.select_dtypes(include=['object']).columns
        
        for col in categorical_cols:
            if df[col].notna().sum() > 0:
                value_counts = df[col].value_counts()
                
                # High frequency values
                if len(value_counts) > 0:
                    most_common = value_counts.iloc[0]
                    total = len(df[col].dropna())
                    
                    if most_common / total > 0.5:
                        insights.append(DataInsight(
                            insight_type="pattern",
                            title=f"Dominant Value in {col}",
                            description=f"'{value_counts.index[0]}' appears in {most_common/total*100:.1f}% of records",
                            confidence=0.9,
                            data_points=[value_counts.index[0], most_common],
                            visualization_suggestion="pie_chart"
                        ))
        
        return insights
    
    def _get_data_quality_analysis(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze data quality"""
        quality_report = {
            "missing_data": {},
            "duplicate_rows": len(df) - len(df.drop_duplicates()),
            "data_types_issues": []
        }
        
        # Missing data analysis
        for col in df.columns:
            missing_count = df[col].isna().sum()
            if missing_count > 0:
                quality_report["missing_data"][col] = {
                    "count": missing_count,
                    "percentage": missing_count / len(df) * 100
                }
        
        # Data type issues
        for col in df.columns:
            if df[col].dtype == 'object':
                # Check if numeric data is stored as text
                numeric_pattern = r'^-?\d+\.?\d*$'
                numeric_count = df[col].astype(str).str.match(numeric_pattern).sum()
                if numeric_count > len(df[col].dropna()) * 0.8:
                    quality_report["data_types_issues"].append({
                        "column": col,
                        "issue": "Numeric data stored as text",
                        "suggestion": "Convert to numeric type"
                    })
        
        return quality_report
    
    def _get_pattern_analysis(self, df: pd.DataFrame) -> List[DataInsight]:
        """Analyze patterns in the data"""
        insights = []
        
        # Correlation analysis for numeric columns
        numeric_df = df.select_dtypes(include=[np.number])
        if len(numeric_df.columns) > 1:
            corr_matrix = numeric_df.corr()
            
            # Find strong correlations
            for i in range(len(corr_matrix.columns)):
                for j in range(i+1, len(corr_matrix.columns)):
                    corr_value = corr_matrix.iloc[i, j]
                    if abs(corr_value) > 0.7:
                        insights.append(DataInsight(
                            insight_type="correlation",
                            title=f"Strong Correlation Found",
                            description=f"'{corr_matrix.columns[i]}' and '{corr_matrix.columns[j]}' have a correlation of {corr_value:.3f}",
                            confidence=0.8,
                            data_points=[corr_value],
                            visualization_suggestion="scatter_plot"
                        ))
        
        # Time series patterns (if date columns exist)
        if self._has_date_columns(df):
            date_col = self._get_date_column(df)
            if date_col:
                df_sorted = df.sort_values(date_col)
                numeric_cols = df_sorted.select_dtypes(include=[np.number]).columns
                
                for col in numeric_cols:
                    if len(df_sorted) > 10:
                        # Simple trend detection
                        first_half = df_sorted[col].iloc[:len(df_sorted)//2].mean()
                        second_half = df_sorted[col].iloc[len(df_sorted)//2:].mean()
                        
                        if abs(second_half - first_half) / first_half > 0.1:
                            trend = "increasing" if second_half > first_half else "decreasing"
                            insights.append(DataInsight(
                                insight_type="trend",
                                title=f"Trend in {col}",
                                description=f"Column '{col}' shows {trend} trend over time",
                                confidence=0.7,
                                data_points=[first_half, second_half],
                                visualization_suggestion="line_chart"
                            ))
        
        return insights
    
    def _get_visualization_suggestions(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Suggest appropriate visualizations"""
        suggestions = []
        
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        categorical_cols = df.select_dtypes(include=['object']).columns
        
        # Histogram for numeric columns
        for col in numeric_cols:
            suggestions.append({
                "type": "histogram",
                "title": f"Distribution of {col}",
                "description": f"Shows the distribution of values in {col}",
                "columns": [col]
            })
        
        # Bar chart for categorical columns
        for col in categorical_cols:
            if df[col].nunique() < 20:  # Only for columns with few unique values
                suggestions.append({
                    "type": "bar_chart",
                    "title": f"Count by {col}",
                    "description": f"Shows the count of records for each value in {col}",
                    "columns": [col]
                })
        
        # Scatter plot for numeric pairs
        if len(numeric_cols) >= 2:
            suggestions.append({
                "type": "scatter_plot",
                "title": f"Relationship between {numeric_cols[0]} and {numeric_cols[1]}",
                "description": f"Shows the relationship between {numeric_cols[0]} and {numeric_cols[1]}",
                "columns": list(numeric_cols[:2])
            })
        
        return suggestions
    
    def _get_recommendations(self, df: pd.DataFrame) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        # Data quality recommendations
        missing_data = df.isna().sum()
        if missing_data.sum() > 0:
            recommendations.append("Consider handling missing data through imputation or removal")
        
        if len(df) - len(df.drop_duplicates()) > 0:
            recommendations.append("Remove duplicate rows to improve data quality")
        
        # Analysis recommendations
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            recommendations.append("Perform statistical analysis on numeric columns")
        
        categorical_cols = df.select_dtypes(include=['object']).columns
        if len(categorical_cols) > 0:
            recommendations.append("Analyze categorical distributions and patterns")
        
        # Visualization recommendations
        if len(df.columns) > 5:
            recommendations.append("Consider dimensionality reduction techniques")
        
        if len(df) > 1000:
            recommendations.append("Use sampling techniques for large dataset analysis")
        
        return recommendations
    
    def _has_date_columns(self, df: pd.DataFrame) -> bool:
        """Check if DataFrame has date columns"""
        return any(df[col].dtype.name.startswith('datetime') for col in df.columns)
    
    def _get_date_column(self, df: pd.DataFrame) -> Optional[str]:
        """Get the first date column"""
        for col in df.columns:
            if df[col].dtype.name.startswith('datetime'):
                return col
        return None
    
    def _get_date_range(self, df: pd.DataFrame) -> Dict[str, str]:
        """Get date range if date columns exist"""
        date_col = self._get_date_column(df)
        if date_col:
            return {
                "start": str(df[date_col].min()),
                "end": str(df[date_col].max())
            }
        return {}
    
    def generate_chart_data(self, df: pd.DataFrame, chart_type: str, columns: List[str]) -> Dict[str, Any]:
        """Generate chart data for visualization"""
        try:
            if chart_type == "histogram":
                col = columns[0]
                counts, bins = np.histogram(df[col].dropna(), bins=10)
                return {
                    "type": "bar",
                    "title": f"Distribution of {col}",
                    "labels": [f"{bins[i]:.1f}-{bins[i+1]:.1f}" for i in range(len(counts))],
                    "data": counts.tolist(),
                    "colors": ["#3b82f6"]
                }
            
            elif chart_type == "bar_chart":
                col = columns[0]
                value_counts = df[col].value_counts().head(10)
                return {
                    "type": "bar",
                    "title": f"Count by {col}",
                    "labels": value_counts.index.tolist(),
                    "data": value_counts.values.tolist(),
                    "colors": ["#10b981"]
                }
            
            elif chart_type == "pie_chart":
                col = columns[0]
                value_counts = df[col].value_counts().head(8)
                return {
                    "type": "pie",
                    "title": f"Distribution of {col}",
                    "labels": value_counts.index.tolist(),
                    "data": value_counts.values.tolist(),
                    "colors": ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4", "#84cc16", "#f97316"]
                }
            
            elif chart_type == "scatter_plot":
                if len(columns) >= 2:
                    x_col, y_col = columns[0], columns[1]
                    return {
                        "type": "scatter",
                        "title": f"{x_col} vs {y_col}",
                        "labels": [f"Point {i}" for i in range(len(df))],
                        "data": df[[x_col, y_col]].dropna().values.tolist(),
                        "colors": ["#3b82f6"]
                    }
            
            elif chart_type == "line_chart":
                if len(columns) >= 2:
                    x_col, y_col = columns[0], columns[1]
                    sorted_df = df.sort_values(x_col)
                    return {
                        "type": "line",
                        "title": f"{y_col} over {x_col}",
                        "labels": sorted_df[x_col].tolist(),
                        "data": sorted_df[y_col].tolist(),
                        "colors": ["#3b82f6"]
                    }
            
            return {"error": "Unsupported chart type"}
            
        except Exception as e:
            return {"error": str(e)}
    
    def get_analysis_history(self) -> List[Dict[str, Any]]:
        """Get analysis history"""
        return self.analysis_history
    
    def clear_cache(self):
        """Clear data cache"""
        self.data_cache.clear()
        self.analysis_history.clear()
