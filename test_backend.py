import os
import unittest
from copy import deepcopy
from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

with patch.dict(os.environ, {"SECRET_KEY": "test-secret-key-for-callmed"}):
    from app import create_app

from repositories.database_module import load_database_module
from repositories.mongo_repository import MongoRepository
from werkzeug.security import check_password_hash


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
            "especialidades": [
                {"id": 1, "nome": "Otorrinolaringologia"},
                {"id": 2, "nome": "Dermatologia"},
            ],
            "configuracoes_usuario": [],
            "triagens": [],
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

    def get_by_id(self, collection, record_id):
        return next(
            (
                deepcopy(record)
                for record in self.collections.get(collection, [])
                if str(record.get("id")) == str(record_id)
            ),
            None,
        )

    def find_by_field(self, collection, field, value):
        return next(
            (
                deepcopy(record)
                for record in self.collections.get(collection, [])
                if (
                    str(record.get(field, "")).casefold()
                    == str(value).casefold()
                    if field == "email"
                    else str(record.get(field)) == str(value)
                )
            ),
            None,
        )

    def insert(self, collection, record):
        self.collections.setdefault(collection, []).append(deepcopy(record))
        return deepcopy(record)

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
            if str(record.get("id")) == str(record_id):
                records.remove(record)
                return True
        return False

    def delete_by_field(self, collection, field, value):
        records = self.collections.setdefault(collection, [])
        original_count = len(records)
        records[:] = [
            record
            for record in records
            if str(record.get(field)) != str(value)
        ]
        return original_count - len(records)

    def get_document(self, collection):
        if collection == "config":
            collection = "configuracoes"
        return deepcopy(self.documents.get(collection, {}))

    def save_document(self, collection, document):
        if collection == "config":
            collection = "configuracoes"
        self.documents[collection] = deepcopy(document)

    def replace_document(self, collection, document):
        if collection == "config":
            collection = "configuracoes"
        self.documents[collection] = deepcopy(document)

    def delete_document(self, collection):
        if collection == "config":
            collection = "configuracoes"
        return self.documents.pop(collection, None) is not None


class BackendTests(unittest.TestCase):
    def setUp(self):
        repository = InMemoryRepository()
        self.repository = repository
        self.app = create_app(
            repository=repository,
            config_overrides={
                "SECRET_KEY": "test-secret-key-for-callmed",
                "TOKEN_MAX_AGE_SECONDS": 3600,
            },
        )
        self.client = self.app.test_client()
        login = self.client.post(
            "/api/login",
            json={"email": "admin@AgendaMed.com", "senha": "123456"},
        )
        self.assertEqual(login.status_code, 200)
        self.client.environ_base["HTTP_AUTHORIZATION"] = (
            f"Bearer {login.get_json()['token']}"
        )

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
        self.assertTrue(resp.get_json()["token"])
        self.assertNotIn("senha", resp.get_json()["usuario"])
        stored_user = self.repository.get_by_id("usuarios", 1)
        self.assertTrue(check_password_hash(stored_user["senha"], "123456"))

    def test_login_rejects_wrong_password_and_missing_account(self):
        wrong_password = self.client.post(
            "/api/login",
            json={"email": "admin@AgendaMed.com", "senha": "incorrect"},
        )
        missing_user = self.client.post(
            "/api/login",
            json={"email": "missing@example.com", "senha": "123456"},
        )
        self.assertEqual(wrong_password.status_code, 401)
        self.assertEqual(missing_user.status_code, 401)

    def test_protected_routes_reject_missing_and_invalid_tokens(self):
        anonymous = self.app.test_client()
        self.assertEqual(anonymous.get("/api/usuarios").status_code, 401)
        invalid = anonymous.get(
            "/api/usuarios",
            headers={"Authorization": "Bearer invalid-token"},
        )
        self.assertEqual(invalid.status_code, 401)

    def test_regular_user_cannot_access_admin_operations(self):
        created = self.client.post(
            "/api/cadastro",
            json={
                "nome": "Paciente comum",
                "email": f"paciente-{uuid4().hex}@example.com",
                "senha": "minha-senha",
                "tipo": "paciente",
            },
        )
        self.assertEqual(created.status_code, 201)
        email = created.get_json()["usuario"]["email"]
        patient_client = self.app.test_client()
        login = patient_client.post(
            "/api/login",
            json={"email": email, "senha": "minha-senha"},
        )
        headers = {"Authorization": f"Bearer {login.get_json()['token']}"}
        self.assertEqual(
            patient_client.get("/api/usuarios", headers=headers).status_code,
            403,
        )
        self.assertEqual(
            patient_client.get("/api/config", headers=headers).status_code,
            403,
        )

    def test_public_registration_cannot_create_admins_and_invalid_json_is_400(self):
        registration = self.app.test_client().post(
            "/api/cadastro",
            json={
                "nome": "Tentativa admin",
                "email": f"admin-{uuid4().hex}@example.com",
                "senha": "minha-senha",
                "tipo": "admin",
            },
        )
        malformed = self.app.test_client().post(
            "/api/cadastro",
            data="[",
            content_type="application/json",
        )
        self.assertEqual(registration.status_code, 403)
        self.assertEqual(malformed.status_code, 400)

    def test_get_medicos(self):
        resp = self.client.get('/api/medicos')
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.get_json(), list)

    def test_patient_and_doctor_update(self):
        patient = self.client.put(
            '/api/pacientes/3',
            json={'telefone': '(11) 90000-0000', 'id': 999},
        )
        self.assertEqual(patient.status_code, 200)
        self.assertEqual(patient.get_json()['id'], 3)
        self.assertEqual(patient.get_json()['telefone'], '(11) 90000-0000')

        doctor = self.client.put(
            '/api/medicos/2',
            json={'especialidade': 'Pediatria', 'id': 999},
        )
        self.assertEqual(doctor.status_code, 200)
        self.assertEqual(doctor.get_json()['id'], 2)
        self.assertEqual(doctor.get_json()['nome'], 'Dr. Altemar')
        self.assertEqual(doctor.get_json()['especialidade'], 'Pediatria')

    def test_complete_appointment_crud_and_conflict_validation(self):
        created = self.client.post(
            '/api/agendamentos',
            json={
                'pacienteId': 3,
                'medicoId': 4,
                'data': '2026-10-20',
                'hora': '09:30',
                'observacoes': 'Consulta de acompanhamento',
            },
        )
        self.assertEqual(created.status_code, 201)
        appointment = created.get_json()
        appointment_id = appointment['id']
        self.assertEqual(appointment['pacienteNome'], 'Sabrina')
        self.assertEqual(appointment['medicoNome'], 'Dra. Ana Souza')
        self.assertEqual(appointment['status'], 'agendado')

        fetched = self.client.get(f'/api/agendamentos/{appointment_id}')
        self.assertEqual(fetched.status_code, 200)
        self.assertEqual(fetched.get_json()['id'], appointment_id)

        conflict = self.client.post(
            '/api/agenda',
            json={
                'pacienteId': 3,
                'medicoId': 4,
                'data': '2026-10-20',
                'hora': '09:30',
            },
        )
        self.assertEqual(conflict.status_code, 409)

        updated = self.client.put(
            f'/api/agendamentos/{appointment_id}',
            json={'status': 'confirmado'},
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.get_json()['observacoes'], 'Consulta de acompanhamento')
        self.assertEqual(updated.get_json()['status'], 'confirmado')

        deleted = self.client.delete(f'/api/agendamentos/{appointment_id}')
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(
            self.client.get(f'/api/agendamentos/{appointment_id}').status_code,
            404,
        )

    def test_appointment_requires_existing_patient_doctor_and_slot(self):
        missing_fields = self.client.post('/api/agendamentos', json={})
        self.assertEqual(missing_fields.status_code, 400)

        missing_patient = self.client.post(
            '/api/agendamentos',
            json={
                'pacienteId': 999,
                'medicoId': 4,
                'data': '2026-10-20',
                'hora': '09:30',
            },
        )
        self.assertEqual(missing_patient.status_code, 404)

        missing_doctor = self.client.post(
            '/api/agendamentos',
            json={
                'pacienteId': 3,
                'medicoId': 999,
                'data': '2026-10-20',
                'hora': '09:30',
            },
        )
        self.assertEqual(missing_doctor.status_code, 404)

    def test_admin_crud(self):
        admins = self.client.get('/api/administradores')
        self.assertEqual(admins.status_code, 200)
        self.assertEqual([item['id'] for item in admins.get_json()], [1])
        self.assertNotIn('senha', admins.get_json()[0])

        created = self.client.post(
            '/api/administradores',
            json={
                'nome': 'Admin novo',
                'email': f'admin-{uuid4().hex}@example.com',
                'senha': 'senha-segura',
            },
        )
        self.assertEqual(created.status_code, 201)
        admin = created.get_json()['administrador']
        self.assertEqual(admin['tipoClinica'], 'admin')
        self.assertNotIn('senha', admin)

        updated = self.client.put(
            f"/api/administradores/{admin['id']}",
            json={'nome': 'Admin atualizado'},
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.get_json()['nome'], 'Admin atualizado')

        fetched = self.client.get(f"/api/administradores/{admin['id']}")
        self.assertEqual(fetched.status_code, 200)
        self.assertNotIn('senha', fetched.get_json())

        deleted = self.client.delete(f"/api/administradores/{admin['id']}")
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(
            self.client.get(f"/api/administradores/{admin['id']}").status_code,
            404,
        )

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

    def test_conversational_triage_persists_context_and_collects_preferences(self):
        patient_client = self.app.test_client()
        login = patient_client.post(
            "/api/login",
            json={"email": "sabrina@AgendaMed.com", "senha": "123456"},
        )
        headers = {"Authorization": f"Bearer {login.get_json()['token']}"}
        created = patient_client.post(
            "/api/triagem/conversas",
            json={},
            headers=headers,
        )
        self.assertEqual(created.status_code, 201)
        conversation_id = created.get_json()["id"]
        self.assertIn("não é um diagnóstico", created.get_json()["mensagens"][0]["conteudo"])

        first = patient_client.post(
            f"/api/triagem/conversas/{conversation_id}/mensagens",
            json={"mensagem": "Estou com dor de ouvido há 3 dias, piorando"},
            headers=headers,
        )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.get_json()["estado"], "safety_review")

        screened = patient_client.post(
            f"/api/triagem/conversas/{conversation_id}/mensagens",
            json={"mensagem": "não"},
            headers=headers,
        )
        self.assertEqual(screened.status_code, 200)
        self.assertEqual(screened.get_json()["aguardando"], "associados")
        self.assertEqual(screened.get_json()["dados"]["duracao"], "ha 3 dias")
        self.assertEqual(screened.get_json()["dados"]["evolucao"], "piorando")

        answered = patient_client.post(
            f"/api/triagem/conversas/{conversation_id}/mensagens",
            json={"mensagem": "nenhum outro sintoma"},
            headers=headers,
        )
        self.assertEqual(answered.status_code, 200)
        self.assertEqual(answered.get_json()["estado"], "triage_summary")
        self.assertIn(
            "Otorrinolaringologia",
            answered.get_json()["especialidades_sugeridas"][
                "sugeridas_preliminarmente"
            ],
        )
        self.assertIn("não é um diagnóstico", answered.get_json()["resumo"])

        confirmation = patient_client.post(
            f"/api/triagem/conversas/{conversation_id}/mensagens",
            json={"mensagem": "sim"},
            headers=headers,
        )
        self.assertEqual(confirmation.get_json()["aguardando"], "data_desejada")

        invalid_date = patient_client.post(
            f"/api/triagem/conversas/{conversation_id}/mensagens",
            json={"mensagem": "10/11/2026"},
            headers=headers,
        )
        self.assertEqual(invalid_date.status_code, 400)

        valid_date = (date.today() + timedelta(days=10)).isoformat()
        date_response = patient_client.post(
            f"/api/triagem/conversas/{conversation_id}/mensagens",
            json={"mensagem": valid_date},
            headers=headers,
        )
        self.assertEqual(date_response.status_code, 200)
        self.assertEqual(date_response.get_json()["aguardando"], "periodo")

        period = patient_client.post(
            f"/api/triagem/conversas/{conversation_id}/mensagens",
            json={"mensagem": "manhã"},
            headers=headers,
        )
        self.assertEqual(period.get_json()["aguardando"], "modalidade")

        modality = patient_client.post(
            f"/api/triagem/conversas/{conversation_id}/mensagens",
            json={"mensagem": "online"},
            headers=headers,
        )
        saved = modality.get_json()
        self.assertEqual(saved["estado"], "pending_matchmaking")
        self.assertEqual(
            saved["matchmaking"]["estado"],
            "pending_matchmaking",
        )
        self.assertFalse(saved["matchmaking"]["agendamento_confirmado"])
        self.assertFalse(
            saved["matchmaking"]["verificacao_disponibilidade_realizada"]
        )
        self.assertEqual(saved["preferencias"]["modalidade"], "online")

        fetched = patient_client.get(
            f"/api/triagem/conversas/{conversation_id}",
            headers=headers,
        )
        self.assertEqual(fetched.status_code, 200)
        self.assertEqual(len(fetched.get_json()["mensagens"]), 16)
        self.assertEqual(
            patient_client.get(
                "/api/triagem/conversas",
                headers=headers,
            ).get_json()[0]["id"],
            conversation_id,
        )
        self.assertEqual(
            patient_client.post(
                f"/api/triagem/conversas/{conversation_id}/mensagens",
                json={"mensagem": "continuar"},
                headers=headers,
            ).status_code,
            409,
        )

    def test_conversational_triage_detects_urgent_signals_and_stops_flow(self):
        created = self.client.post(
            "/api/triagem/conversas",
            json={"pacienteId": 3},
        )
        conversation_id = created.get_json()["id"]
        response = self.client.post(
            f"/api/triagem/conversas/{conversation_id}/mensagens",
            json={
                "mensagem": (
                    "Estou com pressão no peito e falta de ar agora"
                )
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["estado"], "urgent_referral")
        self.assertTrue(response.get_json()["dados"]["sinais_alerta"])
        last_message = response.get_json()["mensagens"][-1]["conteudo"]
        self.assertIn("192", last_message)
        self.assertNotIn("diagnóstico", last_message)
        self.assertEqual(
            self.client.patch(
                f"/api/triagem/conversas/{conversation_id}",
                json={"correcoes": {"queixa_principal": "dor leve"}},
            ).status_code,
            409,
        )

    def test_conversational_triage_answers_questions_without_losing_symptoms(self):
        created = self.client.post(
            "/api/triagem/conversas",
            json={"pacienteId": 3},
        )
        conversation_id = created.get_json()["id"]
        endpoint = (
            f"/api/triagem/conversas/{conversation_id}/mensagens"
        )

        greeting = self.client.post(
            endpoint,
            json={"mensagem": "Oi"},
        ).get_json()
        self.assertEqual(greeting["aguardando"], "queixa_principal")
        self.assertIn("assistente virtual", greeting["mensagens"][-1]["conteudo"])

        medication_question = self.client.post(
            endpoint,
            json={"mensagem": "Qual remédio posso tomar?"},
        ).get_json()
        self.assertEqual(
            medication_question["aguardando"],
            "queixa_principal",
        )
        self.assertIn(
            "não posso indicar remédios",
            medication_question["mensagens"][-1]["conteudo"].casefold(),
        )

        clarification = self.client.post(
            endpoint,
            json={"mensagem": "Pode repetir?"},
        ).get_json()
        self.assertEqual(clarification["aguardando"], "queixa_principal")
        self.assertIn("principal motivo", clarification["mensagens"][-1]["conteudo"])

        symptom_question = self.client.post(
            endpoint,
            json={
                "mensagem": (
                    "Estou com dor de ouvido há 3 dias, pode me dizer "
                    "o que eu tenho?"
                )
            },
        ).get_json()
        self.assertEqual(symptom_question["aguardando"], "safety_screen")
        self.assertIn("dor de ouvido", symptom_question["dados"]["queixa_principal"])
        self.assertIn(
            "agradeço",
            symptom_question["mensagens"][-1]["conteudo"],
        )

        urgent_question = self.client.post(
            endpoint,
            json={"mensagem": "Estou com dor no peito e falta de ar"},
        ).get_json()
        self.assertEqual(urgent_question["estado"], "urgent_referral")
        self.assertIn("192", urgent_question["mensagens"][-1]["conteudo"])

    def test_conversational_triage_adapts_questions_and_accepts_corrections(self):
        created = self.client.post(
            "/api/triagem/conversas",
            json={"pacienteId": 3},
        )
        conversation_id = created.get_json()["id"]
        first = self.client.post(
            f"/api/triagem/conversas/{conversation_id}/mensagens",
            json={
                "mensagem": (
                    "Tenho dor abdominal há 2 dias, intensidade 5 de 10 "
                    "e está melhorando"
                )
            },
        ).get_json()
        self.assertEqual(first["aguardando"], "safety_screen")
        self.assertEqual(first["dados"]["duracao"], "ha 2 dias")
        self.assertEqual(first["dados"]["intensidade"], "5/10")
        self.assertEqual(first["dados"]["evolucao"], "melhorando")

        after_safety = self.client.post(
            f"/api/triagem/conversas/{conversation_id}/mensagens",
            json={"mensagem": "não"},
        ).get_json()
        self.assertEqual(after_safety["aguardando"], "associados")

        summary = self.client.post(
            f"/api/triagem/conversas/{conversation_id}/mensagens",
            json={"mensagem": "nenhum"},
        ).get_json()
        self.assertEqual(summary["estado"], "triage_summary")

        corrected = self.client.patch(
            f"/api/triagem/conversas/{conversation_id}",
            json={
                "correcoes": {
                    "localizacao": "lado direito do abdômen",
                    "evolucao": "continua igual",
                }
            },
        )
        self.assertEqual(corrected.status_code, 200)
        self.assertEqual(
            corrected.get_json()["dados"]["localizacao"],
            "lado direito do abdômen",
        )
        self.assertEqual(
            corrected.get_json()["dados"]["evolucao"],
            "continua igual",
        )

    def test_conversational_triage_limits_access_and_requires_authentication(self):
        anonymous = self.app.test_client()
        self.assertEqual(
            anonymous.post("/api/triagem/conversas", json={}).status_code,
            401,
        )
        patient_client = self.app.test_client()
        patient_login = patient_client.post(
            "/api/login",
            json={"email": "sabrina@AgendaMed.com", "senha": "123456"},
        )
        patient_headers = {
            "Authorization": f"Bearer {patient_login.get_json()['token']}"
        }
        created = patient_client.post(
            "/api/triagem/conversas",
            json={},
            headers=patient_headers,
        )
        self.assertEqual(created.status_code, 201)
        conversation_id = created.get_json()["id"]

        another_registration = self.client.post(
            "/api/cadastro",
            json={
                "nome": "Paciente de teste",
                "email": f"triagem-{uuid4().hex}@example.com",
                "senha": "senha-segura",
                "tipo": "paciente",
            },
        )
        another_client = self.app.test_client()
        another_login = another_client.post(
            "/api/login",
            json={
                "email": another_registration.get_json()["usuario"]["email"],
                "senha": "senha-segura",
            },
        )
        another_headers = {
            "Authorization": f"Bearer {another_login.get_json()['token']}"
        }
        self.assertEqual(
            another_client.get(
                f"/api/triagem/conversas/{conversation_id}",
                headers=another_headers,
            ).status_code,
            403,
        )
        self.assertEqual(
            patient_client.delete(
                f"/api/triagem/conversas/{conversation_id}",
                headers=patient_headers,
            ).status_code,
            200,
        )

    def test_triage_specialty_suggestion_requires_a_registered_match(self):
        self.repository.collections["especialidades"] = []
        self.repository.collections["medicos"] = []
        created = self.client.post(
            "/api/triagem/conversas",
            json={"pacienteId": 3},
        )
        conversation_id = created.get_json()["id"]
        self.client.post(
            f"/api/triagem/conversas/{conversation_id}/mensagens",
            json={"mensagem": "Minha pele está com coceira há 2 dias"},
        )
        self.client.post(
            f"/api/triagem/conversas/{conversation_id}/mensagens",
            json={"mensagem": "não"},
        )
        response = self.client.post(
            f"/api/triagem/conversas/{conversation_id}/mensagens",
            json={"mensagem": "nenhum"},
        )
        for _ in range(8):
            if response.get_json()["estado"] == "triage_summary":
                break
            response = self.client.post(
                f"/api/triagem/conversas/{conversation_id}/mensagens",
                json={"mensagem": "não sei"},
            )
        self.assertEqual(response.get_json()["estado"], "triage_summary")
        suggestions = response.get_json()["especialidades_sugeridas"]
        self.assertEqual(suggestions["sugeridas_preliminarmente"], [])
        self.assertEqual(suggestions["cadastradas_no_sistema"], [])
        self.assertIn(
            "não há correspondência de especialidade confirmada",
            response.get_json()["resumo"].lower(),
        )

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
        self.assertIn(
            email.lower(),
            [user['email'].lower() for user in self.client.get('/api/usuarios').get_json()],
        )
        self.assertIn(
            email.lower(),
            [patient['email'].lower() for patient in self.client.get('/api/pacientes').get_json()],
        )

        agenda = self.client.post('/api/agenda', json={
            'pacienteId': 3,
            'medicoId': 2,
            'data': '2099-09-25',
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
            'data': '2099-09-30',
            'hora': '10:00'
        })
        agendamento_id = novo_agendamento.get_json()['id']
        self.assertEqual(self.client.delete(f'/api/agenda/{agendamento_id}').status_code, 200)

    def test_clinica_crud_contract(self):
        criada = self.client.post('/api/clinicas', json={'nome': 'Clínica Teste'})
        self.assertEqual(criada.status_code, 201)
        clinica = criada.get_json()
        encontrada = self.client.get(f"/api/clinicas/{clinica['id']}")
        self.assertEqual(encontrada.status_code, 200)
        self.assertEqual(encontrada.get_json()['nome'], 'Clínica Teste')

        atualizada_put = self.client.put(
            f"/api/clinicas/{clinica['id']}",
            json={'nome': 'Clínica Atualizada por PUT'},
        )
        self.assertEqual(atualizada_put.status_code, 200)
        self.assertEqual(
            atualizada_put.get_json()['nome'],
            'Clínica Atualizada por PUT',
        )

        atualizada = self.client.post('/api/clinicas', json={**clinica, 'nome': 'Clínica Atualizada'})
        self.assertEqual(atualizada.status_code, 200)
        self.assertEqual(atualizada.get_json()['nome'], 'Clínica Atualizada')
        self.assertEqual(self.client.delete(f"/api/clinicas/{clinica['id']}").status_code, 200)
        self.assertEqual(
            self.client.get(f"/api/clinicas/{clinica['id']}").status_code,
            404,
        )

    def test_specialty_crud_and_role_restrictions(self):
        specialties_url = "/api/especialidades"
        created = self.client.post(
            specialties_url,
            json={"nome": "Dermatologia", "descricao": "Especialidade teste"},
        )
        self.assertEqual(created.status_code, 201)
        specialty_id = created.get_json()["id"]

        self.assertEqual(self.client.get(specialties_url).status_code, 200)
        fetched = self.client.get(f"{specialties_url}/{specialty_id}")
        self.assertEqual(fetched.status_code, 200)
        self.assertEqual(fetched.get_json()["nome"], "Dermatologia")

        updated = self.client.patch(
            f"{specialties_url}/{specialty_id}",
            json={"descricao": "Descrição atualizada"},
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(
            updated.get_json()["descricao"],
            "Descrição atualizada",
        )

        deleted = self.client.delete(f"{specialties_url}/{specialty_id}")
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(
            self.client.get(f"{specialties_url}/{specialty_id}").status_code,
            404,
        )

        patient_client = self.app.test_client()
        patient_login = patient_client.post(
            "/api/login",
            json={"email": "sabrina@AgendaMed.com", "senha": "123456"},
        )
        patient_headers = {
            "Authorization": f"Bearer {patient_login.get_json()['token']}"
        }
        denied = patient_client.post(
            specialties_url,
            json={"nome": "Não autorizado"},
            headers=patient_headers,
        )
        self.assertEqual(denied.status_code, 403)

    def test_history_crud_requires_admin(self):
        history_url = "/api/historico"
        created = self.client.post(
            history_url,
            json={"descricao": "Evento para teste", "tipo": "consulta"},
        )
        self.assertEqual(created.status_code, 201)
        history_id = created.get_json()["id"]

        fetched = self.client.get(f"{history_url}/{history_id}")
        self.assertEqual(fetched.status_code, 200)
        self.assertEqual(fetched.get_json()["descricao"], "Evento para teste")

        updated = self.client.put(
            f"{history_url}/{history_id}",
            json={"descricao": "Evento atualizado", "id": 999},
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.get_json()["id"], history_id)
        self.assertEqual(updated.get_json()["descricao"], "Evento atualizado")

        deleted = self.client.delete(f"{history_url}/{history_id}")
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(
            self.client.get(f"{history_url}/{history_id}").status_code,
            404,
        )

    def test_global_settings_crud(self):
        settings_url = "/api/config"
        self.assertEqual(self.client.get(settings_url).get_json()["tema"], "light")

        replaced = self.client.put(
            settings_url,
            json={"idioma": "pt-BR"},
        )
        self.assertEqual(replaced.status_code, 200)
        self.assertEqual(replaced.get_json(), {"idioma": "pt-BR"})

        patched = self.client.patch(
            settings_url,
            json={"notificacoes": False},
        )
        self.assertEqual(patched.status_code, 200)
        self.assertEqual(patched.get_json()["idioma"], "pt-BR")
        self.assertFalse(patched.get_json()["notificacoes"])

        deleted = self.client.delete(settings_url)
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(self.client.get(settings_url).get_json(), {})
        self.assertEqual(self.client.delete(settings_url).status_code, 404)

    def test_user_settings_crud_is_limited_to_owner_or_admin(self):
        settings_url = "/api/configuracoes-usuario"
        patient_client = self.app.test_client()
        patient_login = patient_client.post(
            "/api/login",
            json={"email": "sabrina@AgendaMed.com", "senha": "123456"},
        )
        patient_headers = {
            "Authorization": f"Bearer {patient_login.get_json()['token']}"
        }

        created = patient_client.post(
            settings_url,
            json={"tema": "escuro", "notificacoes": True},
            headers=patient_headers,
        )
        self.assertEqual(created.status_code, 201)
        setting_id = created.get_json()["id"]
        self.assertEqual(created.get_json()["usuarioId"], 3)

        self.assertEqual(
            patient_client.get(settings_url, headers=patient_headers).get_json(),
            [created.get_json()],
        )
        fetched = patient_client.get(
            f"{settings_url}/{setting_id}",
            headers=patient_headers,
        )
        self.assertEqual(fetched.status_code, 200)

        updated = patient_client.patch(
            f"{settings_url}/{setting_id}",
            json={"tema": "claro", "usuarioId": 1},
            headers=patient_headers,
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.get_json()["tema"], "claro")
        self.assertEqual(updated.get_json()["usuarioId"], 3)

        second_registration = self.client.post(
            "/api/cadastro",
            json={
                "nome": "Outro paciente",
                "email": f"outro-{uuid4().hex}@example.com",
                "senha": "senha-segura",
                "tipo": "paciente",
            },
        )
        self.assertEqual(second_registration.status_code, 201)
        second_client = self.app.test_client()
        second_login = second_client.post(
            "/api/login",
            json={
                "email": second_registration.get_json()["usuario"]["email"],
                "senha": "senha-segura",
            },
        )
        second_headers = {
            "Authorization": f"Bearer {second_login.get_json()['token']}"
        }
        self.assertEqual(
            second_client.get(
                f"{settings_url}/{setting_id}",
                headers=second_headers,
            ).status_code,
            403,
        )

        self.assertEqual(
            self.client.get(settings_url).status_code,
            200,
        )
        self.assertIn(
            setting_id,
            [item["id"] for item in self.client.get(settings_url).get_json()],
        )
        self.assertEqual(
            patient_client.delete(
                f"{settings_url}/{setting_id}",
                headers=patient_headers,
            ).status_code,
            200,
        )
        self.assertEqual(
            patient_client.get(
                f"{settings_url}/{setting_id}",
                headers=patient_headers,
            ).status_code,
            404,
        )


class MongoRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.collections = {
            name: MagicMock()
            for name in (
                "usuarios",
                "pacientes",
                "medicos",
                "clinicas",
                "especialidades",
                "agendamentos",
                "configuracoes",
                "configuracoes_usuario",
                "logs",
                "triagens",
            )
        }
        self.repository = MongoRepository(SimpleNamespace(**self.collections))

    def test_lists_records_from_existing_database_collections(self):
        self.collections["medicos"].find.return_value = [
            {"_id": "mongo-id", "id": 7, "nome": "Médico"}
        ]

        records = self.repository.get_all("medicos")

        self.assertEqual(records, [{"id": 7, "nome": "Médico"}])
        self.collections["medicos"].find.assert_called_once_with({})

    def test_inserts_accounts_and_appointments_into_mapped_collections(self):
        account = {"id": 8, "nome": "Paciente"}
        appointment = {"id": 9, "pacienteId": 8, "medicoId": 4}

        self.repository.insert("usuarios", account)
        self.collections["usuarios"].insert_one.assert_called_once_with(account)

        self.repository.insert("agendamentos", appointment)
        self.collections["agendamentos"].insert_one.assert_called_once_with(
            appointment
        )

    def test_maps_api_history_and_settings_to_existing_collections(self):
        self.repository.get_all("historico")
        self.collections["logs"].find.assert_called_once_with({})

        self.collections["configuracoes"].find_one.return_value = None
        self.repository.get_document("config")
        self.collections["configuracoes"].find_one.assert_called_once_with()

    def test_updates_the_existing_global_settings_document(self):
        self.collections["configuracoes"].find_one.return_value = {
            "_id": "settings-id"
        }
        settings = {"tema": "dark", "notificacoes": False}

        self.repository.save_document("config", settings)

        self.collections["configuracoes"].update_one.assert_called_once_with(
            {"_id": "settings-id"},
            {"$set": settings},
        )

    def test_replaces_and_deletes_singleton_settings_document(self):
        collection = self.collections["configuracoes"]
        collection.find_one.return_value = {"_id": "settings-id", "old": True}
        replacement = {"_id": "settings-id", "tema": "dark"}

        self.repository.replace_document("config", replacement)

        collection.replace_one.assert_called_once_with(
            {"_id": "settings-id"},
            replacement,
        )
        collection.delete_one.return_value.deleted_count = 1
        self.assertTrue(self.repository.delete_document("config"))
        collection.delete_one.assert_called_once_with({})

    def test_updates_and_deletes_only_the_record_with_matching_numeric_id(self):
        record = {"id": 12, "nome": "Dra. Nova"}
        self.collections["medicos"].find_one.return_value = {
            "_id": "mongo-id",
            **record,
        }
        replace_result = self.collections["medicos"].replace_one.return_value
        replace_result.modified_count = 0
        replace_result.matched_count = 1

        self.repository.replace("medicos", record)
        self.collections["medicos"].replace_one.assert_called_once_with(
            {"_id": "mongo-id"},
            {"_id": "mongo-id", **record},
        )

        self.collections["medicos"].delete_one.return_value.deleted_count = 1
        self.assertTrue(self.repository.delete("medicos", 12))
        self.collections["medicos"].delete_one.assert_called_once_with(
            {"id": 12}
        )

    def test_object_id_documents_are_serialized_with_api_id(self):
        from bson import ObjectId

        object_id = ObjectId()
        self.collections["pacientes"].find_one.return_value = {
            "_id": object_id,
            "nome": "Paciente legado",
        }
        patient = self.repository.get_by_id("pacientes", str(object_id))
        self.assertEqual(patient, {"id": str(object_id), "nome": "Paciente legado"})


class DatabaseModuleTests(unittest.TestCase):
    @patch("repositories.database_module.MongoClient")
    def test_connects_to_remote_database_without_local_database_project(
        self, mongo_client
    ):
        database = MagicMock()
        mongo_client.return_value.__getitem__.return_value = database

        with patch.dict(
            os.environ,
            {"DATABASE_PROJECT_PATH": r"C:\old\local\database"},
        ):
            module = load_database_module(
                mongo_uri="mongodb+srv://example.invalid",
                db_name="callmed_test",
            )

        mongo_client.assert_called_once_with("mongodb+srv://example.invalid")
        mongo_client.return_value.__getitem__.assert_called_once_with(
            "callmed_test"
        )
        self.assertIs(module.client, mongo_client.return_value)
        self.assertIs(module.db, database)
        for collection_name in (
            "usuarios",
            "pacientes",
            "medicos",
            "clinicas",
            "especialidades",
            "agendamentos",
            "configuracoes",
            "configuracoes_usuario",
            "logs",
            "triagens",
        ):
            self.assertIs(
                getattr(module, collection_name),
                database.__getitem__.return_value,
            )
        self.assertEqual(database.__getitem__.call_count, 10)


if __name__ == '__main__':
    unittest.main()
