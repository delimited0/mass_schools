import altair as alt
import pandas as pd
import streamlit as st
from pathlib import Path

try:
    alt.data_transformers.enable("vegafusion")
except Exception:
    alt.data_transformers.disable_max_rows()

st.set_page_config(layout="wide", page_title="Massachusetts School Trends Over Time")

SAT_DATA_PATTERN = "SAT_Performance_*"
DEMOGRAPHICS_DATA_PATTERN = "Enrollment__Grade,_Race_Ethnicity,_Gender,_and_Selected_Populations_*"
DISCIPLINE_DATA_PATTERN = "Student_Discipline_*"
MCAS_DATA_PATTERN = "MCAS_Achievement_Results_*"
SUPPLEMENTAL_DATA_FILES = [
    "pittsford_sat_scores.csv",
]
HIGHLIGHT_COLORS = [
    "#00E5FF", "#FF9800", "#69FF47", "#FF4081",
    "#FFEB3B", "#B388FF", "#FF6E40", "#40C4FF",
]
RACE_GROUPS = [
    "American Indian or Alaska Native",
    "Asian",
    "Black or African American",
    "Hispanic or Latino",
    "Multi-Race, Not Hispanic or Latino",
    "Native Hawaiian or Other Pacific Islander",
    "White",
]
RACE_COLORS = [
    "#1f77b4",
    "#ff7f0e",
    "#2ca02c",
    "#d62728",
    "#9467bd",
    "#8c564b",
    "#e377c2",
]
DISADVANTAGED_GROUPS = [
    "High Needs",
    "English Learners",
    "Low Income",
    "Students with Disabilities",
    "Economically Disadvantaged",
]
DISADVANTAGED_COLORS = [
    "#1f77b4",
    "#ff7f0e",
    "#2ca02c",
    "#d62728",
    "#9467bd",
]
MCAS_SUBJECT_LABELS = {
    "ELA": "ELA",
    "MATH": "Math",
    "SCI": "Science",
    "BIO": "Biology",
    "PHY": "Physics",
    "CIV": "Civics",
}
MCAS_SUBJECT_ORDER = ["ELA", "MATH", "SCI", "BIO", "PHY", "CIV"]
MCAS_GRADE_ORDER = ["03", "04", "05", "06", "07", "08", "10", "ALL (03-08)", "HS SCI"]
MCAS_STAGE_GRADE_MAP = {
    "Elementary school": {"03", "04", "05"},
    "Middle school": {"06", "07", "08"},
    "High school": {"10", "HS SCI"},
}
RACE_PCT_COLUMNS = {
    "American Indian or Alaska Native": "AIAN_PCT",
    "Asian": "AS_PCT",
    "Black or African American": "BAA_PCT",
    "Hispanic or Latino": "HL_PCT",
    "Multi-Race, Not Hispanic or Latino": "MNHL_PCT",
    "Native Hawaiian or Other Pacific Islander": "NHPI_PCT",
    "White": "WH_PCT",
}
DISADVANTAGED_COLUMNS = {
    "High Needs": ("HN_CNT", "HN_PCT"),
    "English Learners": ("EL_CNT", "EL_PCT"),
    "Low Income": ("LI_CNT", "LI_PCT"),
    "Students with Disabilities": ("SWD_CNT", "SWD_PCT"),
    "Economically Disadvantaged": ("ECD_CNT", "ECD_PCT"),
}
SAT_REQUIRED_COLUMNS = [
    "ORG_TYPE",
    "ORG_CODE",
    "ORG_NAME",
    "DIST_CODE",
    "DIST_NAME",
    "SY",
    "STU_GRP",
    "TAKEN_CNT",
    "READ_SCORE",
    "WRITE_SCORE",
    "READ_WRITE_SCORE",
    "MATH_SCORE",
]
DEMOGRAPHICS_REQUIRED_COLUMNS = [
    "ORG_TYPE",
    "ORG_CODE",
    "ORG_NAME",
    "DIST_CODE",
    "DIST_NAME",
    "SY",
    "TOTAL_CNT",
    *sorted(set(RACE_PCT_COLUMNS.values())),
    *sorted({count_col for count_col, _ in DISADVANTAGED_COLUMNS.values()}),
    *sorted({pct_col for _, pct_col in DISADVANTAGED_COLUMNS.values()}),
]
DISCIPLINE_REQUIRED_COLUMNS = [
    "ORG_TYPE",
    "ORG_CODE",
    "ORG_NAME",
    "DIST_CODE",
    "DIST_NAME",
    "SY",
    "STU_GRP",
    "OFFENSE",
    "STU_CNT",
    "STU_DISCIPL_CNT",
    "IN_SUSP_PCT",
    "OUT_SUSP_PCT",
    "EXP_PCT",
    "ALT_SETTING_PCT",
    "EMERG_RMVL_PCT",
    "ARREST_PCT",
    "LAWENF_REF_PCT",
]
MCAS_REQUIRED_COLUMNS = [
    "ORG_TYPE",
    "ORG_CODE",
    "ORG_NAME",
    "DIST_CODE",
    "DIST_NAME",
    "SY",
    "TEST_GRADE",
    "SUBJECT_CODE",
    "STU_GRP",
    "AVG_SCALED_SCORE",
    "STU_PART_PCT",
    "STU_CNT",
]

base = Path(__file__).resolve().parent


def collect_versioned_data_paths(base_path, stem_glob):
    candidate_paths = sorted(
        list(base_path.glob(f"{stem_glob}.csv")) + list(base_path.glob(f"{stem_glob}.parquet"))
    )
    preferred_paths = {}
    for path in candidate_paths:
        current = preferred_paths.get(path.stem)
        if current is None or (current.suffix == ".csv" and path.suffix == ".parquet"):
            preferred_paths[path.stem] = path
    return sorted(preferred_paths.values())


def read_tabular_file(path, **kwargs):
    if path.suffix == ".parquet":
        kwargs.pop("low_memory", None)
        kwargs.pop("usecols", None)
        return pd.read_parquet(path, **kwargs)
    kwargs.pop("columns", None)
    return pd.read_csv(path, **kwargs)


sat_data_paths = collect_versioned_data_paths(base, SAT_DATA_PATTERN)
if not sat_data_paths:
    st.error(f"No data file matching {SAT_DATA_PATTERN}.csv or {SAT_DATA_PATTERN}.parquet found in {base}")
    st.stop()

supplemental_paths = []
for file_name in SUPPLEMENTAL_DATA_FILES:
    parquet_path = base / f"{Path(file_name).stem}.parquet"
    csv_path = base / file_name
    if parquet_path.exists():
        supplemental_paths.append(parquet_path)
    elif csv_path.exists():
        supplemental_paths.append(csv_path)

sat_data_paths = sorted(sat_data_paths) + supplemental_paths
demographics_data_paths = collect_versioned_data_paths(base, DEMOGRAPHICS_DATA_PATTERN)
discipline_data_paths = collect_versioned_data_paths(base, DISCIPLINE_DATA_PATTERN)
mcas_data_paths = collect_versioned_data_paths(base, MCAS_DATA_PATTERN)


def parse_numeric(series, *, percent=False):
    cleaned = (
        series.astype(str)
        .str.replace(",", "", regex=False)
        .str.strip()
        .replace({"nan": None, "": None})
    )
    if percent:
        cleaned = cleaned.str.replace("%", "", regex=False)
    return pd.to_numeric(cleaned, errors="coerce")


def build_preferred_name_map(df, *, code_col, name_col):
    name_df = df[[code_col, name_col, "SY"]].copy()
    name_df[code_col] = name_df[code_col].astype(str).str.strip()
    name_df[name_col] = name_df[name_col].astype(str).str.strip()
    name_df = name_df[(name_df[code_col] != "") & name_df[name_col].notna() & (name_df[name_col] != "")]
    if name_df.empty:
        return {}

    name_df["has_lowercase"] = name_df[name_col].str.contains(r"[a-z]", regex=True)
    name_df["name_length"] = name_df[name_col].str.len()
    preferred = (
        name_df.sort_values(
            [code_col, "has_lowercase", "SY", "name_length", name_col],
            ascending=[True, False, False, False, True],
        )
        .drop_duplicates(subset=[code_col])
        [[code_col, name_col]]
    )
    return dict(zip(preferred[code_col], preferred[name_col]))


def add_org_identity_columns(df):
    df = df.copy()
    for col in ["ORG_CODE", "DIST_CODE"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
    for col in ["ORG_NAME", "DIST_NAME"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    org_name_map = build_preferred_name_map(df, code_col="ORG_CODE", name_col="ORG_NAME")
    dist_name_map = build_preferred_name_map(df, code_col="DIST_CODE", name_col="DIST_NAME")

    df["ORG_DISPLAY"] = df["ORG_CODE"].map(org_name_map).fillna(df["ORG_NAME"])
    df["DIST_DISPLAY"] = df["DIST_CODE"].map(dist_name_map).fillna(df["DIST_NAME"])
    df["ORG_KEY"] = df["ORG_TYPE"].astype(str) + "::" + df["ORG_CODE"]
    df["ORG_FULL"] = df["ORG_DISPLAY"]
    return df


def cycle_colors(count):
    if count <= 0:
        return []
    repeats = (count + len(HIGHLIGHT_COLORS) - 1) // len(HIGHLIGHT_COLORS)
    return (HIGHLIGHT_COLORS * repeats)[:count]


def sort_with_preferred_order(values, preferred_order):
    order_map = {value: idx for idx, value in enumerate(preferred_order)}
    return sorted(values, key=lambda value: (order_map.get(value, len(order_map)), str(value).lower()))


def format_mcas_subject(subject_code):
    return MCAS_SUBJECT_LABELS.get(subject_code, subject_code)


def format_mcas_grade(test_grade):
    return f"Grade {test_grade}" if str(test_grade).isdigit() else str(test_grade)


def normalize_mcas_org_type(series):
    mapping = {
        "Public School District": "District",
        "Charter District": "District",
        "Public School": "School",
        "Charter School": "School",
    }
    return series.astype(str).str.strip().map(mapping).fillna(series.astype(str).str.strip())


@st.cache_data
def load_sat_data(paths):
    frames = []
    for path in paths:
        frame = read_tabular_file(path, columns=SAT_REQUIRED_COLUMNS, usecols=SAT_REQUIRED_COLUMNS)
        frame.columns = [c.strip() for c in frame.columns]
        frames.append(frame)

    df = pd.concat(frames, ignore_index=True)
    df = df[df["ORG_TYPE"].isin(["District", "School"])].copy()
    df = add_org_identity_columns(df)

    for col in ["TAKEN_CNT", "READ_SCORE", "WRITE_SCORE", "READ_WRITE_SCORE", "MATH_SCORE"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(",", "", regex=False).replace({"nan": None})
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["SY"] = pd.to_numeric(df["SY"], errors="coerce").astype("Int64")
    df["READING"] = df["READ_SCORE"].where(df["SY"] < 2017, df["READ_WRITE_SCORE"])
    all_students_taken = (
        df[df["STU_GRP"] == "All Students"][["SY", "ORG_TYPE", "ORG_CODE", "TAKEN_CNT"]]
        .rename(columns={"TAKEN_CNT": "ALL_STUDENTS_TAKEN_CNT"})
    )
    df = df.merge(
        all_students_taken,
        on=["SY", "ORG_TYPE", "ORG_CODE"],
        how="left",
    )
    df["TAKEN_PCT_OF_ALL"] = (
        df["TAKEN_CNT"]
        .div(df["ALL_STUDENTS_TAKEN_CNT"].where(df["ALL_STUDENTS_TAKEN_CNT"] > 0))
        .mul(100)
    )
    return df


@st.cache_data
def load_demographics_data(paths):
    if not paths:
        return pd.DataFrame()

    frames = []
    for path in paths:
        frame = read_tabular_file(
            path,
            low_memory=False,
            columns=DEMOGRAPHICS_REQUIRED_COLUMNS,
            usecols=DEMOGRAPHICS_REQUIRED_COLUMNS,
        )
        frame.columns = [c.strip() for c in frame.columns]
        frames.append(frame)

    df = pd.concat(frames, ignore_index=True)
    df = df[df["ORG_TYPE"].isin(["District", "School"])].copy()
    df = add_org_identity_columns(df)

    count_columns = ["TOTAL_CNT"] + sorted({count_col for count_col, _ in DISADVANTAGED_COLUMNS.values()})
    pct_columns = sorted(set(RACE_PCT_COLUMNS.values()) | {pct_col for _, pct_col in DISADVANTAGED_COLUMNS.values()})

    for col in count_columns:
        if col in df.columns:
            df[col] = parse_numeric(df[col])
    for col in pct_columns:
        if col in df.columns:
            df[col] = parse_numeric(df[col], percent=True)
            df[col] = parse_numeric(df[col], percent=True)
    df["SY"] = pd.to_numeric(df["SY"], errors="coerce").astype("Int64")
    df["SY"] = pd.to_numeric(df["SY"], errors="coerce").astype("Int64")
    return df


@st.cache_data
def load_discipline_data(paths):
    if not paths:
        return pd.DataFrame()

    frames = []
    for path in paths:
        frame = read_tabular_file(
            path,
            low_memory=False,
            columns=DISCIPLINE_REQUIRED_COLUMNS,
            usecols=DISCIPLINE_REQUIRED_COLUMNS,
        )
        frame.columns = [c.strip() for c in frame.columns]
        frames.append(frame)

    df = pd.concat(frames, ignore_index=True)
    df = df[df["ORG_TYPE"].isin(["District", "School"])].copy()
    df = add_org_identity_columns(df)

    for col in ["STU_CNT", "STU_DISCIPL_CNT"]:
        if col in df.columns:
            df[col] = parse_numeric(df[col])
    for col in [
        "IN_SUSP_PCT",
        "OUT_SUSP_PCT",
        "EXP_PCT",
        "ALT_SETTING_PCT",
        "EMERG_RMVL_PCT",
        "ARREST_PCT",
        "LAWENF_REF_PCT",
    ]:
        if col in df.columns:
            df[col] = parse_numeric(df[col], percent=True)

    df["SY"] = pd.to_numeric(df["SY"], errors="coerce").astype("Int64")
    df["OFFENSE"] = df["OFFENSE"].astype(str).str.strip()
    df["STU_GRP"] = df["STU_GRP"].astype(str).str.strip()
    return df


@st.cache_data
def load_mcas_data(paths):
    if not paths:
        return pd.DataFrame()

    frames = []
    for path in paths:
        frame = read_tabular_file(
            path,
            low_memory=False,
            columns=MCAS_REQUIRED_COLUMNS,
            usecols=MCAS_REQUIRED_COLUMNS,
        )
        frame.columns = [c.strip() for c in frame.columns]
        frames.append(frame)

    df = pd.concat(frames, ignore_index=True)
    df["ORG_TYPE"] = normalize_mcas_org_type(df["ORG_TYPE"])
    df = df[df["ORG_TYPE"].isin(["District", "School"])].copy()
    df = add_org_identity_columns(df)

    for col in ["AVG_SCALED_SCORE", "STU_PART_PCT", "STU_CNT"]:
        if col in df.columns:
            df[col] = parse_numeric(df[col], percent=(col == "STU_PART_PCT"))

    df["SY"] = pd.to_numeric(df["SY"], errors="coerce").astype("Int64")
    df["SUBJECT_CODE"] = df["SUBJECT_CODE"].astype(str).str.strip()
    df["TEST_GRADE"] = df["TEST_GRADE"].astype(str).str.strip()
    df["STU_GRP"] = df["STU_GRP"].astype(str).str.replace("\xa0", " ", regex=False).str.strip()
    return df


def build_labeled_line_chart(
    data,
    metric,
    y_title,
    chart_title,
    group_field,
    group_title,
    group_order,
    color_range,
    subtitle=None,
    tooltip_format=".0f",
):
    metric_df = data[data[metric].notna()].copy()
    if metric_df.empty:
        return None

    metric_df["SY_LABEL"] = metric_df["SY"].astype(str)

    color = alt.Color(
        f"{group_field}:N",
        title=group_title,
        scale=alt.Scale(domain=group_order, range=color_range),
    )
    title = (
        alt.TitleParams(
            text=chart_title,
            subtitle=subtitle,
            subtitleFontSize=11,
            subtitleColor="#888888",
            anchor="middle",
        )
        if subtitle
        else chart_title
    )

    line = alt.Chart(metric_df).mark_line(strokeWidth=3).encode(
        x=alt.X("SY:O", title="Year", sort="ascending"),
        y=alt.Y(f"{metric}:Q", title=y_title),
        color=color,
        detail=f"{group_field}:N",
        tooltip=[
            alt.Tooltip(f"{group_field}:N", title=group_title),
            alt.Tooltip("SY:O", title="Year"),
            alt.Tooltip(f"{metric}:Q", title=y_title, format=tooltip_format),
        ],
    )

    last_points = (
        metric_df.sort_values(["SY", group_field])
        .groupby(group_field, as_index=False)
        .tail(1)
    )
    labels = alt.Chart(last_points).mark_text(
        align="left",
        dx=6,
        fontSize=11,
        fontWeight="bold",
    ).encode(
        x=alt.X("SY:O"),
        y=alt.Y(f"{metric}:Q"),
        color=color,
        text=alt.Text(f"{group_field}:N"),
    )

    return alt.layer(line, labels).properties(title=title, height=320)


def build_aligned_chart_stack(charts):
    valid_charts = [chart for chart in charts if chart is not None]
    if not valid_charts:
        return None
    return alt.vconcat(*valid_charts, spacing=18).resolve_scale(x="shared")


def build_org_selector_options(data, *, view_type):
    option_df = (
        data[data["ORG_TYPE"] == view_type][["ORG_KEY", "ORG_DISPLAY", "DIST_DISPLAY", "ORG_CODE"]]
        .drop_duplicates()
        .copy()
    )
    option_df["ORG_SELECTOR_LABEL"] = option_df["ORG_DISPLAY"]

    duplicate_display = option_df["ORG_DISPLAY"].duplicated(keep=False)
    if view_type == "School":
        option_df.loc[duplicate_display, "ORG_SELECTOR_LABEL"] = (
            option_df.loc[duplicate_display, "ORG_DISPLAY"]
            + " ("
            + option_df.loc[duplicate_display, "DIST_DISPLAY"]
            + ")"
        )

    duplicate_labels = option_df["ORG_SELECTOR_LABEL"].duplicated(keep=False)
    option_df.loc[duplicate_labels, "ORG_SELECTOR_LABEL"] = (
        option_df.loc[duplicate_labels, "ORG_SELECTOR_LABEL"]
        + " ["
        + option_df.loc[duplicate_labels, "ORG_CODE"]
        + "]"
    )

    return option_df.sort_values("ORG_SELECTOR_LABEL", key=lambda series: series.str.lower()).reset_index(drop=True)


def render_org_comparison_selector(data, *, prefix, view_type, search):
    ids_key = f"{prefix}_org_ids"
    next_key = f"{prefix}_next_id"

    if ids_key not in st.session_state:
        st.session_state[ids_key] = [0]
        st.session_state[next_key] = 1

    def add_org():
        st.session_state[ids_key].append(st.session_state[next_key])
        st.session_state[next_key] += 1

    def remove_org(org_id):
        st.session_state[ids_key].remove(org_id)

    st.markdown("**Compare schools / districts**")
    option_df = build_org_selector_options(data, view_type=view_type)
    full_label_map = dict(zip(option_df["ORG_KEY"], option_df["ORG_SELECTOR_LABEL"]))
    reverse_label_map = {}
    for org_key, label in full_label_map.items():
        reverse_label_map.setdefault(label, []).append(org_key)

    filtered_option_df = option_df
    if search:
        search_text = search.lower()
        filtered_option_df = option_df[
            option_df["ORG_SELECTOR_LABEL"].str.lower().str.contains(search_text)
            | option_df["ORG_DISPLAY"].str.lower().str.contains(search_text)
            | option_df["DIST_DISPLAY"].str.lower().str.contains(search_text)
        ]
    options = ["(None)"] + filtered_option_df["ORG_KEY"].tolist()

    for i, org_id in enumerate(st.session_state[ids_key]):
        color = HIGHLIGHT_COLORS[i % len(HIGHLIGHT_COLORS)]
        swatch_col, sel_col, btn_col = st.columns([0.35, 5, 1])
        with swatch_col:
            st.markdown(
                f'<div style="width:14px;height:14px;background:{color};'
                f'border-radius:3px;margin-top:10px"></div>',
                unsafe_allow_html=True,
            )
        with sel_col:
            current_value = st.session_state.get(f"{prefix}_org_{org_id}", "(None)")
            if current_value not in options and isinstance(current_value, str):
                legacy_matches = reverse_label_map.get(current_value, [])
                if len(legacy_matches) == 1:
                    current_value = legacy_matches[0]
                    st.session_state[f"{prefix}_org_{org_id}"] = current_value
            select_options = options
            if current_value not in select_options:
                select_options = ["(None)", current_value] + [option for option in options if option != current_value]
            st.selectbox(
                f"Organization {i + 1}",
                options=select_options,
                key=f"{prefix}_org_{org_id}",
                format_func=lambda option_key: "(None)" if option_key == "(None)" else full_label_map.get(option_key, option_key),
                label_visibility="collapsed",
            )
        with btn_col:
            if len(st.session_state[ids_key]) > 1:
                st.button("−", key=f"{prefix}_remove_{org_id}", on_click=remove_org, args=(org_id,))

    st.button("＋ Add organization", key=f"{prefix}_add", on_click=add_org)

    selected_orgs = [
        st.session_state.get(f"{prefix}_org_{org_id}", "(None)")
        for org_id in st.session_state[ids_key]
    ]
    selected_orgs = list(dict.fromkeys(org for org in selected_orgs if org != "(None)"))
    return selected_orgs, full_label_map


def render_school_sequence_selector(data, *, prefix, search):
    ids_key = f"{prefix}_sequence_ids"
    next_key = f"{prefix}_next_id"
    stage_configs = [
        ("elementary", "Elementary school"),
        ("middle", "Middle school"),
        ("high", "High school"),
    ]

    if ids_key not in st.session_state:
        st.session_state[ids_key] = [0]
        st.session_state[next_key] = 1

    def add_sequence():
        st.session_state[ids_key].append(st.session_state[next_key])
        st.session_state[next_key] += 1

    def remove_sequence(sequence_id):
        st.session_state[ids_key].remove(sequence_id)

    option_df = build_org_selector_options(data, view_type="School")
    full_label_map = dict(zip(option_df["ORG_KEY"], option_df["ORG_SELECTOR_LABEL"]))
    reverse_label_map = {}
    for org_key, label in full_label_map.items():
        reverse_label_map.setdefault(label, []).append(org_key)

    filtered_option_df = option_df
    if search:
        search_text = search.lower()
        filtered_option_df = option_df[
            option_df["ORG_SELECTOR_LABEL"].str.lower().str.contains(search_text)
            | option_df["ORG_DISPLAY"].str.lower().str.contains(search_text)
            | option_df["DIST_DISPLAY"].str.lower().str.contains(search_text)
        ]
    options = ["(None)"] + filtered_option_df["ORG_KEY"].tolist()

    st.markdown("**Compare school sequences**")
    header_cols = st.columns([3, 3, 3, 0.8])
    for header_col, (_, stage_label) in zip(header_cols[:3], stage_configs):
        with header_col:
            st.markdown(f"**{stage_label}**")

    sequences = []
    for sequence_id in st.session_state[ids_key]:
        row_cols = st.columns([3, 3, 3, 0.8])
        stage_values = []
        stage_label_map = {}

        for col, (stage_key, stage_label) in zip(row_cols[:3], stage_configs):
            state_key = f"{prefix}_{stage_key}_{sequence_id}"
            current_value = st.session_state.get(state_key, "(None)")
            if current_value not in options and isinstance(current_value, str):
                legacy_matches = reverse_label_map.get(current_value, [])
                if len(legacy_matches) == 1:
                    current_value = legacy_matches[0]
                    st.session_state[state_key] = current_value
            select_options = options
            if current_value not in select_options:
                select_options = ["(None)", current_value] + [option for option in options if option != current_value]
            with col:
                selected_value = st.selectbox(
                    stage_label,
                    options=select_options,
                    key=state_key,
                    format_func=lambda option_key: "(None)" if option_key == "(None)" else full_label_map.get(option_key, option_key),
                    label_visibility="collapsed",
                )
            if selected_value != "(None)":
                stage_values.append(selected_value)
                stage_label_map[selected_value] = stage_label

        with row_cols[3]:
            if len(st.session_state[ids_key]) > 1:
                st.button("−", key=f"{prefix}_remove_{sequence_id}", on_click=remove_sequence, args=(sequence_id,))

        unique_stage_values = list(dict.fromkeys(stage_values))
        if unique_stage_values:
            sequence_label = " \u2192 ".join(full_label_map.get(org_key, org_key) for org_key in unique_stage_values)
            sequences.append(
                {
                    "sequence_id": sequence_id,
                    "school_keys": unique_stage_values,
                    "sequence_label": sequence_label,
                    "stage_label_map": stage_label_map,
                }
            )

    st.button("＋ Add sequence", key=f"{prefix}_add", on_click=add_sequence)
    return sequences, full_label_map


def render_sat_scores_tab(data):
    col1, col2 = st.columns([2, 3])
    with col1:
        view_type = st.radio("View by", ["District", "School"], key="sat_view_type")
        metrics = []
        st.markdown("**Metrics**")
        if st.checkbox("Reading", value=True):
            metrics.append("READING")
        if st.checkbox("Writing", value=False):
            metrics.append("WRITE_SCORE")
        if st.checkbox("Math", value=True):
            metrics.append("MATH_SCORE")
        st.markdown("---")
        show_background = st.checkbox("Show all organizations in background", value=True)
        search = st.text_input("Search school/district (type to filter)", key="sat_search")

    with col2:
        selected_schools, sat_label_map = render_org_comparison_selector(
            data,
            prefix="sat",
            view_type=view_type,
            search=search,
        )

    plot_df = data[data["ORG_TYPE"] == view_type].copy()
    plot_df["ORG_SELECTOR_LABEL"] = plot_df["ORG_KEY"].map(sat_label_map).fillna(plot_df["ORG_DISPLAY"])
    if not metrics:
        st.warning("Pick at least one metric to display.")
        return

    for metric in metrics:
        short_label = {
            "READING": "Reading",
            "WRITE_SCORE": "Writing",
            "MATH_SCORE": "Math",
        }.get(metric, metric)

        subtitle = (
            "SAT Critical Reading through 2016; Evidence-Based Reading & Writing from 2017"
            if metric == "READING"
            else None
        )
        chart_title = (
            alt.TitleParams(
                text=short_label,
                subtitle=subtitle,
                subtitleFontSize=11,
                subtitleColor="#888888",
                anchor="middle",
            )
            if subtitle
            else short_label
        )

        layers = []
        bg_df = plot_df[["SY", "ORG_KEY", "ORG_SELECTOR_LABEL", metric]].copy()

        if show_background:
            layers.append(
                alt.Chart(bg_df).mark_line(color="#888888", opacity=0.15).encode(
                    x=alt.X("SY:O", title="Year"),
                    y=alt.Y(f"{metric}:Q", title=short_label),
                    detail="ORG_KEY:N",
                    tooltip=["ORG_SELECTOR_LABEL", "SY", metric],
                )
            )

        for i, school_key in enumerate(selected_schools):
            color = HIGHLIGHT_COLORS[i % len(HIGHLIGHT_COLORS)]
            school_df = plot_df[plot_df["ORG_KEY"] == school_key]
            if school_df.empty:
                continue

            layers.append(
                alt.Chart(school_df).mark_line(color=color, strokeWidth=3).encode(
                    x=alt.X("SY:O", title="Year"),
                    y=alt.Y(f"{metric}:Q", title=short_label),
                    tooltip=["ORG_SELECTOR_LABEL", "SY", metric],
                )
            )

            valid_df = school_df[school_df[metric].notna()]
            if not valid_df.empty:
                last_df = valid_df.loc[[valid_df["SY"].idxmax()]]
                layers.append(
                    alt.Chart(last_df).mark_text(
                        align="left",
                        dx=6,
                        fontSize=11,
                        color=color,
                        fontWeight="bold",
                    ).encode(
                        x=alt.X("SY:O"),
                        y=alt.Y(f"{metric}:Q"),
                        text="ORG_SELECTOR_LABEL:N",
                    )
                )

        if not layers:
            st.info(f"No data to display for **{short_label}**. Select a school or enable background.")
            continue

        y_range = plot_df[metric].agg(["min", "max"])
        axis_df = pd.DataFrame({metric: [y_range["min"], y_range["max"]]})
        left_axis = alt.Chart(axis_df).mark_point(opacity=0, size=0).encode(
            y=alt.Y(f"{metric}:Q", axis=alt.Axis(orient="left", title=short_label))
        )
        right_axis = alt.Chart(axis_df).mark_point(opacity=0, size=0).encode(
            y=alt.Y(f"{metric}:Q", axis=alt.Axis(orient="right", title=None))
        )

        st.altair_chart(
            alt.layer(left_axis, *layers, right_axis).properties(title=chart_title, height=350),
            use_container_width=True,
        )


def build_demographics_long_df(data, *, view_type, selected_orgs, group_config, show_percent):
    plot_df = data[
        (data["ORG_TYPE"] == view_type)
        & (data["ORG_KEY"].isin(selected_orgs))
        & data["SY"].notna()
    ].copy()
    if plot_df.empty:
        return pd.DataFrame()

    frames = []
    for group_label, column_config in group_config.items():
        frame = plot_df[["SY", "ORG_KEY", "ORG_SELECTOR_LABEL", "TOTAL_CNT"]].copy()
        frame["GROUP"] = group_label

        if isinstance(column_config, tuple):
            count_col, pct_col = column_config
        else:
            count_col, pct_col = None, column_config

        pct_values = plot_df[pct_col] if pct_col in plot_df.columns else pd.Series(index=plot_df.index, dtype="float64")
        estimated_counts = plot_df["TOTAL_CNT"].mul(pct_values).div(100)

        if show_percent:
            frame["VALUE"] = pct_values
        elif count_col and count_col in plot_df.columns:
            frame["VALUE"] = plot_df[count_col].fillna(estimated_counts)
        else:
            frame["VALUE"] = estimated_counts

        frames.append(frame)

    result = pd.concat(frames, ignore_index=True)
    return result[result["VALUE"].notna()]


def build_faceted_demographics_chart(
    data,
    *,
    chart_title,
    y_title,
    groups,
    colors,
    org_order,
    tooltip_title,
    tooltip_format,
    independent_y=False,
):
    if data.empty:
        return None

    base = alt.Chart(data)
    color = alt.Color(
        "GROUP:N",
        title="Group",
        scale=alt.Scale(domain=groups, range=colors[: len(groups)]),
    )
    line = base.mark_line(strokeWidth=3).encode(
        x=alt.X("SY:O", title="Year", sort="ascending"),
        y=alt.Y("VALUE:Q", title=y_title),
        color=color,
        detail=["ORG_KEY:N", "GROUP:N"],
        tooltip=[
            alt.Tooltip("ORG_SELECTOR_LABEL:N", title=tooltip_title),
            alt.Tooltip("GROUP:N", title="Group"),
            alt.Tooltip("SY:O", title="Year"),
            alt.Tooltip("VALUE:Q", title=y_title, format=tooltip_format),
        ],
    )
    labels = (
        base.transform_window(
            group_rank="rank()",
            sort=[alt.SortField("SY", order="descending")],
            groupby=["ORG_KEY", "GROUP"],
        )
        .transform_filter(alt.datum.group_rank == 1)
        .mark_text(
            align="left",
            dx=6,
            fontSize=11,
            fontWeight="bold",
        )
        .encode(
            x=alt.X("SY:O"),
            y=alt.Y("VALUE:Q"),
            color=color,
            text="GROUP:N",
        )
    )

    chart = (
        alt.layer(line, labels, data=data)
        .properties(title=chart_title, height=220)
        .facet(
            row=alt.Row(
                "ORG_SELECTOR_LABEL:N",
                title=None,
                sort=org_order,
                header=alt.Header(labelFontWeight="bold", labelFontSize=12),
            )
        )
    )
    if independent_y:
        chart = chart.resolve_scale(y="independent")
    return chart


def build_faceted_discipline_chart(data, *, chart_title, y_title, group_order):
    if data.empty:
        return None

    base = alt.Chart(data)
    color = alt.Color(
        "SERIES_LABEL:N",
        title="Organization / Offense",
        scale=alt.Scale(scheme="tableau20"),
        legend=alt.Legend(orient="bottom", columns=2),
    )
    line = base.mark_line(strokeWidth=3).encode(
        x=alt.X("SY:O", title="Year", sort="ascending"),
        y=alt.Y("STU_DISCIPL_CNT:Q", title=y_title),
        color=color,
        detail=["ORG_KEY:N", "OFFENSE:N", "STU_GRP:N"],
        tooltip=[
            alt.Tooltip("ORG_SELECTOR_LABEL:N", title="Organization"),
            alt.Tooltip("STU_GRP:N", title="Student Group"),
            alt.Tooltip("OFFENSE:N", title="Offense"),
            alt.Tooltip("SY:O", title="Year"),
            alt.Tooltip("STU_DISCIPL_CNT:Q", title=y_title, format=".0f"),
        ],
    )
    labels = (
        base.transform_window(
            series_rank="rank()",
            sort=[alt.SortField("SY", order="descending")],
            groupby=["ORG_KEY", "OFFENSE", "STU_GRP"],
        )
        .transform_filter(alt.datum.series_rank == 1)
        .mark_text(
            align="right",
            dx=-6,
            fontSize=11,
            fontWeight="bold",
        )
        .encode(
            x=alt.X("SY:O"),
            y=alt.Y("STU_DISCIPL_CNT:Q"),
            color=color,
            text="SERIES_LABEL:N",
        )
    )

    return (
        alt.layer(line, labels, data=data)
        .properties(
            title=chart_title,
            height=220,
            width="container",
        )
        .facet(
            row=alt.Row(
                "STU_GRP:N",
                title=None,
                sort=group_order,
                header=alt.Header(labelFontWeight="bold", labelFontSize=12),
            )
        )
        .configure_facet(spacing=12)
    )


def render_demographics_over_time_tab(data):
    if data.empty:
        st.warning("No demographics enrollment file is available yet.")
        return

    col1, col2 = st.columns([2, 3])
    with col1:
        view_type = st.radio("View by", ["District", "School"], key="demographics_view_type")
        search = st.text_input(
            "Search school/district (type to filter)",
            key="demographics_search",
        )
    with col2:
        selected_orgs, demographics_label_map = render_org_comparison_selector(
            data,
            prefix="demographics",
            view_type=view_type,
            search=search,
        )

    if not selected_orgs:
        st.info("Select at least one school or district to display.")
        return

    view_data = data[data["ORG_TYPE"] == view_type].copy()
    view_data["ORG_SELECTOR_LABEL"] = view_data["ORG_KEY"].map(demographics_label_map).fillna(view_data["ORG_DISPLAY"])
    selected_labels = [demographics_label_map.get(org_key, org_key) for org_key in selected_orgs]

    race_show_percent = st.toggle(
        "Show racial / ethnic enrollment as percentages",
        value=True,
        key="demographics_race_percent",
    )
    race_df = build_demographics_long_df(
        view_data,
        view_type=view_type,
        selected_orgs=selected_orgs,
        group_config=RACE_PCT_COLUMNS,
        show_percent=race_show_percent,
    )
    race_chart = build_faceted_demographics_chart(
        race_df,
        chart_title="Racial / Ethnic Enrollment Over Time",
        y_title="Percent of Enrollment" if race_show_percent else "Students",
        groups=RACE_GROUPS,
        colors=RACE_COLORS,
        org_order=selected_labels,
        tooltip_title=view_type,
        tooltip_format=".1f" if race_show_percent else ".0f",
        independent_y=not race_show_percent and len(selected_orgs) > 1,
    )
    if race_chart is None:
        st.info("No racial / ethnic enrollment data is available for that selection.")
    else:
        st.altair_chart(race_chart, use_container_width=True)
        if not race_show_percent:
            st.caption("Race / ethnicity counts are estimated from each year’s total enrollment and reported percentages.")

    disadvantaged_show_percent = st.toggle(
        "Show disadvantaged categories as percentages",
        value=True,
        key="demographics_disadvantaged_percent",
    )
    disadvantaged_df = build_demographics_long_df(
        view_data,
        view_type=view_type,
        selected_orgs=selected_orgs,
        group_config=DISADVANTAGED_COLUMNS,
        show_percent=disadvantaged_show_percent,
    )
    disadvantaged_chart = build_faceted_demographics_chart(
        disadvantaged_df,
        chart_title="Disadvantaged Categories Over Time",
        y_title="Percent of Enrollment" if disadvantaged_show_percent else "Students",
        groups=DISADVANTAGED_GROUPS,
        colors=DISADVANTAGED_COLORS,
        org_order=selected_labels,
        tooltip_title=view_type,
        tooltip_format=".1f" if disadvantaged_show_percent else ".0f",
        independent_y=not disadvantaged_show_percent and len(selected_orgs) > 1,
    )
    if disadvantaged_chart is None:
        st.info("No disadvantaged category data is available for that selection.")
    else:
        st.altair_chart(disadvantaged_chart, use_container_width=True)
        if not disadvantaged_show_percent:
            st.caption(
                "Disadvantaged category counts use reported counts when available and estimate missing counts from each year’s total enrollment and reported percentages."
            )


def render_discipline_tab(data):
    if data.empty:
        st.warning("No discipline file is available yet.")
        return

    col1, col2 = st.columns([2, 3])
    with col1:
        view_type = st.radio("View by", ["District", "School"], key="discipline_view_type")
        search = st.text_input(
            "Search school/district (type to filter)",
            key="discipline_org_search",
        )
    with col2:
        selected_orgs, discipline_label_map = render_org_comparison_selector(
            data,
            prefix="discipline",
            view_type=view_type,
            search=search,
        )

    if not selected_orgs:
        st.info("Select at least one school or district to display.")
        return

    view_data = data[data["ORG_TYPE"] == view_type].copy()
    view_data["ORG_SELECTOR_LABEL"] = view_data["ORG_KEY"].map(discipline_label_map).fillna(view_data["ORG_DISPLAY"])
    filter_col1, filter_col2 = st.columns(2)
    with filter_col1:
        offense_options = sorted(view_data["OFFENSE"].dropna().unique().tolist(), key=str.lower)
        selected_offenses = st.multiselect(
            "Offenses",
            options=offense_options,
            default=["All Offenses"] if "All Offenses" in offense_options else offense_options[:1],
            key="discipline_offenses",
            help="Type to search and add offenses to the plot.",
        )
    with filter_col2:
        group_options = sorted(view_data["STU_GRP"].dropna().unique().tolist(), key=str.lower)
        selected_groups = st.multiselect(
            "Student groups",
            options=group_options,
            default=["All Students"] if "All Students" in group_options else group_options[:1],
            key="discipline_student_groups",
            help="Type to search and add student groups to the plot.",
        )

    if not selected_offenses:
        st.warning("Pick at least one offense to display.")
        return
    if not selected_groups:
        st.warning("Pick at least one student group to display.")
        return

    chart_df = view_data[
        view_data["ORG_KEY"].isin(selected_orgs)
        & view_data["OFFENSE"].isin(selected_offenses)
        & view_data["STU_GRP"].isin(selected_groups)
        & view_data["SY"].notna()
        & view_data["STU_DISCIPL_CNT"].notna()
    ].copy()
    if chart_df.empty:
        st.info("No discipline data is available for that organization / offense / student-group selection.")
        return

    selected_group_order = [group for group in group_options if group in selected_groups]
    selected_offense_order = [offense for offense in offense_options if offense in selected_offenses]
    selected_label_order = [discipline_label_map.get(org_key, org_key) for org_key in selected_orgs]
    chart_df["SERIES_LABEL"] = pd.Categorical(
        chart_df["ORG_SELECTOR_LABEL"] + " - " + chart_df["OFFENSE"],
        categories=[
            f"{org_label} - {offense}"
            for org_label in selected_label_order
            for offense in selected_offense_order
        ],
        ordered=True,
    )

    chart = build_faceted_discipline_chart(
        chart_df,
        chart_title="Disciplined Students Over Time",
        y_title="Disciplined Students",
        group_order=selected_group_order,
    )
    if chart is None:
        st.info("No discipline data is available for that selection.")
        return

    st.altair_chart(chart, use_container_width=True)
    st.caption("Each line shows `STU_DISCIPL_CNT` for a selected student-group and offense combination.")


def render_mcas_scores_tab(data):
    if data.empty:
        st.warning("No MCAS file is available yet.")
        return

    col1, col2 = st.columns([2, 3])
    with col1:
        view_type = st.radio("View by", ["District", "School"], key="mcas_view_type")
        search = st.text_input(
            "Search school/district (type to filter)",
            key="mcas_search",
        )

    with col2:
        selected_orgs, mcas_label_map = render_org_comparison_selector(
            data,
            prefix="mcas",
            view_type=view_type,
            search=search,
        )

    if not selected_orgs:
        st.info("Select at least one school or district to display.")
        return

    view_data = data[(data["ORG_TYPE"] == view_type) & (data["STU_GRP"] == "All Students")].copy()
    if view_data.empty:
        st.info("No all-students MCAS data is available for that view.")
        return

    filter_col1, filter_col2 = st.columns(2)
    with filter_col1:
        subject_options = sort_with_preferred_order(
            view_data["SUBJECT_CODE"].dropna().unique().tolist(),
            MCAS_SUBJECT_ORDER,
        )
        if st.session_state.get("mcas_subject") not in subject_options:
            st.session_state["mcas_subject"] = "ELA" if "ELA" in subject_options else subject_options[0]
        selected_subject = st.selectbox(
            "Subject",
            options=subject_options,
            key="mcas_subject",
            format_func=format_mcas_subject,
        )
    with filter_col2:
        grade_options = sort_with_preferred_order(
            view_data[view_data["SUBJECT_CODE"] == selected_subject]["TEST_GRADE"].dropna().unique().tolist(),
            MCAS_GRADE_ORDER,
        )
        if st.session_state.get("mcas_grade") not in grade_options:
            st.session_state["mcas_grade"] = grade_options[0]
        selected_grade = st.selectbox(
            "Test grade",
            options=grade_options,
            key="mcas_grade",
            format_func=format_mcas_grade,
        )

    chart_df = view_data[
        view_data["ORG_KEY"].isin(selected_orgs)
        & (view_data["SUBJECT_CODE"] == selected_subject)
        & (view_data["TEST_GRADE"] == selected_grade)
        & view_data["SY"].notna()
    ].copy()
    if chart_df.empty:
        st.info("No MCAS data is available for that organization / subject / grade selection.")
        return

    chart_df["ORG_SELECTOR_LABEL"] = chart_df["ORG_KEY"].map(mcas_label_map).fillna(chart_df["ORG_DISPLAY"])
    selected_labels = [mcas_label_map.get(org_key, org_key) for org_key in selected_orgs]
    color_range = cycle_colors(len(selected_labels))
    grade_label = format_mcas_grade(selected_grade)
    subject_label = format_mcas_subject(selected_subject)

    score_chart = build_labeled_line_chart(
        data=chart_df,
        metric="AVG_SCALED_SCORE",
        y_title="Average Scaled Score",
        chart_title=f"{subject_label} Average Scaled Score — {grade_label}",
        group_field="ORG_SELECTOR_LABEL",
        group_title=view_type,
        group_order=selected_labels,
        color_range=color_range,
        tooltip_format=".1f",
    )
    participation_chart = build_labeled_line_chart(
        data=chart_df,
        metric="STU_PART_PCT",
        y_title="Student Participation (%)",
        chart_title=f"{subject_label} Student Participation — {grade_label}",
        group_field="ORG_SELECTOR_LABEL",
        group_title=view_type,
        group_order=selected_labels,
        color_range=color_range,
        tooltip_format=".1f",
    )

    combined_chart = build_aligned_chart_stack([score_chart, participation_chart])
    if combined_chart is None:
        st.info("No MCAS score or participation data is available for that selection.")
        return

    st.altair_chart(combined_chart, use_container_width=True)
    st.caption("This subtab uses only `STU_GRP == 'All Students'` MCAS rows for the selected subject and test grade.")


def render_mcas_demographic_tab(data):
    if data.empty:
        st.warning("No MCAS file is available yet.")
        return

    col1, col2 = st.columns([2, 3])
    with col1:
        view_type = st.radio("View by", ["District", "School"], key="mcas_demo_view_type")
        search = st.text_input(
            "Search school/district (type to filter)",
            key="mcas_demo_search",
        )
    with col2:
        option_df = build_org_selector_options(data, view_type=view_type)
        if search:
            search_text = search.lower()
            option_df = option_df[
                option_df["ORG_SELECTOR_LABEL"].str.lower().str.contains(search_text)
                | option_df["ORG_DISPLAY"].str.lower().str.contains(search_text)
                | option_df["DIST_DISPLAY"].str.lower().str.contains(search_text)
            ]
        if option_df.empty:
            st.info("No organizations match that search.")
            return
        option_keys = option_df["ORG_KEY"].tolist()
        option_label_map = dict(zip(option_df["ORG_KEY"], option_df["ORG_SELECTOR_LABEL"]))
        if st.session_state.get("mcas_demo_org") not in option_keys:
            st.session_state["mcas_demo_org"] = option_keys[0]
        selected_org = st.selectbox(
            "Organization",
            options=option_keys,
            key="mcas_demo_org",
            format_func=lambda option_key: option_label_map.get(option_key, option_key),
        )

    org_data = data[(data["ORG_TYPE"] == view_type) & (data["ORG_KEY"] == selected_org)].copy()
    if org_data.empty:
        st.info("No MCAS data is available for that organization.")
        return

    filter_col1, filter_col2 = st.columns(2)
    with filter_col1:
        subject_options = sort_with_preferred_order(
            org_data["SUBJECT_CODE"].dropna().unique().tolist(),
            MCAS_SUBJECT_ORDER,
        )
        if st.session_state.get("mcas_demo_subject") not in subject_options:
            st.session_state["mcas_demo_subject"] = "ELA" if "ELA" in subject_options else subject_options[0]
        selected_subject = st.selectbox(
            "Subject",
            options=subject_options,
            key="mcas_demo_subject",
            format_func=format_mcas_subject,
        )
    with filter_col2:
        grade_options = sort_with_preferred_order(
            org_data[org_data["SUBJECT_CODE"] == selected_subject]["TEST_GRADE"].dropna().unique().tolist(),
            MCAS_GRADE_ORDER,
        )
        if st.session_state.get("mcas_demo_grade") not in grade_options:
            st.session_state["mcas_demo_grade"] = grade_options[0]
        selected_grade = st.selectbox(
            "Test grade",
            options=grade_options,
            key="mcas_demo_grade",
            format_func=format_mcas_grade,
        )

    group_df = org_data[
        (org_data["SUBJECT_CODE"] == selected_subject)
        & (org_data["TEST_GRADE"] == selected_grade)
    ].copy()
    group_options = sorted(group_df["STU_GRP"].dropna().unique().tolist(), key=str.lower)
    default_groups = [group for group in ["All Students", "Economically Disadvantaged", "English Learners", "Students with Disabilities"] if group in group_options]
    selected_groups = st.multiselect(
        "Student groups",
        options=group_options,
        default=default_groups or group_options[:1],
        key="mcas_demo_groups",
        help="Type to search and add student groups to the plots.",
    )
    if not selected_groups:
        st.warning("Pick at least one student group to display.")
        return

    chart_df = group_df[
        group_df["STU_GRP"].isin(selected_groups)
        & group_df["SY"].notna()
    ].copy()
    if chart_df.empty:
        st.info("No MCAS demographic data is available for that organization / subject / grade selection.")
        return

    ordered_groups = [group for group in group_options if group in selected_groups]
    color_range = cycle_colors(len(ordered_groups))
    grade_label = format_mcas_grade(selected_grade)
    subject_label = format_mcas_subject(selected_subject)

    score_chart = build_labeled_line_chart(
        data=chart_df,
        metric="AVG_SCALED_SCORE",
        y_title="Average Scaled Score",
        chart_title=f"{subject_label} Average Scaled Score by Student Group — {grade_label}",
        group_field="STU_GRP",
        group_title="Student Group",
        group_order=ordered_groups,
        color_range=color_range,
        tooltip_format=".1f",
    )
    participation_chart = build_labeled_line_chart(
        data=chart_df,
        metric="STU_PART_PCT",
        y_title="Student Participation (%)",
        chart_title=f"{subject_label} Student Participation by Student Group — {grade_label}",
        group_field="STU_GRP",
        group_title="Student Group",
        group_order=ordered_groups,
        color_range=color_range,
        tooltip_format=".1f",
    )

    combined_chart = build_aligned_chart_stack([score_chart, participation_chart])
    if combined_chart is None:
        st.info("No MCAS score or participation data is available for that selection.")
        return

    st.altair_chart(combined_chart, use_container_width=True)


def summarize_mcas_trajectory(metric_series, weight_series):
    valid_mask = metric_series.notna()
    if not valid_mask.any():
        return None

    valid_values = metric_series[valid_mask]
    valid_weights = weight_series[valid_mask].fillna(0)
    positive_mask = valid_weights > 0
    if positive_mask.any():
        return (valid_values[positive_mask] * valid_weights[positive_mask]).sum() / valid_weights[positive_mask].sum()
    return valid_values.mean()


def build_mcas_trajectory_plot_df(data, *, subject_code, selected_years, sequences, label_map):
    frames = []
    for order, sequence in enumerate(sequences):
        stage_frames = []
        for school_key in sequence["school_keys"]:
            stage_label = sequence["stage_label_map"].get(school_key, "School")
            allowed_grades = MCAS_STAGE_GRADE_MAP.get(stage_label, set())
            school_df = data[
                (data["ORG_KEY"] == school_key)
                & (data["SUBJECT_CODE"] == subject_code)
                & data["SY"].isin(selected_years)
                & data["TEST_GRADE"].notna()
                & (data["TEST_GRADE"] != "ALL (03-08)")
            ].copy()
            if allowed_grades:
                school_df = school_df[school_df["TEST_GRADE"].isin(allowed_grades)]
            if school_df.empty:
                continue

            school_df["SEQUENCE_LABEL"] = sequence["sequence_label"]
            school_df["SEQUENCE_ORDER"] = order
            school_df["SCHOOL_LABEL"] = school_df["ORG_KEY"].map(label_map).fillna(school_df["ORG_DISPLAY"])
            school_df["STAGE_LABEL"] = stage_label
            stage_frames.append(school_df)

        if not stage_frames:
            continue
        frames.append(pd.concat(stage_frames, ignore_index=True))

    if not frames:
        return pd.DataFrame()

    combined_df = pd.concat(frames, ignore_index=True)

    def aggregate_group(group):
        school_labels = " | ".join(
            dict.fromkeys(
                f"{stage}: {school}"
                for stage, school in zip(group["STAGE_LABEL"], group["SCHOOL_LABEL"])
            )
        )
        return pd.Series(
            {
                "AVG_SCALED_SCORE": summarize_mcas_trajectory(group["AVG_SCALED_SCORE"], group["STU_CNT"]),
                "STU_PART_PCT": summarize_mcas_trajectory(group["STU_PART_PCT"], group["STU_CNT"]),
                "SCHOOL_LABELS": school_labels,
            }
        )

    plot_rows = []
    for group_keys, group in combined_df.groupby(
        ["SEQUENCE_LABEL", "SEQUENCE_ORDER", "SY", "TEST_GRADE"],
        dropna=False,
        sort=False,
    ):
        sequence_label, sequence_order, year, test_grade = group_keys
        summary = aggregate_group(group)
        plot_rows.append(
            {
                "SEQUENCE_LABEL": sequence_label,
                "SEQUENCE_ORDER": sequence_order,
                "SY": year,
                "TEST_GRADE": test_grade,
                "AVG_SCALED_SCORE": summary["AVG_SCALED_SCORE"],
                "STU_PART_PCT": summary["STU_PART_PCT"],
                "SCHOOL_LABELS": summary["SCHOOL_LABELS"],
            }
        )

    plot_df = pd.DataFrame(plot_rows)
    plot_df["SY_LABEL"] = plot_df["SY"].astype(str)
    plot_df["SERIES_LABEL"] = plot_df["SEQUENCE_LABEL"] + " (" + plot_df["SY_LABEL"] + ")"
    return plot_df


def build_mcas_trajectory_chart(
    data,
    *,
    metric,
    y_title,
    chart_title,
    grade_order,
    sequence_order,
    tooltip_format,
    y_domain=None,
):
    metric_df = data[data[metric].notna()].copy()
    if metric_df.empty:
        return None

    base = alt.Chart(metric_df)
    line = base.mark_line(point=True, strokeWidth=3).encode(
        x=alt.X("TEST_GRADE:N", title="Test Grade", sort=grade_order),
        y=alt.Y(
            f"{metric}:Q",
            title=y_title,
            scale=alt.Scale(domain=y_domain, zero=False, nice=False) if y_domain else alt.Undefined,
        ),
        color=alt.Color(
            "SEQUENCE_LABEL:N",
            title="School sequence",
            sort=sequence_order,
            scale=alt.Scale(range=cycle_colors(len(sequence_order))),
        ),
        strokeDash=alt.StrokeDash("SY_LABEL:N", title="Year"),
        detail=["SEQUENCE_LABEL:N", "SY_LABEL:N"],
        tooltip=[
            alt.Tooltip("SEQUENCE_LABEL:N", title="School sequence"),
            alt.Tooltip("SY_LABEL:N", title="Year"),
            alt.Tooltip("TEST_GRADE:N", title="Test Grade"),
            alt.Tooltip("SCHOOL_LABELS:N", title="Schools"),
            alt.Tooltip(f"{metric}:Q", title=y_title, format=tooltip_format),
        ],
    )
    return line.properties(title=chart_title, height=320)


def get_axis_bounds(values, *, padding, min_floor=None, max_ceiling=None):
    valid_values = values.dropna()
    if valid_values.empty:
        return None

    min_value = float(valid_values.min())
    max_value = float(valid_values.max())
    if min_value == max_value:
        min_value -= padding
        max_value += padding
    else:
        min_value -= padding
        max_value += padding

    if min_floor is not None:
        min_value = max(min_floor, min_value)
    if max_ceiling is not None:
        max_value = min(max_ceiling, max_value)
    if min_value >= max_value:
        max_value = min_value + max(padding, 1.0)
    return min_value, max_value


def render_mcas_trajectory_tab(data):
    if data.empty:
        st.warning("No MCAS file is available yet.")
        return

    school_data = data[(data["ORG_TYPE"] == "School") & (data["STU_GRP"] == "All Students")].copy()
    if school_data.empty:
        st.warning("No school-level all-students MCAS data is available.")
        return

    col1, col2 = st.columns([2, 3])
    with col1:
        subject_options = sort_with_preferred_order(
            school_data["SUBJECT_CODE"].dropna().unique().tolist(),
            MCAS_SUBJECT_ORDER,
        )
        if st.session_state.get("mcas_trajectory_subject") not in subject_options:
            st.session_state["mcas_trajectory_subject"] = "ELA" if "ELA" in subject_options else subject_options[0]
        selected_subject = st.selectbox(
            "Subject",
            options=subject_options,
            key="mcas_trajectory_subject",
            format_func=format_mcas_subject,
        )
        year_options = sorted(
            school_data[school_data["SUBJECT_CODE"] == selected_subject]["SY"].dropna().astype(int).unique().tolist()
        )
        default_years = [year_options[-1]] if year_options else []
        current_years = st.session_state.get("mcas_trajectory_years", default_years)
        valid_years = [year for year in current_years if year in year_options]
        if not valid_years:
            valid_years = default_years
        st.session_state["mcas_trajectory_years"] = valid_years
        selected_years = st.multiselect(
            "Years",
            options=year_options,
            default=valid_years,
            key="mcas_trajectory_years",
            help="Choose one or more years to compare how the sequence changes over time.",
        )
        school_search = st.text_input(
            "Search schools (type to filter)",
            key="mcas_trajectory_search",
        )
    with col2:
        sequences, school_label_map = render_school_sequence_selector(
            school_data,
            prefix="mcas_trajectory",
            search=school_search,
        )

    if not selected_years:
        st.warning("Pick at least one year to display.")
        return
    if not sequences:
        st.info("Choose at least one school sequence to display.")
        return

    plot_df = build_mcas_trajectory_plot_df(
        school_data,
        subject_code=selected_subject,
        selected_years=selected_years,
        sequences=sequences,
        label_map=school_label_map,
    )
    if plot_df.empty:
        st.info("No MCAS trajectory data is available for that subject / year / school-sequence selection.")
        return

    grade_order = [
        grade for grade in MCAS_GRADE_ORDER
        if grade in plot_df["TEST_GRADE"].dropna().unique().tolist()
    ]
    sequence_order = [sequence["sequence_label"] for sequence in sequences if sequence["sequence_label"] in plot_df["SEQUENCE_LABEL"].tolist()]
    subject_label = format_mcas_subject(selected_subject)
    axis_col1, axis_col2 = st.columns(2)
    with axis_col1:
        st.markdown("**Score y-axis**")
        default_score_min, default_score_max = 450.0, 550.0
        score_y_min = st.number_input(
            "Score min",
            value=float(default_score_min),
            step=1.0,
            key="mcas_trajectory_score_y_min",
        )
        score_y_max = st.number_input(
            "Score max",
            value=float(default_score_max),
            step=1.0,
            key="mcas_trajectory_score_y_max",
        )
    with axis_col2:
        st.markdown("**Participation y-axis**")
        default_participation_min, default_participation_max = 80.0, 100.0
        participation_y_min = st.number_input(
            "Participation min",
            value=float(default_participation_min),
            step=1.0,
            key="mcas_trajectory_participation_y_min",
        )
        participation_y_max = st.number_input(
            "Participation max",
            value=float(default_participation_max),
            step=1.0,
            key="mcas_trajectory_participation_y_max",
        )

    if score_y_min >= score_y_max:
        st.warning("Score y-axis min must be less than max.")
        return
    if participation_y_min >= participation_y_max:
        st.warning("Participation y-axis min must be less than max.")
        return

    score_chart = build_mcas_trajectory_chart(
        plot_df,
        metric="AVG_SCALED_SCORE",
        y_title="Average Scaled Score",
        chart_title=f"{subject_label} Performance Trajectory",
        grade_order=grade_order,
        sequence_order=sequence_order,
        tooltip_format=".1f",
        y_domain=[score_y_min, score_y_max],
    )
    participation_chart = build_mcas_trajectory_chart(
        plot_df,
        metric="STU_PART_PCT",
        y_title="Student Participation (%)",
        chart_title=f"{subject_label} Participation Trajectory",
        grade_order=grade_order,
        sequence_order=sequence_order,
        tooltip_format=".1f",
        y_domain=[participation_y_min, participation_y_max],
    )

    combined_chart = build_aligned_chart_stack([score_chart, participation_chart])
    if combined_chart is None:
        st.info("No MCAS trajectory score or participation data is available for that selection.")
        return

    st.altair_chart(combined_chart, use_container_width=True)
    st.caption(
        "Each line follows a selected elementary \u2192 middle \u2192 high school sequence across available MCAS test grades for the chosen subject and year."
    )


def render_group_breakdown_tab(
    data,
    *,
    groups,
    colors,
    selector_label,
    selector_key,
    multiselect_label,
    multiselect_key,
    empty_data_message,
    empty_selection_message,
    empty_chart_message,
    title_suffix,
    count_toggle_key,
):
    school_df = data[
        (data["ORG_TYPE"] == "School")
        & (data["STU_GRP"].isin(groups))
    ].copy()
    if school_df.empty:
        st.warning(empty_data_message)
        return

    option_df = build_org_selector_options(school_df, view_type="School")
    option_keys = option_df["ORG_KEY"].tolist()
    option_label_map = dict(zip(option_df["ORG_KEY"], option_df["ORG_SELECTOR_LABEL"]))
    reverse_label_map = {}
    for org_key, label in option_label_map.items():
        reverse_label_map.setdefault(label, []).append(org_key)

    current_value = st.session_state.get(selector_key)
    if current_value not in option_keys and isinstance(current_value, str):
        legacy_matches = reverse_label_map.get(current_value, [])
        if len(legacy_matches) == 1:
            st.session_state[selector_key] = legacy_matches[0]

    selected_school = st.selectbox(
        selector_label,
        options=option_keys,
        key=selector_key,
        format_func=lambda option_key: option_label_map.get(option_key, option_key),
    )
    selected_groups = st.multiselect(
        multiselect_label,
        options=groups,
        default=groups,
        key=multiselect_key,
    )
    show_pct_of_all = st.toggle(
        "Show test takers as percentage of all test takers",
        value=False,
        key=count_toggle_key,
    )

    if not selected_groups:
        st.warning(empty_selection_message)
        return

    chart_df = school_df[
        (school_df["ORG_KEY"] == selected_school)
        & (school_df["STU_GRP"].isin(selected_groups))
    ].copy()

    if chart_df.empty:
        st.info(empty_chart_message)
        return

    ordered_groups = [group for group in groups if group in selected_groups]
    count_metric = "TAKEN_PCT_OF_ALL" if show_pct_of_all else "TAKEN_CNT"
    count_y_title = "Percent of All Test Takers" if show_pct_of_all else "Test Takers"
    count_chart_title = (
        f"Test Takers by {title_suffix} (% of All Students)"
        if show_pct_of_all
        else f"Test Takers by {title_suffix}"
    )
    count_tooltip_format = ".1f" if show_pct_of_all else ".0f"
    chart_specs = [
        (count_metric, count_y_title, count_chart_title, None, count_tooltip_format),
        (
            "READING",
            "Reading",
            f"Reading SAT Scores by {title_suffix}",
            "SAT Critical Reading through 2016; Evidence-Based Reading & Writing from 2017",
            ".0f",
        ),
        ("MATH_SCORE", "Math", f"Math SAT Scores by {title_suffix}", None, ".0f"),
    ]

    for spec in chart_specs:
        metric, y_title, title = spec[:3]
        subtitle = spec[3] if len(spec) > 3 else None
        tooltip_format = spec[4] if len(spec) > 4 else ".0f"
        chart = build_labeled_line_chart(
            data=chart_df,
            metric=metric,
            y_title=y_title,
            chart_title=title,
            group_field="STU_GRP",
            group_title="Group",
            group_order=ordered_groups,
            color_range=colors[: len(ordered_groups)],
            subtitle=subtitle,
            tooltip_format=tooltip_format,
        )
        if chart is None:
            st.info(f"No data to display for **{title}**.")
            continue
        st.altair_chart(chart, use_container_width=True)


def render_racial_breakdown_tab(data):
    render_group_breakdown_tab(
        data,
        groups=RACE_GROUPS,
        colors=RACE_COLORS,
        selector_label="School",
        selector_key="race_school",
        multiselect_label="Race / ethnicity groups",
        multiselect_key="race_groups",
        empty_data_message="No school-level race/ethnicity data is available in the loaded file.",
        empty_selection_message="Pick at least one race / ethnicity group to display.",
        empty_chart_message="No race / ethnicity data is available for that school and selection.",
        title_suffix="Race / Ethnicity",
        count_toggle_key="race_count_toggle",
    )


def render_disadvantaged_breakdown_tab(data):
    render_group_breakdown_tab(
        data,
        groups=DISADVANTAGED_GROUPS,
        colors=DISADVANTAGED_COLORS,
        selector_label="School",
        selector_key="disadvantaged_school",
        multiselect_label="Disadvantaged student groups",
        multiselect_key="disadvantaged_groups",
        empty_data_message="No school-level disadvantaged-group data is available in the loaded file.",
        empty_selection_message="Pick at least one disadvantaged student group to display.",
        empty_chart_message="No disadvantaged-group data is available for that school and selection.",
        title_suffix="Disadvantaged Student Group",
        count_toggle_key="disadvantaged_count_toggle",
    )


st.title("Massachusetts School Trends Over Time")
st.markdown(
    "Use the SAT Scores tab for school and district SAT comparisons plus SAT subgroup breakdowns, "
    "the Demographics Over Time tab for enrollment composition trends, the MCAS scores tab for "
    "MCAS score and participation trends, or the Discipline tab for discipline trends by offense "
    "and student group. Supplemental recent SAT results for Pittsford Sutherland High School (NY) "
    "are included in the school comparison view."
)

section = st.segmented_control(
    "Section",
    ["SAT Scores", "Demographics Over Time", "MCAS scores", "Discipline"],
    default="SAT Scores",
    key="section",
    label_visibility="collapsed",
    width="stretch",
)

if section == "SAT Scores":
    with st.spinner(f"Loading {len(sat_data_paths)} SAT data file(s)..."):
        sat_df = load_sat_data(tuple(sat_data_paths))
    sat_subsection = st.segmented_control(
        "SAT view",
        ["Scores Over Time", "Racial Breakdown", "Disadvantaged Breakdown"],
        default="Scores Over Time",
        key="sat_subsection",
        width="stretch",
    )
    if sat_subsection == "Scores Over Time":
        all_students_df = sat_df[sat_df["STU_GRP"] == "All Students"].copy()
        render_sat_scores_tab(all_students_df)
    elif sat_subsection == "Racial Breakdown":
        render_racial_breakdown_tab(sat_df)
    else:
        render_disadvantaged_breakdown_tab(sat_df)

elif section == "Demographics Over Time":
    with st.spinner(f"Loading {len(demographics_data_paths)} demographics data file(s)..."):
        demographics_df = load_demographics_data(tuple(demographics_data_paths))
    render_demographics_over_time_tab(demographics_df)

elif section == "MCAS scores":
    with st.spinner(f"Loading {len(mcas_data_paths)} MCAS data file(s)..."):
        mcas_df = load_mcas_data(tuple(mcas_data_paths))
    mcas_subsection = st.segmented_control(
        "MCAS view",
        ["Scores Over Time", "Demographic Breakdown", "Performance Trajectory"],
        default="Scores Over Time",
        key="mcas_subsection",
        width="stretch",
    )
    if mcas_subsection == "Scores Over Time":
        mcas_all_students_df = mcas_df[mcas_df["STU_GRP"] == "All Students"].copy()
        render_mcas_scores_tab(mcas_all_students_df)
    elif mcas_subsection == "Demographic Breakdown":
        render_mcas_demographic_tab(mcas_df)
    else:
        render_mcas_trajectory_tab(mcas_df)

else:
    with st.spinner(f"Loading {len(discipline_data_paths)} discipline data file(s)..."):
        discipline_df = load_discipline_data(tuple(discipline_data_paths))
    render_discipline_tab(discipline_df)

st.markdown(
    "Data assumptions: state-level rows are excluded. The SAT Scores tab uses only rows with "
    "`STU_GRP == 'All Students'` for the Scores Over Time subtab. The SAT Racial Breakdown and "
    "Disadvantaged Breakdown subtabs use school rows from the SAT file, and their percentage views "
    "divide each selected subgroup's `TAKEN_CNT` by the matching school-year `All Students` "
    "`TAKEN_CNT`. The Demographics Over Time tab uses the enrollment file and includes all grade "
    "configurations in the selected district or school. Race / ethnicity percentages come directly "
    "from the enrollment file, while race / ethnicity count views are estimated from total "
    "enrollment and reported percentages. Disadvantaged category count views use reported counts "
    "when available and otherwise estimate counts from total enrollment and reported percentages. "
    "The MCAS scores tab normalizes public and charter organization types into district / school, "
    "uses `STU_GRP == 'All Students'` for the Scores Over Time subtab, and plots "
    "`AVG_SCALED_SCORE` plus `STU_PART_PCT` for the selected subject and test grade. The "
    "Demographic Breakdown subtab uses the MCAS file's `STU_GRP` values directly. The "
    "Performance Trajectory subtab uses school-level all-students MCAS rows and lets you define "
    "elementary / middle / high school sequences, then plots `AVG_SCALED_SCORE` and "
    "`STU_PART_PCT` across available test grades for the selected subject and years. The "
    "Discipline tab plots `STU_DISCIPL_CNT` for the selected organization, offense, and "
    "student-group combinations."
)
