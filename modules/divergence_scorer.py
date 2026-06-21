# modules/divergence_scorer.py
import pandas as pd

def calculate_divergence_requirement(junction_name, event_type, attendance, j_scores_df, e_scores_df):
    """
    Calculates a 0-100 score. Returns dict with score and boolean recommendation.
    """
    try:
        # 1. Event Severity (Fallback to 50 if missing)
        e_match = e_scores_df[e_scores_df["event_cause"].str.lower() == event_type.lower()]
        event_score = e_match.iloc[0]["event_congestion_score"] if not e_match.empty else 50.0

        # 2. Junction Vulnerability (Fallback to 50 if missing)
        j_match = j_scores_df[j_scores_df["junction"].str.lower() == junction_name.lower()]
        junction_risk = j_match.iloc[0]["risk_score"] if not j_match.empty else 50.0

        # 3. Volume Multiplier (Maxes out at 100 impact for 5000+ people)
        volume_score = min((attendance / 5000.0) * 100.0, 100.0)

        # 4. Final Weighted Calculation
        final_score = (event_score * 0.50) + (junction_risk * 0.30) + (volume_score * 0.20)

        # 5. Hard Rules (Accidents, Tree Falls, etc. ALWAYS require divergence)
        absolute_blockers = ['tree_fall', 'vehicle_breakdown', 'debris', 'water_logging', 'construction', 'accident']
        
        requires_divergence = True if (event_type.lower() in absolute_blockers or final_score >= 65.0) else False

        return {
            "score": round(final_score, 1),
            "requires_divergence": requires_divergence
        }
    except Exception as e:
        # Safe fallback if CSVs are unreadable
        return {"score": 50.0, "requires_divergence": True}