from typing import TypedDict


class User(TypedDict, total=False):
    id: int
    nome: str
    email: str
    senha: str
    tipo: str


class Doctor(TypedDict, total=False):
    id: int
    nome: str
    especialidade: str
    crm: str
    telefone: str
    email: str
    status: str


class Patient(TypedDict, total=False):
    id: int
    usuarioId: int
    nome: str
    email: str
    telefone: str
    dataNascimento: str
    data_nascimento: str
    status: str


class Appointment(TypedDict, total=False):
    id: int
    pacienteId: int
    paciente_id: int
    medicoId: int
    medico_id: int
    data: str
    hora: str
    horario: str
    status: str


class Clinic(TypedDict, total=False):
    id: int
    nome: str
    status: str


class HistoryRecord(TypedDict, total=False):
    id: int
    pacienteId: int
    paciente_id: int
    medicoId: int
    medico_id: int
    data: str
    descricao: str
