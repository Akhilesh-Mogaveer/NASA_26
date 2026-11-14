"""Matching Evaluation and Sensitivity Analysis Engine for FireLens.

Evaluates spatial-temporal matching across all 12 candidate parameter combinations:
Spatial radii: [1.25 km, 2.0 km, 3.5 km]
Temporal windows: [15 min, 30 min, 60 min, 90 min]
Calculates association counts, ambiguity rates, distance and time statistics,
and generates comparative sensitivity matrices.
"""
import statistics
from typing import List, Dict, Any, Optional
import numpy as np
import pandas as pd

from app.services.matching_config import (
    CANDIDATE_SPATIAL_RADII_KM,
    CANDIDATE_TEMPORAL_WINDOWS_MINUTES,
    MatchingConfig,
)
from app.services.candidate_generation import CandidateGenerator
from app.services.association import AssociationProcessor


class MatchingEvaluator:
    """Runs systematic sensitivity evaluations across all 12 parameter combinations."""

    def __init__(
        self,
        spatial_radii: Optional[List[float]] = None,
        temporal_windows: Optional[List[float]] = None,
    ):
        self.spatial_radii = spatial_radii or CANDIDATE_SPATIAL_RADII_KM
        self.temporal_windows = temporal_windows or CANDIDATE_TEMPORAL_WINDOWS_MINUTES

    def evaluate_grid(
        self,
        modis_df: pd.DataFrame,
        viirs_df: pd.DataFrame,
        weight_spatial: float = 0.5,
        weight_temporal: float = 0.5,
    ) -> List[Dict[str, Any]]:
        """Run all 12 parameter combinations and compute detailed sensitivity metrics."""
        results: List[Dict[str, Any]] = []

        total_modis = len(modis_df)
        total_viirs = len(viirs_df)

        for radius in self.spatial_radii:
            for window in self.temporal_windows:
                cfg = MatchingConfig(
                    spatial_radius_km=radius,
                    temporal_window_minutes=window,
                    weight_spatial=weight_spatial,
                    weight_temporal=weight_temporal,
                    valid_only=True,
                    exclude_duplicates=True,
                )

                generator = CandidateGenerator(cfg)
                raw_candidates = generator.generate_candidates(modis_df, viirs_df)

                processor = AssociationProcessor(cfg)
                processed = processor.process_associations(raw_candidates, modis_df, viirs_df)

                assocs = processed["associations"]
                summary = processed["summary"]

                # Calculate distance and time stats
                distances = [a.distance_km for a in assocs]
                time_diffs = [a.time_diff_minutes for a in assocs]
                scores = [a.heuristic_score for a in assocs]

                mean_dist = round(float(np.mean(distances)), 3) if distances else 0.0
                median_dist = round(float(np.median(distances)), 3) if distances else 0.0
                mean_time = round(float(np.mean(time_diffs)), 2) if time_diffs else 0.0
                median_time = round(float(np.median(time_diffs)), 2) if time_diffs else 0.0
                mean_score = round(float(np.mean(scores)), 3) if scores else 0.0

                mult = summary["multiplicity_breakdown"]
                classif = summary["classification_breakdown"]

                # Candidate ratios
                candidates_per_modis = round(
                    len(assocs) / max(1, summary["unique_modis_matched"]), 2
                ) if summary["unique_modis_matched"] > 0 else 0.0
                candidates_per_viirs = round(
                    len(assocs) / max(1, summary["unique_viirs_matched"]), 2
                ) if summary["unique_viirs_matched"] > 0 else 0.0

                # Ambiguity percentages
                modis_ambiguity_pct = round(
                    summary["ambiguous_modis_count"] / max(1, summary["unique_modis_matched"]) * 100.0, 2
                ) if summary["unique_modis_matched"] > 0 else 0.0

                viirs_ambiguity_pct = round(
                    summary["ambiguous_viirs_count"] / max(1, summary["unique_viirs_matched"]) * 100.0, 2
                ) if summary["unique_viirs_matched"] > 0 else 0.0

                # Match rates
                modis_match_rate = round(summary["unique_modis_matched"] / max(1, total_modis) * 100.0, 2)
                viirs_match_rate = round(summary["unique_viirs_matched"] / max(1, total_viirs) * 100.0, 2)

                results.append({
                    "spatial_radius_km": radius,
                    "temporal_window_minutes": window,
                    "total_modis_considered": total_modis,
                    "total_viirs_considered": total_viirs,
                    "candidate_association_count": len(assocs),
                    "unique_modis_matched": summary["unique_modis_matched"],
                    "unique_viirs_matched": summary["unique_viirs_matched"],
                    "unmatched_modis_count": summary["unmatched_modis_count"],
                    "unmatched_viirs_count": summary["unmatched_viirs_count"],
                    "modis_match_rate_pct": modis_match_rate,
                    "viirs_match_rate_pct": viirs_match_rate,
                    "ambiguous_modis_count": summary["ambiguous_modis_count"],
                    "ambiguous_viirs_count": summary["ambiguous_viirs_count"],
                    "modis_ambiguity_pct": modis_ambiguity_pct,
                    "viirs_ambiguity_pct": viirs_ambiguity_pct,
                    "one_to_one_count": mult.get("1:1", 0),
                    "one_to_many_count": mult.get("1:N", 0),
                    "many_to_one_count": mult.get("N:1", 0),
                    "many_to_many_count": mult.get("M:N", 0),
                    "strong_proximity_count": classif.get("strong_proximity", 0),
                    "candidate_association_count_only": classif.get("candidate_association", 0),
                    "ambiguous_association_count": classif.get("ambiguous_association", 0),
                    "mean_distance_km": mean_dist,
                    "median_distance_km": median_dist,
                    "mean_time_diff_min": mean_time,
                    "median_time_diff_min": median_time,
                    "candidates_per_matched_modis": candidates_per_modis,
                    "candidates_per_matched_viirs": candidates_per_viirs,
                    "mean_heuristic_score": mean_score,
                })

        return results

    @staticmethod
    def to_dataframe(results: List[Dict[str, Any]]) -> pd.DataFrame:
        """Convert sensitivity evaluation results to Pandas DataFrame."""
        return pd.DataFrame(results)
