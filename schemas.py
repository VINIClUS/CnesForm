"""
Schemas padronizados para o portal CNES Forms.
Espelha a estrutura do banco CnesData (cnesdata.duckdb).
"""

from dataclasses import dataclass, field
from typing import Final, Optional


# ---------------------------------------------------------------------------
# Domain constants
# ---------------------------------------------------------------------------

FACILITY_TYPES: Final[list[str]] = [
    "UBS - Unidade Básica de Saúde",
    "UPA - Unidade de Pronto Atendimento",
    "Hospital Geral",
    "Hospital Especializado",
    "Policlínica",
    "Centro de Especialidades Odontológicas",
    "CAPS - Centro de Atenção Psicossocial",
    "Laboratório de Saúde Pública",
    "Farmácia",
    "Outros",
]

PROFESSIONAL_ROLES: Final[list[str]] = [
    "Médico",
    "Enfermeiro",
    "Técnico de Enfermagem",
    "Dentista",
    "Fisioterapeuta",
    "Psicólogo",
    "Farmacêutico",
    "Assistente Social",
    "Nutricionista",
    "Fonoaudiólogo",
    "Terapeuta Ocupacional",
    "Agente Comunitário de Saúde",
    "Auxiliar de Enfermagem",
    "Biomédico",
    "Outros",
]

REGISTRATION_TYPES: Final[list[str]] = [
    "CRM",   # Médico
    "COREN", # Enfermagem
    "CRO",   # Dentista
    "CREFITO", # Fisioterapeuta
    "CRP",   # Psicólogo
    "CRF",   # Farmacêutico
    "CRESS", # Assistente Social
    "CRN",   # Nutricionista
    "CREFONO", # Fonoaudiólogo
    "N/A",
]

PROFESSIONAL_STATUS: Final[list[str]] = ["ATIVO", "INATIVO", "AFASTADO"]

VINCULO_TYPES: Final[list[str]] = [
    "CLT",
    "Estatutário",
    "Temporário",
    "Autônomo",
    "Voluntário",
]


# ---------------------------------------------------------------------------
# Data schemas (mirrors CnesData DB tables)
# ---------------------------------------------------------------------------

@dataclass
class Facility:
    """Espelha tabela estabelecimentos do cnesdata.duckdb."""
    cnes_id: str           # 7 dígitos, PK
    name: str              # NOME_FANTASIA
    facility_type: str     # TIPO_UNIDADE
    cnpj: str              # CNPJ_MANTENEDORA (14 dígitos)
    legal_nature: str      # NATUREZA_JURIDICA
    municipality_code: str # COD_MUNICIPIO
    sus_link: bool         # VINCULO_SUS
    address: str
    city: str
    state: str
    cep: str
    phone: str
    email: str
    source: str = "CSV"    # FONTE


@dataclass
class Professional:
    """Espelha tabela profissionais do cnesdata.duckdb."""
    prof_id: str            # PK gerado
    cnes_id: str            # FK -> Facility.cnes_id
    name: str               # NOME_PROFISSIONAL
    cpf: str                # 11 dígitos
    cns: str                # CNS — Cartão Nacional de Saúde
    role: str               # Descrição do CBO
    cbo_code: str           # Código CBO
    registration_number: str
    registration_type: str
    vinculo_type: str       # TIPO_VINCULO
    sus: bool               # Atua no SUS
    status: str             # ATIVO | INATIVO | AFASTADO
    sex: str = "N/I"        # SEXO


@dataclass
class ChangeLogEntry:
    """Payload de auditoria gerado em cada submissão do formulário."""
    metadata: dict
    CREATE: list[dict] = field(default_factory=list)
    DELETE: list[dict] = field(default_factory=list)
    UPDATE: list[dict] = field(default_factory=list)
    justification: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "metadata": self.metadata,
            "CREATE": self.CREATE,
            "DELETE": self.DELETE,
            "UPDATE": self.UPDATE,
            "justification": self.justification,
        }


# ---------------------------------------------------------------------------
# CSV column contracts (used for validation at load time)
# ---------------------------------------------------------------------------

SCHEMA_ESTABELECIMENTO: Final[tuple[str, ...]] = (
    "cnes_id",
    "name",
    "facility_type",
    "cnpj",
    "municipality_code",
    "city",
    "state",
    "cep",
    "phone",
    "email",
)

SCHEMA_PROFISSIONAL: Final[tuple[str, ...]] = (
    "prof_id",
    "cnes_id",
    "name",
    "cpf",
    "cns",
    "role",
    "cbo_code",
    "registration_number",
    "registration_type",
    "status",
)
