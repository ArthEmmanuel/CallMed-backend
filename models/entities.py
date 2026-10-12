from typing import TypedDict


class User(TypedDict, total=False):
    id: int | str
    nome: str
    email: str
    senha: str
    tipo: str
    tipoClinica: str
    telefone: str


class Patient(TypedDict, total=False):
    id: int | str
    usuarioId: int | str
    nome: str
    email: str
    telefone: str
    dataNascimento: str
    data_nascimento: str
    status: str


class Doctor(TypedDict, total=False):
    id: int | str
    usuarioId: int | str
    nome: str
    email: str
    telefone: str
    especialidade: str
    crm: str
    perfil: dict
    status: str


class TriageConversation(TypedDict, total=False):
    id: str
    usuarioId: int | str
    pacienteId: int | str
    status: str
    estado: str
    dados: dict
    mensagens: list[dict]
    preferencias: dict
    matchmaking: dict
    criadoEm: str
    atualizadoEm: str
