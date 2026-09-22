import unittest
from uuid import uuid4

from app import app


class BackendTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

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
            'pacienteNome': 'João da Silva',
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


if __name__ == '__main__':
    unittest.main()
