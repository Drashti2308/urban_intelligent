"""Urban Infrastructure Pulse — simple single-page Streamlit GUI.

Place in: <project root>/dashboard/urban_pulse_simple.py
Run from project root:
    python -m streamlit run dashboard/urban_pulse_simple.py

Uses the project's existing, validated geographic, historical and three-model
pipeline. It does not write uploaded CSVs or modify historical models.
"""

from __future__ import annotations

import hashlib
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.integration.upload_preflight import run_upload_preflight
from src.integration.live_uploaded_batch_pipeline import (
    load_upload_baseline,
    process_uploaded_csv_bytes,
)
from src.integration.investigation_review_queue import build_review_queue
from src.ui.service_factory import get_gui_adapter

st.set_page_config(
    page_title="Urban Infrastructure Pulse",
    page_icon="🏙️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

TEMPLATE = ROOT / "outputs/templates/new_complaints_template.csv"
TAXONOMY = ROOT / "outputs/tables/dbscan/dbscan_action_taxonomy_v1.csv"


@st.cache_data(show_spinner=False)
def supported_categories() -> list[str]:
    values = pd.read_csv(TAXONOMY, dtype="string")["complaint_category"]
    return sorted({str(v).strip().upper() for v in values.dropna()})


@st.cache_resource(show_spinner=False)
def existing_backend_adapter():
    return get_gui_adapter()


@st.cache_resource(show_spinner=False)
def existing_historical_baseline():
    return load_upload_baseline(ROOT)


def show_location_review(item: dict, feed: dict) -> None:
    """Render the evidence and action in the format used by the explainer."""
    st.subheader(f"{item['location']} — {item['category'].title()}")
    pattern = ", ".join(item.get("kmeans_patterns", [])) or "Not assigned (limited area evidence)"
    st.markdown(f"**Peer group (K-Means):** {pattern}")

    if item["kind"] == "area_category":
        count = item["incoming_reports"]
        spatial_count = item["spatial_overlap_reports"]
        st.markdown("**Where complaints gather (DBSCAN)**")
        if spatial_count:
            st.write(
                f"{spatial_count} of the {count} reports belong to newly found "
                "spatial concentration(s) in this reporting area."
            )
        else:
            st.write("No linked spatial concentration was detected for these reports.")
        st.markdown("**What is unusual (anomaly detection)**")
        st.write(
            f"{count} new reports; historical seasonal daily maximum: "
            f"{item['seasonal_max']}; historical all-weekday daily maximum: "
            f"{item['all_weekday_max']}."
        )
    else:
        st.markdown("**Where complaints gather (DBSCAN)**")
        st.write(
            f"{item['incoming_reports']} nearby reports form new spatial "
            f"candidate {item['candidate_id']}."
        )
        st.markdown("**What is unusual (anomaly detection)**")
        st.write(
            "This spatial group has no linked qualifying historical-count "
            "anomaly. That does not mean it is safe or unsafe."
        )

    st.markdown("**Why investigate?**")
    st.write(item["why"])
    st.markdown("**Suggested action**")
    st.write(item["suggested_action"])
    st.caption(item["evidence_note"])

    linked_ids = set(item.get("linked_spatial_ids", []))
    if linked_ids:
        positions = []
        for feature in feed["map_geojson"]["features"]:
            if str(feature["id"]) in linked_ids:
                lon, lat = feature["geometry"]["coordinates"]
                positions.append({
                    "latitude": float(lat),
                    "longitude": float(lon),
                    "spatial_candidate": str(feature["id"]),
                })
        if positions:
            with st.expander("Show approximate reported concentration on map"):
                st.map(pd.DataFrame(positions)[["latitude", "longitude"]])
                st.caption(
                    "Pins represent selected submitted complaint coordinates, "
                    "not confirmed faults or verified intersections."
                )


def main() -> None:
    st.title("Urban Infrastructure Pulse")
    st.write("**Upload complaints. Find places worth investigating. See why and what to check.**")
    st.caption("One-screen workflow • existing verified backend • no automatic repair decisions")

    if not TAXONOMY.is_file():
        st.error("Category taxonomy is missing from the project. No models were run.")
        st.stop()

    # STEP 1: file upload + initial validation.
    st.header("1. Upload and validate CSV")
    if TEMPLATE.is_file():
        st.download_button(
            "Download CSV template",
            TEMPLATE.read_bytes(),
            file_name="new_complaints_template.csv",
            mime="text/csv",
        )

    uploaded = st.file_uploader("Choose your complaints CSV", type=["csv"])
    c1, c2 = st.columns([1, 1])
    day = c1.date_input("Reporting date (NYC)", value=date.today())
    synthetic = c2.checkbox("This is test / synthetic data", value=True)
    st.caption("CSV limit: 10 MB / 5,000 reports. All records are audited; only eligible records are analyzed.")

    payload = uploaded.getvalue() if uploaded is not None else None
    file_key = hashlib.sha256(payload).hexdigest() if payload else None
    run_key = (file_key, day.isoformat(), bool(synthetic))

    if st.button("Validate CSV", disabled=payload is None, type="secondary"):
        try:
            result = run_upload_preflight(payload, supported_categories())
        except Exception as exc:
            st.session_state.pop("pulse_preflight", None)
            st.session_state.pop("pulse_preflight_key", None)
            st.error(f"CSV validation failed: {exc}")
        else:
            st.session_state["pulse_preflight_key"] = file_key
            st.session_state["pulse_preflight"] = result
            st.session_state.pop("pulse_analysis", None)
            st.session_state.pop("pulse_analysis_key", None)

    validated = (
        bool(file_key)
        and st.session_state.get("pulse_preflight_key") == file_key
        and "pulse_preflight" in st.session_state
    )
    if validated:
        checked = st.session_state["pulse_preflight"]
        st.success(f"CSV checked: {checked['row_count']} submitted reports. You can continue to analysis.")
        if checked.get("status_counts"):
            st.write("**Initial validation results:** " + ", ".join(
                f"{label}: {count}" for label, count in checked["status_counts"].items()
            ))
        with st.expander("View row-level validation details"):
            st.dataframe(checked["validation_results"], hide_index=True, use_container_width=True)
        st.caption("Geographic verification happens during analysis. Passing this step does not confirm a complaint location.")

    # STEP 2: existing backend, strictly after validation for this same file.
    st.header("2. Analyze complaints")
    if not validated:
        st.info("Upload a CSV and click **Validate CSV** to unlock analysis.")
    if st.button("Analyze and get recommendations", type="primary", disabled=not validated):
        try:
            with st.spinner("Checking locations and running the three existing models..."):
                with threadpool_limits(limits=1):
                    result = process_uploaded_csv_bytes(
                        payload,
                        day.isoformat(),
                        ROOT,
                        synthetic_data=bool(synthetic),
                        adapter=existing_backend_adapter(),
                        baseline=existing_historical_baseline(),
                    )
                feed = result.get("feed")
                queue = build_review_queue(feed) if feed is not None else None
        except Exception as exc:
            st.session_state.pop("pulse_analysis", None)
            st.session_state.pop("pulse_analysis_key", None)
            st.error(f"Analysis could not finish: {type(exc).__name__}: {exc}")
        else:
            # Keep only what the UI needs; original backend and historical files stay untouched.
            st.session_state["pulse_analysis_key"] = run_key
            st.session_state["pulse_analysis"] = {
                "selection": result["selection_stats"],
                "uploaded": result["uploaded_rows"],
                "audit": result["backend_records"],
                "feed": feed,
                "review": queue,
            }

    current = st.session_state.get("pulse_analysis")
    if current is None or st.session_state.get("pulse_analysis_key") != run_key:
        st.stop()

    # STEP 3: usable recommendations rather than raw model dumps.
    st.header("3. Investigation recommendations")
    selection = current["selection"]
    a, b, c = st.columns(3)
    a.metric("Uploaded reports", current["uploaded"])
    b.metric("Analyzed for selected day", selection["selected_for_new_models"])
    c.metric("Excluded from analysis", current["uploaded"] - selection["selected_for_new_models"])

    with st.expander("Why were some records excluded? / Download audit"):
        st.write(
            f"Geographic or backend-quality exclusions: {selection['excluded_by_backend_quality']}. "
            f"Other-day reports: {selection['excluded_by_reporting_day']}."
        )
        st.download_button(
            "Download complete backend audit CSV",
            current["audit"].to_csv(index=False).encode("utf-8"),
            file_name="urban_pulse_backend_audit.csv",
            mime="text/csv",
        )

    feed, review = current["feed"], current["review"]
    if feed is None:
        st.info("No geographically verified complaints belong to this date. No conclusions were generated.")
        return

    if feed["metadata"].get("synthetic_data", False):
        st.warning("Synthetic test data — these are demonstration findings, not live incidents.")
    else:
        st.info("Uploaded reports have not been independently verified in the field.")

    summary = review["summary"]
    x, y, z = st.columns(3)
    x.metric("Review first · two signals", summary["review_first_groups"])
    y.metric("Other spatial findings", summary["spatial_only_groups"])
    z.metric("Distinct reports with a signal", summary["distinct_with_signals"])
    st.caption(
        "Review-first means a reporting-count increase and nearby-complaint concentration occur together. "
        "It is not an emergency ranking, risk score, or repair order."
    )

    items = review["queue"]
    if not items:
        st.success("No review candidates met the existing screening rules for this batch.")
        return

    # One compact overview, with details for only the selected location.
    overview = pd.DataFrame([
        {
            "Review order": item["review_order"],
            "Place": item["location"],
            "Issue": item["category"].title(),
            "Reports": item["incoming_reports"],
            "Finding": "Two signals" if item["tier"] == 1 else (
                "Reporting increase" if item["tier"] == 2 else "Spatial concentration"
            ),
        }
        for item in items
    ])
    st.markdown("**Places worth reviewing**")
    st.dataframe(overview, hide_index=True, use_container_width=True, height=285)

    choices = list(range(len(items)))
    chosen_index = st.selectbox(
        "Choose a place to see WHY and WHAT TO DO",
        choices,
        format_func=lambda idx: (
            f"{items[idx]['review_order']}. {items[idx]['location']} "
            f"— {items[idx]['category'].title()}"
        ),
    )
    with st.container(border=True):
        show_location_review(items[chosen_index], feed)

    export = pd.DataFrame([
        {
            "Review order": item["review_order"],
            "Place": item["location"],
            "Issue": item["category"],
            "Reports": item["incoming_reports"],
            "Why investigate": item["why"],
            "Suggested action": item["suggested_action"],
            "Evidence limitation": item["evidence_note"],
        }
        for item in items
    ])
    st.download_button(
        "Download all investigation recommendations (CSV)",
        export.to_csv(index=False).encode("utf-8"),
        file_name="urban_pulse_investigation_recommendations.csv",
        mime="text/csv",
    )
    st.caption(
        "K-Means = similar area reporting patterns; DBSCAN = geographic concentration; "
        "anomaly screening = unusual historical complaint counts. "
        "Review original reports and maintenance records before operational action."
    )


# Explicit one-page navigation hides the older pages without deleting them.
# This relies on Streamlit's supported st.Page/st.navigation API.
st.navigation(
    [st.Page(main, title="Urban Infrastructure Pulse", default=True)],
    position="hidden",
).run()
