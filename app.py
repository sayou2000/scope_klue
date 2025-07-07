import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")
st.title("Migration Scope Entscheidung (Flache Ansicht)")

# CSV Upload
uploaded_file = st.file_uploader("Lade die CSV-Datei hoch", type="csv")
if uploaded_file:
    # CSV laden
    df = pd.read_csv(uploaded_file, sep=";", quotechar='"', encoding="utf-8")

    # Basis-Checks
    required_columns = {"TenantId", "ParentId", "DisplayName"}
    if not required_columns.issubset(df.columns):
        st.error(f"CSV muss folgende Spalten enthalten: {', '.join(required_columns)}")
        st.stop()

    # Pfad berechnen (flach, rekursiv über ParentId)
    id_map = df.set_index("TenantId")[["ParentId", "DisplayName"]].to_dict("index")

    def build_path(tenant_id):
        path = []
        current = tenant_id
        seen = set()
        while current in id_map and current not in seen:
            seen.add(current)
            path.insert(0, id_map[current]["DisplayName"])
            current = id_map[current]["ParentId"]
        return " > ".join(path)

    df["Pfad"] = df["TenantId"].apply(build_path)

    # Scope-Spalte initialisieren
    if "Scope" not in df.columns:
        df["Scope"] = "Unentschieden"

    # Filteroptionen (optional erweitern)
    st.subheader("Filter")
    search_term = st.text_input("Suche nach Objektnamen oder Pfad")
    filtered_df = df[df["Pfad"].str.contains(search_term, case=False, na=False)] if search_term else df

    # Auswahl pro Zeile (In/Out of Scope)
    st.subheader("Scope-Festlegung")

    for idx, row in filtered_df.iterrows():
        scope = st.radio(
            f"{row['Pfad']} ({row['TenantId']})",
            ["Unentschieden", "In Scope", "Out of Scope"],
            index=["Unentschieden", "In Scope", "Out of Scope"].index(row["Scope"]),
            key=f"scope_{row['TenantId']}"
        )
        df.at[idx, "Scope"] = scope

    # Export
    st.subheader("Export")
    export_df = df[["TenantId", "DisplayName", "Pfad", "Scope"]]
    st.download_button("📥 CSV mit Entscheidungen herunterladen", export_df.to_csv(index=False), file_name="scope_entscheidungen.csv")
