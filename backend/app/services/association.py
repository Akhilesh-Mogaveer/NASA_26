"""Association Processing and Ambiguity Classification for FireLens.

Structures candidate associations, assigns candidate rankings,
determines multiplicity types (1:1, 1:N, N:1, M:N), identifies
ambiguous associations, and tracks unmatched observations.
"""
from typing import List, Dict, Any, Set, Tuple
from collections import defaultdict
from datetime import datetime, timezone
import pandas as pd

from app.services.matching_config import (
    AssociationRecord,
    MatchingConfig,
    STRONG_PROXIMITY_THRESHOLD,
    AMBIGUITY_SCORE_DELTA,
)


class AssociationProcessor:
    """Processes candidate pairs into ranked, classified AssociationRecords."""

    def __init__(self, config: MatchingConfig):
        self.config = config

    def process_associations(
        self,
        raw_candidates: List[Dict[str, Any]],
        modis_input_df: pd.DataFrame,
        viirs_input_df: pd.DataFrame,
    ) -> Dict[str, Any]:
        """Classify and structure candidate pairs into associations and unmatched records."""
        # Map candidates by MODIS ID and VIIRS ID for degree/multiplicity tracking
        modis_to_candidates: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        viirs_to_candidates: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        for c in raw_candidates:
            m_id = c["modis_observation_id"]
            v_id = c["viirs_observation_id"]
            modis_to_candidates[m_id].append(c)
            viirs_to_candidates[v_id].append(c)

        # Sort candidates per MODIS observation by heuristic_score DESC, distance_km ASC
        for m_id, c_list in modis_to_candidates.items():
            c_list.sort(key=lambda x: (-x["heuristic_score"], x["distance_km"]))
            for rank, item in enumerate(c_list, start=1):
                item["candidate_rank"] = rank

        # Sort candidates per VIIRS observation similarly
        for v_id, c_list in viirs_to_candidates.items():
            c_list.sort(key=lambda x: (-x["heuristic_score"], x["distance_km"]))

        # Identify ambiguous observations
        ambiguous_modis_ids: Set[str] = set()
        for m_id, c_list in modis_to_candidates.items():
            if len(c_list) >= 2:
                # If top two candidates have scores within delta, mark as ambiguous
                if (c_list[0]["heuristic_score"] - c_list[1]["heuristic_score"]) <= AMBIGUITY_SCORE_DELTA:
                    ambiguous_modis_ids.add(m_id)

        ambiguous_viirs_ids: Set[str] = set()
        for v_id, c_list in viirs_to_candidates.items():
            if len(c_list) >= 2:
                if (c_list[0]["heuristic_score"] - c_list[1]["heuristic_score"]) <= AMBIGUITY_SCORE_DELTA:
                    ambiguous_viirs_ids.add(v_id)

        # Build structured AssociationRecords
        structured_associations: List[AssociationRecord] = []
        now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        for m_id, c_list in modis_to_candidates.items():
            m_degree = len(c_list)
            is_m_ambiguous = m_id in ambiguous_modis_ids

            for c in c_list:
                v_id = c["viirs_observation_id"]
                v_degree = len(viirs_to_candidates[v_id])
                is_v_ambiguous = v_id in ambiguous_viirs_ids

                # Multiplicity determination
                if m_degree == 1 and v_degree == 1:
                    multiplicity = "1:1"
                elif m_degree > 1 and v_degree == 1:
                    multiplicity = "1:N"  # Sub-pixel splitting
                elif m_degree == 1 and v_degree > 1:
                    multiplicity = "N:1"  # MODIS footprint overlap
                else:
                    multiplicity = "M:N"  # Complex multi-pixel cluster

                # Classification determination
                if is_m_ambiguous or is_v_ambiguous or multiplicity == "M:N":
                    classification = "ambiguous_association"
                elif (c["spatial_score"] >= STRONG_PROXIMITY_THRESHOLD and
                      c["temporal_score"] >= STRONG_PROXIMITY_THRESHOLD):
                    classification = "strong_proximity"
                else:
                    classification = "candidate_association"

                assoc_id = f"ASSOC-{m_id}-{v_id}"

                rec = AssociationRecord(
                    association_id=assoc_id,
                    modis_observation_id=m_id,
                    viirs_observation_id=v_id,
                    modis_timestamp_utc=c["modis_timestamp_utc"],
                    viirs_timestamp_utc=c["viirs_timestamp_utc"],
                    distance_km=c["distance_km"],
                    time_diff_minutes=c["time_diff_minutes"],
                    spatial_score=c["spatial_score"],
                    temporal_score=c["temporal_score"],
                    heuristic_score=c["heuristic_score"],
                    candidate_rank=c["candidate_rank"],
                    classification=classification,
                    multiplicity_type=multiplicity,
                    modis_frp=c["modis_frp"],
                    viirs_frp=c["viirs_frp"],
                    modis_latitude=c["modis_latitude"],
                    modis_longitude=c["modis_longitude"],
                    viirs_latitude=c["viirs_latitude"],
                    viirs_longitude=c["viirs_longitude"],
                    modis_satellite=c["modis_satellite"],
                    viirs_satellite=c["viirs_satellite"],
                    spatial_radius_km=c["spatial_radius_km"],
                    temporal_window_minutes=c["temporal_window_minutes"],
                    processed_at=now_utc,
                )
                structured_associations.append(rec)

        # Unmatched observations
        matched_modis_ids = set(modis_to_candidates.keys())
        matched_viirs_ids = set(viirs_to_candidates.keys())

        # MODIS unmatched
        m_obs_col = "observation_id" if "observation_id" in modis_input_df.columns else modis_input_df.columns[0]
        unmatched_modis_df = modis_input_df[~modis_input_df[m_obs_col].isin(matched_modis_ids)].copy()
        unmatched_modis = unmatched_modis_df[[
            m_obs_col, "latitude", "longitude", "timestamp_utc", "frp", "satellite", "instrument"
        ]].rename(columns={m_obs_col: "observation_id"}).to_dict(orient="records") if not unmatched_modis_df.empty else []

        # VIIRS unmatched
        v_obs_col = "observation_id" if "observation_id" in viirs_input_df.columns else viirs_input_df.columns[0]
        unmatched_viirs_df = viirs_input_df[~viirs_input_df[v_obs_col].isin(matched_viirs_ids)].copy()
        unmatched_viirs = unmatched_viirs_df[[
            v_obs_col, "latitude", "longitude", "timestamp_utc", "frp", "satellite", "instrument"
        ]].rename(columns={v_obs_col: "observation_id"}).to_dict(orient="records") if not unmatched_viirs_df.empty else []

        # Multiplicity counts
        multiplicity_counts = {"1:1": 0, "1:N": 0, "N:1": 0, "M:N": 0}
        classification_counts = {
            "strong_proximity": 0,
            "candidate_association": 0,
            "ambiguous_association": 0,
        }
        for a in structured_associations:
            multiplicity_counts[a.multiplicity_type] = multiplicity_counts.get(a.multiplicity_type, 0) + 1
            classification_counts[a.classification] = classification_counts.get(a.classification, 0) + 1

        summary = {
            "total_associations": len(structured_associations),
            "unique_modis_matched": len(matched_modis_ids),
            "unique_viirs_matched": len(matched_viirs_ids),
            "unmatched_modis_count": len(unmatched_modis),
            "unmatched_viirs_count": len(unmatched_viirs),
            "ambiguous_modis_count": len(ambiguous_modis_ids),
            "ambiguous_viirs_count": len(ambiguous_viirs_ids),
            "multiplicity_breakdown": multiplicity_counts,
            "classification_breakdown": classification_counts,
        }

        return {
            "associations": structured_associations,
            "unmatched_modis": unmatched_modis,
            "unmatched_viirs": unmatched_viirs,
            "summary": summary,
        }
