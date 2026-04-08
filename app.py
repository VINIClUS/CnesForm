"""
CNES Forms — Portal de Gestão de Profissionais de Saúde
Streamlit app for municipal health facility roster management.
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st

from schemas import PROFESSIONAL_ROLES, REGISTRATION_TYPES

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).parent / "data"
CHANGE_LOG_FILE = Path(__file__).parent / "change_logs.json"

st.set_page_config(
    page_title="CNES Forms",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ---------------------------------------------------------------------------
# Data loading (cached)
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner="Carregando dados das unidades...")
def load_facilities() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "facilities.csv", dtype={"cnes_id": str})
    df["cnes_id"] = df["cnes_id"].str.zfill(7)
    return df


@st.cache_data(show_spinner="Carregando profissionais...")
def load_professionals() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "professionals.csv", dtype={"cnes_id": str, "prof_id": str})
    df["cnes_id"] = df["cnes_id"].str.zfill(7)
    return df


# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------

def init_state() -> None:
    defaults = {
        "selected_cnes": None,
        "roster": [],
        "submission_result": None,
        "data_goal": "",
        "justification": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# ---------------------------------------------------------------------------
# Business logic helpers
# ---------------------------------------------------------------------------

def load_roster_for_facility(cnes_id: str, professionals_df: pd.DataFrame) -> list[dict]:
    """Return the current roster for a facility as a list of row dicts."""
    rows = professionals_df[professionals_df["cnes_id"] == cnes_id].to_dict("records")
    for row in rows:
        row["_status"] = "existing"
    return rows


def validate_roster(roster: list[dict], justification: str) -> list[str]:
    """Return a list of validation error messages (empty = valid)."""
    errors: list[str] = []

    new_rows = [r for r in roster if r["_status"] == "new"]

    # Check new professional names
    for i, row in enumerate(new_rows):
        name = str(row.get("name", "")).strip()
        if not name or len(name) < 3:
            errors.append(f"Profissional novo #{i + 1}: nome deve ter pelo menos 3 caracteres.")

    # Check for duplicates among new entries
    seen: set[tuple[str, str]] = set()
    for row in new_rows:
        key = (str(row.get("name", "")).strip().lower(), str(row.get("role", "")).strip().lower())
        if key in seen:
            errors.append(
                f"Duplicata detectada: '{row.get('name')}' com função '{row.get('role')}' já foi adicionado nesta sessão."
            )
        seen.add(key)

    # Check mandatory justification when all professionals are deleted
    all_deleted = all(r["_status"] == "to_delete" for r in roster) and len(roster) > 0
    if all_deleted and not justification.strip():
        errors.append("Todos os profissionais foram marcados para exclusão. Uma justificativa é obrigatória.")

    return errors


def build_change_log(facility: pd.Series, roster: list[dict], data_goal: str, justification: str) -> dict:
    """Build the JSON change log payload."""
    internal_keys = {"_status", "_temp_id"}

    def clean(row: dict) -> dict:
        return {k: v for k, v in row.items() if k not in internal_keys}

    return {
        "metadata": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "facility_cnes": str(facility["cnes_id"]),
            "facility_name": str(facility["name"]),
            "data_goal": data_goal,
            "operator": "system",
        },
        "CREATE": [clean(r) for r in roster if r["_status"] == "new"],
        "DELETE": [clean(r) for r in roster if r["_status"] == "to_delete"],
        "UPDATE": [],
        "justification": justification if justification.strip() else None,
    }


def append_change_log(entry: dict) -> None:
    """Append a change log entry to change_logs.json."""
    logs: list[dict] = []
    if CHANGE_LOG_FILE.exists():
        try:
            with open(CHANGE_LOG_FILE, "r", encoding="utf-8") as f:
                logs = json.load(f)
        except (json.JSONDecodeError, ValueError):
            logs = []
    logs.append(entry)
    with open(CHANGE_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# UI components
# ---------------------------------------------------------------------------

def render_facility_header(facility: pd.Series) -> None:
    st.subheader(f"🏥 {facility['name']}")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("CNES", facility["cnes_id"])
    col2.metric("Tipo", facility["facility_type"])
    col3.metric("Município", f"{facility['city']} / {facility['state']}")
    col4.metric("Telefone", facility["phone"])
    st.caption(f"Email: {facility['email']} | CEP: {facility['cep']} | CNPJ: {facility['cnpj']}")
    st.divider()


def render_roster_row(i: int, row: dict) -> None:
    """Render a single roster row with action buttons."""
    status = row["_status"]

    # Visual styling by status
    if status == "to_delete":
        container_style = "border-left: 4px solid #e74c3c; padding-left: 8px; opacity: 0.6;"
        label_prefix = "~~"
    elif status == "new":
        container_style = "border-left: 4px solid #27ae60; padding-left: 8px;"
        label_prefix = "✨ "
    else:
        container_style = "border-left: 4px solid #3498db; padding-left: 8px;"
        label_prefix = ""

    with st.container():
        if status == "to_delete":
            st.markdown(
                f"<div style='{container_style}'><s><b>{row.get('name', '—')}</b> — {row.get('role', '—')}</s> "
                f"<span style='color:#e74c3c;font-size:0.8em;'>EXCLUSÃO PENDENTE</span></div>",
                unsafe_allow_html=True,
            )
            col_btn, _ = st.columns([1, 5])
            if col_btn.button("↩ Restaurar", key=f"restore_{i}"):
                st.session_state.roster[i]["_status"] = "existing"
                st.rerun()

        elif status == "new":
            st.markdown(
                f"<div style='{container_style}'><b>{label_prefix}Novo Profissional</b></div>",
                unsafe_allow_html=True,
            )
            col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 2, 1])
            name_val = col1.text_input("Nome *", value=row.get("name", ""), key=f"new_name_{i}")
            role_val = col2.selectbox(
                "Função *",
                PROFESSIONAL_ROLES,
                index=PROFESSIONAL_ROLES.index(row["role"]) if row.get("role") in PROFESSIONAL_ROLES else 0,
                key=f"new_role_{i}",
            )
            reg_type_val = col3.selectbox(
                "Tipo Registro",
                REGISTRATION_TYPES,
                index=REGISTRATION_TYPES.index(row["registration_type"]) if row.get("registration_type") in REGISTRATION_TYPES else 0,
                key=f"new_reg_type_{i}",
            )
            reg_num_val = col4.text_input("Nº Registro", value=row.get("registration_number", ""), key=f"new_reg_num_{i}")
            st.session_state.roster[i]["name"] = name_val
            st.session_state.roster[i]["role"] = role_val
            st.session_state.roster[i]["registration_type"] = reg_type_val
            st.session_state.roster[i]["registration_number"] = reg_num_val
            if col5.button("🗑", key=f"remove_new_{i}", help="Remover"):
                st.session_state.roster.pop(i)
                st.rerun()

        else:  # existing
            col1, col2, col3, col_btn = st.columns([3, 2, 2, 1])
            col1.markdown(f"**{row.get('name', '—')}**")
            col2.markdown(row.get("role", "—"))
            col3.markdown(f"{row.get('registration_type', '')} {row.get('registration_number', '')}")
            if col_btn.button("🗑 Excluir", key=f"delete_{i}"):
                st.session_state.roster[i]["_status"] = "to_delete"
                st.rerun()


# ---------------------------------------------------------------------------
# Main app
# ---------------------------------------------------------------------------

def main() -> None:
    init_state()

    facilities_df = load_facilities()
    professionals_df = load_professionals()

    # -----------------------------------------------------------------------
    # Header
    # -----------------------------------------------------------------------
    st.title("📋 CNES Forms — Gestão de Profissionais")
    st.markdown("Gerencie o quadro de profissionais das unidades de saúde e registre alterações.")
    st.divider()

    # -----------------------------------------------------------------------
    # Facility search
    # -----------------------------------------------------------------------
    st.subheader("1. Selecione a Unidade de Saúde")
    search_query = st.text_input(
        "Buscar por CNES (7 dígitos) ou Nome da Unidade",
        placeholder="Ex: 2078015 ou UBS Vila Nova",
        key="search_input",
    )

    # Filter facilities
    if search_query.strip():
        q = search_query.strip()
        mask = facilities_df["cnes_id"].str.startswith(q) | facilities_df["name"].str.contains(q, case=False, na=False)
        filtered = facilities_df[mask]
    else:
        filtered = facilities_df

    if filtered.empty:
        st.warning("Nenhuma unidade encontrada para a busca informada.")
        return

    options = [f"{row['cnes_id']} — {row['name']}" for _, row in filtered.iterrows()]
    selected_option = st.selectbox("Unidades encontradas", options, key="facility_select")

    if selected_option:
        selected_cnes = selected_option.split(" — ")[0].strip()

        # Load roster when facility changes
        if st.session_state.selected_cnes != selected_cnes:
            st.session_state.selected_cnes = selected_cnes
            st.session_state.roster = load_roster_for_facility(selected_cnes, professionals_df)
            st.session_state.submission_result = None
            st.session_state.data_goal = ""
            st.session_state.justification = ""

        facility = facilities_df[facilities_df["cnes_id"] == selected_cnes].iloc[0]

        st.divider()

        # -----------------------------------------------------------------------
        # Facility info
        # -----------------------------------------------------------------------
        st.subheader("2. Dados da Unidade")
        render_facility_header(facility)

        # -----------------------------------------------------------------------
        # Roster editor
        # -----------------------------------------------------------------------
        st.subheader("3. Quadro de Profissionais")

        roster = st.session_state.roster
        active_count = sum(1 for r in roster if r["_status"] != "to_delete")
        to_delete_count = sum(1 for r in roster if r["_status"] == "to_delete")
        new_count = sum(1 for r in roster if r["_status"] == "new")

        col_s1, col_s2, col_s3 = st.columns(3)
        col_s1.metric("Ativos / Existentes", active_count)
        col_s2.metric("Marcados p/ Exclusão", to_delete_count)
        col_s3.metric("Novos Adicionados", new_count)

        if roster:
            # Column headers for existing rows
            h1, h2, h3, h4 = st.columns([3, 2, 2, 1])
            h1.markdown("**Nome**")
            h2.markdown("**Função**")
            h3.markdown("**Registro**")
            h4.markdown("**Ação**")
            st.markdown("---")

            for i, row in enumerate(roster):
                render_roster_row(i, row)
                st.markdown("")
        else:
            st.info("Nenhum profissional cadastrado para esta unidade.")

        if st.button("➕ Adicionar Profissional", type="secondary"):
            st.session_state.roster.append({
                "_status": "new",
                "_temp_id": str(uuid.uuid4()),
                "name": "",
                "role": PROFESSIONAL_ROLES[0],
                "registration_type": REGISTRATION_TYPES[0],
                "registration_number": "",
                "cnes_id": selected_cnes,
            })
            st.rerun()

        # -----------------------------------------------------------------------
        # Submission form
        # -----------------------------------------------------------------------
        st.divider()
        st.subheader("4. Finalizar e Enviar")

        data_goal = st.text_input(
            "Motivo das alterações",
            value=st.session_state.data_goal,
            placeholder="Ex: Atualização mensal de quadro, substituição por saída...",
            key="data_goal_input",
        )
        st.session_state.data_goal = data_goal

        # Mandatory justification when all are deleted
        all_deleted = all(r["_status"] == "to_delete" for r in roster) and len(roster) > 0
        justification = ""
        if all_deleted:
            st.warning("⚠️ Todos os profissionais estão marcados para exclusão.")
            justification = st.text_area(
                "Justificativa obrigatória para exclusão total *",
                value=st.session_state.justification,
                placeholder="Descreva o motivo pelo qual todos os profissionais serão removidos...",
                key="justification_input",
            )
            st.session_state.justification = justification

        # Display previous submission result
        if st.session_state.submission_result:
            result = st.session_state.submission_result
            if result["success"]:
                st.success(f"✅ Registro enviado com sucesso! {result['summary']}")
            else:
                for err in result["errors"]:
                    st.error(err)

        if st.button("📤 Enviar Registro de Alterações", type="primary"):
            errors = validate_roster(roster, justification)
            if errors:
                st.session_state.submission_result = {"success": False, "errors": errors}
                st.rerun()
            else:
                entry = build_change_log(facility, roster, data_goal, justification)
                append_change_log(entry)
                create_count = len(entry["CREATE"])
                delete_count = len(entry["DELETE"])
                summary = f"{create_count} criação(ões), {delete_count} exclusão(ões) registradas."
                st.session_state.submission_result = {"success": True, "summary": summary}
                # Reset roster to reflect submitted state
                st.session_state.roster = load_roster_for_facility(selected_cnes, professionals_df)
                st.rerun()


if __name__ == "__main__":
    main()
