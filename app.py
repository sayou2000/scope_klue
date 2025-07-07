import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")
st.title("Migration Scope Entscheidung (Flache Ansicht)")

# CSV Upload
uploaded_file = st.file_uploader("Lade die CSV-Datei hoch", type="csv")
if uploaded_file:
    # CSV laden
    try:
        df = pd.read_csv(uploaded_file, sep=";", quotechar='"', encoding="utf-8", on_bad_lines="skip")
    except Exception as e:
        st.error(f"Fehler beim Einlesen der Datei: {e}")
        st.stop()

    # Spalten prüfen
    required_columns = {"Id", "ParentId", "DisplayName"}
    if not required_columns.issubset(df.columns):
        st.error(f"CSV muss folgende Spalten enthalten: {', '.join(required_columns)}")
        st.write("Gefundene Spalten:", df.columns.tolist())
        st.stop()

    # Pfad berechnen (rekursiv über ParentId)
    df_unique = df.drop_duplicates(subset="Id")
    id_map = df_unique.set_index("Id")[["ParentId", "DisplayName"]].to_dict("index")

    def build_path(object_id):
        path = []
        current = object_id
        seen = set()
        while current in id_map and current not in seen:
            seen.add(current)
            path.insert(0, str(id_map[current]["DisplayName"]))
            current = id_map[current]["ParentId"]
        return " > ".join(path)

    df["Pfad"] = df["Id"].apply(build_path)

    # Scope-Spalte initialisieren
    if "Scope" not in df.columns:
        df["Scope"] = "Unentschieden"

    # Filter
    st.subheader("Filter")
    search_term = st.text_input("🔍 Suche nach Objektnamen oder Pfad")
    filtered_df = df[df["Pfad"].str.contains(search_term, case=False, na=False)] if search_term else df

    # Scope-Festlegung
    st.subheader("Scope-Festlegung")

    for idx, row in filtered_df.iterrows():
        scope = st.radio(
            f"{row['Pfad']} ({row['Id']})",
            ["Unentschieden", "In Scope", "Out of Scope"],
            index=["Unentschieden", "In Scope", "Out of Scope"].index(row["Scope"]),
            key=f"scope_{row['Id']}"
        )
        df.at[idx, "Scope"] = scope

    # Exportbereich
    st.subheader("Export")
    export_df = df[["Id", "DisplayName", "Pfad", "Scope"]]
    st.download_button(
        label="📥 CSV mit Entscheidungen herunterladen",
        data=export_df.to_csv(index=False),
        file_name="scope_entscheidungen.csv",
        mime="text/csv"
    )
