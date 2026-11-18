import asyncio
import hashlib
import io
import os
import unittest
import wave
from datetime import datetime,timezone
from unittest.mock import AsyncMock,patch
from xml.etree import ElementTree as ET

import httpx
from fastapi.testclient import TestClient
import security_regression as fixtures
main,csrf,_workspace=fixtures.main,fixtures.csrf,fixtures._workspace
from app import azure_voice,voice


def wav_bytes():
    out=io.BytesIO()
    with wave.open(out,'wb') as w:
        w.setparams((1,2,24000,0,'NONE','not compressed'));w.writeframes(b'\0\0'*100)
    return out.getvalue()


class AzureVoiceTests(unittest.TestCase):
    def setUp(self):
        self.env=patch.dict(os.environ,{'TUTOR_VOICE_PROVIDER':'azure','AZURE_SPEECH_REGION':'westeurope','AZURE_SPEECH_KEY':'test-azure-key-for-mocked-requests'})
        self.env.start()
        self.fixture=fixtures.ResourceSecurityTests('test_valid_voice_and_invalid_csrf');self.fixture.setUp()
        self.client=self.fixture.client;self.profile_id=self.fixture.profile_id;self.token=self.fixture.token
        self.admin=TestClient(main.app,follow_redirects=False)
        token=csrf(self.admin.get('/login'))
        self.assertEqual(self.admin.post('/login',data={'password':'Test-only-adult-9385','csrf_token':token}).status_code,303)
        self.admin_token=csrf(self.admin.get('/'))

    def tearDown(self):
        self.admin.close();self.fixture.tearDown();self.env.stop()

    def speak(self,text='Cinco veces doce, paso a paso.',character='nora'):
        return self.client.post('/tutor/voz',data={'csrf_token':self.token,'character':character,'text':text,'signature':voice.voice_signature(self.profile_id,text)})

    def mock_transport(self,handler):
        real=httpx.AsyncClient
        return patch.object(httpx,'AsyncClient',lambda **kw:real(transport=httpx.MockTransport(handler),**kw))

    def test_three_regional_voices_and_xml_escaping(self):
        requests=[]
        def provider(request):
            requests.append(request)
            self.assertEqual(str(request.url),'https://westeurope.tts.speech.microsoft.com/cognitiveservices/v1')
            self.assertEqual(request.headers['ocp-apim-subscription-key'],'test-azure-key-for-mocked-requests')
            self.assertEqual(request.headers['x-microsoft-outputformat'],'riff-24khz-16bit-mono-pcm')
            root=ET.fromstring(request.content)
            self.assertEqual(root.attrib['{http://www.w3.org/XML/1998/namespace}lang'],'es-ES')
            self.assertEqual(''.join(root.itertext()),'Cinco < doce & siete > tres. </voice><audio src="https://example.invalid"/>')
            self.assertFalse(root.findall('.//{http://www.w3.org/2001/10/synthesis}audio'))
            return httpx.Response(200,content=wav_bytes())
        text='Cinco < doce & siete > tres. </voice><audio src="https://example.invalid"/>'
        with self.mock_transport(provider):
            for character in voice.VOICES:
                response=self.speak(text,character)
                self.assertEqual(response.status_code,200)
                self.assertEqual(response.headers['x-aula-voice-provider'],'azure')
        self.assertEqual([ET.fromstring(r.content)[0].attrib['name'] for r in requests],list(azure_voice.VOICES.values()))

    def test_repeat_is_cached_and_provider_identity_is_separate(self):
        calls=[]
        def provider(request):calls.append(request);return httpx.Response(200,content=wav_bytes())
        with self.mock_transport(provider):
            self.assertEqual(self.speak().status_code,200);self.assertEqual(self.speak().status_code,200)
        self.assertEqual(len(calls),1)
        azure_id=voice.cache_identity('nora')
        with patch.dict(os.environ,{'TUTOR_VOICE_PROVIDER':'openai'}):self.assertNotEqual(azure_id,voice.cache_identity('nora'))
        self.assertTrue(voice.voice_api_key()) # OpenAI transcription remains configured.

    def test_monthly_bound_stops_before_provider_and_covers_preview(self):
        month=datetime.now(timezone.utc).strftime('%Y-%m')
        bucket=hashlib.sha256(f'azure-voice-month:{month}'.encode()).hexdigest()
        with main.db_session() as db:
            db.add(main.SecurityThrottle(bucket=bucket,window_start=datetime.now(timezone.utc),requests=399999));db.commit()
        with patch.object(azure_voice,'synthesize',new=AsyncMock()) as synth:
            self.assertEqual(self.speak().status_code,429)
            result=self.admin.post('/admin/voz/prueba',data={'csrf_token':self.admin_token,'profile_id':self.profile_id,'character':'lumo'})
            self.assertEqual(result.status_code,429);self.assertEqual(synth.await_count,0)

    def test_preview_is_adult_only_and_secrets_are_not_rendered(self):
        payload={'csrf_token':self.token,'profile_id':self.profile_id,'character':'nora'}
        with patch.object(azure_voice,'synthesize',new=AsyncMock(return_value=wav_bytes())) as synth:
            self.assertEqual(self.client.post('/admin/voz/prueba',data=payload).status_code,403)
            self.assertEqual(self.admin.post('/admin/voz/prueba',data={**payload,'csrf_token':'invalid'}).status_code,403)
            response=self.admin.post('/admin/voz/prueba',data={**payload,'csrf_token':self.admin_token})
            self.assertEqual(response.status_code,200);self.assertEqual(synth.await_count,1)
            self.assertTrue(synth.call_args.args[0].startswith('Hola, soy Nora.'))
        page=self.admin.get('/')
        self.assertIn('Probar las voces del tutor',page.text)
        self.assertNotIn('test-azure-key-for-mocked-requests',page.text)
        self.assertNotIn('test-azure-key-for-mocked-requests',self.admin.get('/privacidad').text)
        from pathlib import Path
        if os.getenv('AULA_PREVIEW_DIR'):
            Path(os.environ['AULA_PREVIEW_DIR'],'azure-panel-adulto.html').write_text(page.text,encoding='utf-8')
            Path(os.environ['AULA_PREVIEW_DIR'],'azure-alumno.html').write_text(self.client.get('/mis-tareas').text,encoding='utf-8')

    def test_provider_failure_has_no_openai_fallback(self):
        with self.mock_transport(lambda r:httpx.Response(401,content=b'no')),patch.object(voice,'connect') as realtime:
            self.assertEqual(self.speak().status_code,502);realtime.assert_not_called()

    def test_invalid_region_missing_configuration_and_non_audio(self):
        with patch.dict(os.environ,{'AZURE_SPEECH_REGION':'evil.example/path'}):
            self.assertFalse(voice.synthesis_ready())
            with self.assertRaises(ValueError):azure_voice.region()
        with self.mock_transport(lambda r:httpx.Response(200,content=b'not audio')):
            self.assertEqual(self.speak().status_code,502)


if __name__=='__main__':
    try:unittest.main(verbosity=2)
    finally:main.engine.dispose();_workspace.cleanup()
