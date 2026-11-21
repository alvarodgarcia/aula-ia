import asyncio
import os
from pathlib import Path
import re
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
_workspace = TemporaryDirectory(prefix='aula-security-')
os.environ.update(DATABASE_URL='sqlite:///' + str(Path(_workspace.name) / 'test.db'),
                  DATA_DIR=str(Path(_workspace.name) / 'data'), APP_ADMIN_PASSWORD='Test-only-adult-9385',
                  APP_SESSION_SECRET='test-only-session-secret-' * 3, APP_COOKIE_SECURE='false',
                  APP_PUBLIC='false', APP_ALLOWED_HOSTS='', OPENAI_API_KEY='test-key',
                  AI_PROVIDER='openai', AI_BASE_URL='https://api.openai.com/v1')
from fastapi.testclient import TestClient
from app import main


def csrf(response):
    return re.search(r'name="csrf_token" value="([^"]+)"', response.text)[1]


class ResourceSecurityTests(unittest.TestCase):
    def setUp(self):
        main.pronunciation.Base.metadata.drop_all(main.engine)
        main.accounting.Base.metadata.drop_all(main.engine)
        main.Base.metadata.drop_all(main.engine)
        self.client = TestClient(main.app, follow_redirects=False)
        self.client.__enter__()
        with main.db_session() as db:
            profile = main.Profile(name='Prueba', age=15, stage='ESO', cycle='2.º ciclo', course='4.º')
            db.add(profile)
            db.flush()
            self.profile_id = profile.id
            salt = '11' * 16
            db.add(main.StudentAccess(profile_id=profile.id, pin_salt=salt,
                pin_hash=main.pin_digest('123456', salt), session_version='test-version'))
            db.add(main.StudentLoginCode(profile_id=profile.id, code='TEST12345678'))
            db.add(main.StudentTutorPolicy(profile_id=profile.id, daily_limit=2))
            db.commit()
        result = self.client.post('/login/alumno', data={
            'login_code':'TEST12345678', 'pin':'123456', 'csrf_token':csrf(self.client.get('/login/alumno'))})
        self.assertEqual(result.status_code,303)
        self.token = csrf(self.client.get('/mis-tareas'))

    def tearDown(self):
        self.client.__exit__(None,None,None)

    def voice_turn(self):
        return self.client.post('/tutor/conversacion',data={'csrf_token':self.token,'character':'nora'},
                                files={'audio':('turn.wav',b'test-audio','audio/wav')})

    def upload(self):
        return self.client.post('/mis-tareas/clase/material',data={
            'csrf_token':self.token,'day':main.learning.school_day(),'subject':'Ciencias','topic':'Repaso'},
            files={'file':('apuntes.pdf',b'%PDF-test','application/pdf')})

    def test_silence_is_bounded_even_when_pedagogical_quota_is_refunded(self):
        with patch.object(main.voice,'transcribe_class_audio',new=AsyncMock(return_value='')) as provider:
            for _ in range(6):
                self.assertEqual(self.voice_turn().status_code,422)
            self.assertEqual(self.voice_turn().status_code,429)
            self.assertEqual(provider.await_count,6)
            # Dictation shares the paid transcription budget.
            result=self.client.post('/mis-tareas/clase/transcribir',data={'csrf_token':self.token},
                files={'audio':('turn.wav',b'test-audio','audio/wav')})
            self.assertEqual(result.status_code,429)
            self.assertEqual(provider.await_count,6)

    def test_valid_voice_and_invalid_csrf(self):
        with patch.object(main.voice,'transcribe_class_audio',new=AsyncMock(return_value='Hola')) as provider, \
             patch.object(main,'student_tutor_answer',new=AsyncMock(return_value=('Vamos paso a paso.',None,None))):
            self.assertEqual(self.voice_turn().status_code,200)
            self.assertEqual(provider.await_count,1)
            result=self.client.post('/tutor/conversacion',data={'csrf_token':'invalid','character':'nora'},
                files={'audio':('turn.wav',b'test-audio','audio/wav')})
            self.assertEqual(result.status_code,403)
            self.assertEqual(provider.await_count,1)

    def test_withdrawn_materials_and_package_members_count_toward_storage(self):
        with main.db_session() as db:
            note=main.ClassNote(profile_id=self.profile_id,day=main.learning.school_day(),subject='A',topic='B',notes='C',
                attachment=main.ClassAttachment(filename='old.pdf',is_photo=False,data=b'x'*600000,moderation='withdrawn',
                    files=[main.MaterialFile(filename='part.pdf',is_photo=False,data=b'y'*500000)]))
            db.add(note)
            db.commit()
        with patch.dict(os.environ,{'APP_STUDENT_STORAGE_MB':'1'}), \
             patch.object(main,'read_study_material',new=AsyncMock()) as reader:
            self.assertEqual(self.upload().status_code,413)
            self.assertEqual(reader.await_count,0)

    def test_upload_limit_is_checked_against_new_package_before_commit(self):
        material=main.ReadMaterial('one.pdf',False,'[Página 1]\nMaterial de prueba',b'x'*600000,1)
        with patch.dict(os.environ,{'APP_STUDENT_STORAGE_MB':'1'}), \
             patch.object(main,'read_study_material',new=AsyncMock(return_value=([material,material],[]))):
            self.assertEqual(self.upload().status_code,413)
        with main.db_session() as db:
            self.assertEqual(db.scalar(main.select(main.func.count()).select_from(main.ClassAttachment)),0)

    def test_upload_frequency_before_ocr_and_normal_multi_file_upload(self):
        material=main.ReadMaterial('one.pdf',False,'[Página 1]\nMaterial de prueba',b'%PDF-test',1)
        with patch.dict(os.environ,{'APP_STUDENT_UPLOADS_PER_HOUR':'2'}), \
             patch.object(main,'read_study_material',new=AsyncMock(return_value=([material,material],[]))) as reader:
            self.assertEqual(self.upload().status_code,303)
            self.assertEqual(self.upload().status_code,303)
            self.assertEqual(self.upload().status_code,429)
            self.assertEqual(reader.await_count,2)
        with main.db_session() as db:
            self.assertEqual(db.scalar(main.select(main.func.count()).select_from(main.MaterialFile)),4)


if __name__=='__main__':
    try:
        unittest.main(verbosity=2)
    finally:
        main.engine.dispose()
        _workspace.cleanup()
