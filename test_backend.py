import os
import unittest
from copy import deepcopy
from unittest.mock import MagicMock, call, patch
from uuid import uuid4

with patch.dict(os.environ, {"MONGO_URI": "mongodb://127.0.0.1:27017"}):
    from app import create_app

from repositories.mongo_repository import MongoRepository


class InMemoryRepository:
    def __init__(self):
        self.collections = {
            "usuarios": [
                {
                    "id": 1,
                    "nome": "Admin",
                    "email": "admin@AgendaMed.com",
                    "senha": "123456",
                    "tipo": "clinica",
                    "tipoClinica": "admin",
                },
                {
                    "id": 2,
                    "nome": "Dr. Altemar",
                    "email": "altemar@clinica.com",
                    "senha": "123456",
                    "tipo": "clinica",
                    "tipoClinica": "medico",
                },
                {
                    "id": 3,
                    "nome": "Sabrina",
                    "email": "sabrina@AgendaMed.com",
                    "senha": "123456",
                    "tipo": "paciente",
                },
            ],
            "medicos": [
                {
                    "id": 2,
                    "nome": "Dr. Altemar",
                    "especialidade": "Clínica Geral",
                    "crm": "123456-SP",
                    "telefone": "(11) 99999-9999",
                    "email": "altemar@clinica.com",
                    "status": "ativo",
                },
                {
                    "id": 4,
                    "nome": "Dra. Ana Souza",
                    "especialidade": "Cardiologia",
                    "crm": "654321-SP",
                    "telefone": "(11) 98888-7777",
                    "email": "ana@AgendaMed.com",
                    "status": "ativo",
                },
            ],
            "pacientes": [
                {
                    "id": 3,
                    "nome": "Sabrina",
                    "data_nascimento": "1990-04-12",
                    "telefone": "(11) 98888-9999",
                    "email": "sabrina@AgendaMed.com",
                    "usuarioId": 3,
                    "status": "ativo",
                }
            ],
            "agendamentos": [
                {
                    "id": 1,
                    "paciente_id": 3,
                    "medico_id": 2,
                    "data": "2025-10-15",
                    "hora": "14:00",
                    "status": "Confirmado",
                }
            ],
            "clinicas": [],
            "logs": [
                {
                    "id": 1,
                    "paciente_id": 3,
                    "medico_id": 2,
                    "data": "2025-09-20",
                    "descricao": "Consulta de rotina.",
                }
            ],
        }
        self.documents = {
            "configuracoes": {"tema": "light", "notificacoes": True}
        }

    def get_all(self, collection):
        return deepcopy(self.collections.get(collection, []))

    def insert(self, collection, record):
        self.collections.setdefault(collection, []).append(deepcopy(record))

    def replace(self, collection, record):
        records = self.collections.setdefault(collection, [])
        for index, existing in enumerate(records):
            if existing.get("id") == record.get("id"):
                records[index] = deepcopy(record)
                return
        records.append(deepcopy(record))

    def delete(self, collection, record_id):
        records = self.collections.setdefault(collection, [])
        for record in records:
            if record.get("id") == record_id:
                records.remove(record)
                return True
        return False

    def get_document(self, collection):
        return deepcopy(self.documents.get(collection, {}))

    def save_document(self, collection, document):
        self.documents[collection] = deepcopy(document)


class BackendTests(unittest.TestCase):
    def setUp(self):
        repository = InMemoryRepository()
        self.app = create_app(repository=repository)
        self.client = self.app.test_client()

    def test_health(self):
        resp = self.client.get('/api/health')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('status', resp.get_json())

    def test_login_success(self):
        resp = self.client.post('/api/login', json={
            'email': 'admin@AgendaMed.com',
            'senha': '123456'
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()['usuario']['email'], 'admin@AgendaMed.com')

    def test_get_medicos(self):
        resp = self.client.get('/api/medicos')
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.get_json(), list)

    def test_matchmaking(self):
        resp = self.client.post('/api/matchmaking', json={
            'paciente_id': 3,
            'necessidade': 'dor no peito e falta de ar',
            'sintomas': ['dor no peito', 'falta de ar'],
            'data': '2026-09-22',
            'hora': '14:00'
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIn('recomendacoes', resp.get_json())
        self.assertGreater(len(resp.get_json()['recomendacoes']), 0)
        self.assertEqual(resp.get_json()['recomendacoes'][0]['especialidade'], 'Cardiologia')
        self.assertEqual(resp.get_json()['recomendacoes'][0]['prioridade'], 'especialidade_e_disponibilidade')

    def test_matchmaking_accepts_frontend_fields_and_checks_availability(self):
        resp = self.client.post('/api/matchmaking', json={
            'pacienteId': '3',
            'necessidade': 'dor no peito',
            'sintomas': ['falta de ar'],
            'data': '2026-09-22',
            'hora': '14:00'
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()['recomendacoes'][0]['id'], 4)

        disponibilidade = self.client.get('/api/medicos/2/disponibilidade?data=2025-10-15')
        self.assertEqual(disponibilidade.status_code, 200)
        horario = next(item for item in disponibilidade.get_json()['horarios'] if item['hora'] == '14:00')
        self.assertFalse(horario['disponivel'])

    def test_historico_and_triagem_routes(self):
        historico = self.client.get('/api/historico')
        self.assertEqual(historico.status_code, 200)
        self.assertIsInstance(historico.get_json(), list)

        triagem = self.client.post('/api/triagem', json={
            'paciente_id': 3,
            'necessidade': 'dor no peito',
            'sintomas': ['dor no peito'],
        })
        self.assertEqual(triagem.status_code, 200)
        self.assertIn('recomendacoes', triagem.get_json())

        medico = self.client.get('/api/medicos/2')
        self.assertEqual(medico.status_code, 200)
        self.assertEqual(medico.get_json()['id'], 2)

    def test_frontend_contract_routes(self):
        email = f'maria-{uuid4().hex}@AgendaMed.com'
        cadastro = self.client.post('/api/cadastro', json={
            'nome': 'Maria Souza',
            'email': email,
            'senha': '123456',
            'tipo': 'paciente'
        })
        self.assertEqual(cadastro.status_code, 201)
        self.assertIn('usuario', cadastro.get_json())

        agenda = self.client.post('/api/agenda', json={
            'pacienteId': 3,
            'medicoId': 2,
            'data': '2026-09-25',
            'hora': '16:30',
            'status': 'agendado',
            'pacienteNome': 'Sabrina',
            'medicoNome': 'Dr. Altemar',
            'medicoEspecialidade': 'Clínica Geral'
        })
        self.assertEqual(agenda.status_code, 201)
        self.assertEqual(agenda.get_json()['pacienteId'], 3)

        perfil = self.client.get('/api/perfil/3')
        self.assertEqual(perfil.status_code, 200)
        self.assertEqual(perfil.get_json()['id'], 3)

        perfil_update = self.client.put('/api/perfil/3', json={
            'telefone': '(11) 98888-9999',
            'dataNascimento': '1990-04-12'
        })
        self.assertEqual(perfil_update.status_code, 200)
        self.assertEqual(perfil_update.get_json()['telefone'], '(11) 98888-9999')

    def test_frontend_delete_and_legacy_agenda_contract(self):
        agenda = self.client.get('/api/agenda')
        self.assertEqual(agenda.status_code, 200)
        self.assertIn('pacienteId', agenda.get_json()[0])
        self.assertIn('medicoId', agenda.get_json()[0])

        medico = self.client.post('/api/medicos', json={
            'nome': 'Médico temporário',
            'especialidade': 'Pediatria'
        })
        medico_id = medico.get_json()['id']
        self.assertEqual(self.client.delete(f'/api/medicos/{medico_id}').status_code, 200)

        paciente = self.client.post('/api/pacientes', json={
            'nome': 'Paciente temporário',
            'email': f'temp-{uuid4().hex}@example.com'
        })
        paciente_id = paciente.get_json()['id']
        self.assertEqual(self.client.delete(f'/api/pacientes/{paciente_id}').status_code, 200)

        novo_agendamento = self.client.post('/api/agenda', json={
            'pacienteId': 3,
            'medicoId': 2,
            'data': '2026-09-30',
            'hora': '10:00'
        })
        agendamento_id = novo_agendamento.get_json()['id']
        self.assertEqual(self.client.delete(f'/api/agenda/{agendamento_id}').status_code, 200)

    def test_clinica_crud_contract(self):
        criada = self.client.post('/api/clinicas', json={'nome': 'Clínica Teste'})
        self.assertEqual(criada.status_code, 201)
        clinica = criada.get_json()
        atualizada = self.client.post('/api/clinicas', json={**clinica, 'nome': 'Clínica Atualizada'})
        self.assertEqual(atualizada.status_code, 200)
        self.assertEqual(atualizada.get_json()['nome'], 'Clínica Atualizada')
        self.assertEqual(self.client.delete(f"/api/clinicas/{clinica['id']}").status_code, 200)


class MongoRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.client = MagicMock()
        self.database = MagicMock()
        self.collection = MagicMock()
        self.client.__getitem__.return_value = self.database
        self.database.__getitem__.return_value = self.collection

        with patch(
            "repositories.mongo_repository.MongoClient",
            return_value=self.client,
        ):
            self.repository = MongoRepository(
                "mongodb://localhost:27017",
                "callmed",
            )

    def test_requires_mongo_uri(self):
        with self.assertRaisesRegex(RuntimeError, "MONGO_URI"):
            MongoRepository("", "callmed")

    def test_lists_records_from_existing_database_collections(self):
        self.collection.find.return_value = [
            {"_id": "mongo-id", "id": 7, "nome": "Médico"}
        ]

        records = self.repository.get_all("medicos")

        self.assertEqual(records, [{"id": 7, "nome": "Médico"}])
        self.assertEqual(self.database.__getitem__.call_args, call("medicos"))

    def test_maps_api_history_and_settings_to_existing_collections(self):
        self.repository.get_all("historico")
        self.assertEqual(self.database.__getitem__.call_args, call("logs"))

        self.collection.find_one.return_value = None
        self.repository.get_document("config")
        self.assertEqual(
            self.database.__getitem__.call_args,
            call("configuracoes"),
        )

    def test_updates_the_existing_global_settings_document(self):
        self.collection.find_one.return_value = {"_id": "settings-id"}
        settings = {"tema": "dark", "notificacoes": False}

        self.repository.save_document("config", settings)

        self.collection.update_one.assert_called_once_with(
            {"_id": "settings-id"},
            {"$set": settings},
        )

    def test_updates_and_deletes_only_the_record_with_matching_numeric_id(self):
        record = {"id": 12, "nome": "Dra. Nova"}

        self.repository.replace("medicos", record)
        self.collection.replace_one.assert_called_once_with(
            {"id": 12},
            record,
            upsert=True,
        )

        self.collection.delete_one.return_value.deleted_count = 1
        self.assertTrue(self.repository.delete("medicos", 12))
        self.collection.delete_one.assert_called_once_with({"id": 12})


if __name__ == '__main__':
    unittest.main()
