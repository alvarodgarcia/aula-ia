import io,json,os,unittest,wave
from pathlib import Path
from unittest.mock import patch
import httpx
import english_regression as fixture
main=fixture.main


def wav(seconds=1,rate=16000):
    out=io.BytesIO()
    with wave.open(out,'wb') as w:w.setparams((1,2,rate,0,'NONE','not compressed'));w.writeframes(b'\0\0'*int(seconds*rate))
    return out.getvalue()


class PronunciationTests(unittest.TestCase):
    def setUp(self):
        self.f=fixture.EnglishTests('test_specialist_turn_help_progress_and_accounting');self.f.setUp()
        self.student,self.admin,self.pid,self.token,self.at=self.f.student,self.f.admin,self.f.pid,self.f.token,self.f.at
        self.env=patch.dict(os.environ,{'AZURE_SPEECH_KEY':'test-azure-key','AZURE_SPEECH_REGION':'northeurope'});self.env.start()
        self.calls=[]
    def tearDown(self):self.env.stop();self.f.tearDown()
    def enable(self,scope=0,minutes=240,attempts=10,enabled='true'):
        return self.admin.post('/pronunciacion/limites',data={'csrf_token':self.at,'scope_id':scope,'monthly_minutes':minutes,'daily_attempts':attempts,'enabled':enabled})
    def assess(self,payload=None,**extra):
        data={'csrf_token':self.token,'phrase_id':'hello'};data.update(extra)
        return self.student.post('/mis-tareas/ingles/pronunciacion/evaluar',data=data,files={'audio':('reading.wav',payload if payload is not None else wav(),'audio/wav')})
    def provider(self,request):
        import base64
        self.calls.append(request)
        config=json.loads(base64.b64decode(request.headers['Pronunciation-Assessment']))
        self.assertEqual(config['ReferenceText'],main.pronunciation.PHRASES['hello'])
        self.assertFalse(config['EnableProsodyAssessment']);self.assertEqual(config['Granularity'],'Word')
        self.assertEqual(request.url.host,'northeurope.stt.speech.microsoft.com')
        self.assertEqual(request.url.params['language'],'en-GB')
        return httpx.Response(200,json={'RecognitionStatus':'Success','NBest':[{'AccuracyScore':82,'FluencyScore':76,'CompletenessScore':90,'PronScore':80,'Words':[{'Word':'Hello','AccuracyScore':82,'ErrorType':'None'},{'Word':'friends','AccuracyScore':55,'ErrorType':'Mispronunciation'}]}]})
    def mock(self,handler):return self.f.f.mock(handler)
    def test_disabled_by_default_and_settings_are_adult_only(self):
        with self.mock(self.provider):self.assertEqual(self.assess().status_code,429)
        self.assertEqual(self.calls,[])
        self.assertEqual(self.enable().status_code,303)
        self.assertEqual(self.student.post('/pronunciacion/limites',data={'csrf_token':self.token,'scope_id':0,'monthly_minutes':240}).status_code,403)
        self.assertEqual(self.admin.post('/pronunciacion/limites',data={'csrf_token':'bad','scope_id':0,'monthly_minutes':240}).status_code,403)
        self.assertEqual(self.enable(minutes=241).status_code,422)
    def test_canonical_audio_bounds_before_provider_and_quota(self):
        self.enable()
        with self.mock(self.provider):
            for audio in (b'not a wav',wav(21),wav(1,8000),wav()[:-100]):self.assertEqual(self.assess(audio).status_code,422)
        self.assertEqual(self.calls,[])
        self.assertEqual(main.pronunciation.overview(self.pid)['daily_used'],0)
    def test_recorded_result_locale_and_independent_consumption(self):
        self.enable()
        with self.mock(self.provider):response=self.assess(wav(20))
        self.assertEqual(response.status_code,200);self.assertEqual(response.json()['result']['accuracy'],82)
        overview=main.pronunciation.overview(self.pid)
        self.assertEqual(overview['family_used'],20);self.assertEqual(overview['child_used'],20)
        self.assertEqual(overview['recent'][0]['status'],'ok')
        totals=main.accounting.report('mes')['providers']['azure']['totals']
        self.assertEqual(totals['pronunciation_seconds'],20);self.assertEqual(totals['azure_chars'],0)
        self.assertEqual(totals['pronunciation_calls'],1)
        page=self.student.get('/mis-tareas/ingles?activity=pronunciation');self.assertEqual(page.status_code,200)
        self.assertIn('Grabar mi lectura',page.text)
        self.assertIn('friends',json.dumps(overview['recent'][0]['result']))
        if os.getenv('AULA_PREVIEW_DIR'):
            Path(os.environ['AULA_PREVIEW_DIR'],'pronunciacion-alumno.html').write_text(page.text,encoding='utf-8')
            Path(os.environ['AULA_PREVIEW_DIR'],'pronunciacion-adulto.html').write_text(self.admin.get('/').text,encoding='utf-8')
    def test_csrf_unknown_phrase_and_profile_claims(self):
        self.enable()
        with self.mock(self.provider):
            self.assertEqual(self.assess(csrf_token='bad').status_code,403)
            self.assertEqual(self.assess(phrase_id='custom text').status_code,400)
            self.assertEqual(self.assess(profile_id=9999,reference='malicious',locale='en-US').status_code,200)
        self.assertEqual(main.pronunciation.overview(self.pid)['daily_used'],1)
        self.assertEqual(len(self.calls),1)
    def test_daily_child_and_family_limits_reserve_before_network(self):
        self.enable();self.enable(self.pid,attempts=1)
        with self.mock(self.provider):self.assertEqual(self.assess().status_code,200);self.assertEqual(self.assess().status_code,429)
        self.assertEqual(len(self.calls),1)
        self.enable(self.pid,minutes=1,attempts=10);self.enable(minutes=1)
        first=main.pronunciation.reserve(self.pid,'en-GB','test',20)
        second=main.pronunciation.reserve(self.pid,'en-GB','test',20)
        with self.assertRaises(main.pronunciation.LimitReached):main.pronunciation.reserve(self.pid,'en-GB','test',20)
        self.assertEqual(main.pronunciation.overview(self.pid)['family_used'],41)
    def test_network_failure_and_no_match_keep_local_reservations(self):
        self.enable()
        def timeout(request):raise httpx.ReadTimeout('mock timeout',request=request)
        with self.mock(timeout):self.assertEqual(self.assess(wav(2)).status_code,502)
        with self.mock(lambda r:httpx.Response(200,json={'RecognitionStatus':'NoMatch'})):self.assertEqual(self.assess(wav(2)).status_code,502)
        data=main.pronunciation.overview(self.pid);self.assertEqual(data['family_used'],4)
        self.assertTrue(all(a['status']=='error' for a in data['recent']))
    def test_english_pause_and_general_ai_pause_stop_evaluation(self):
        self.enable();self.f.config(enabled='false')
        with self.mock(self.provider):self.assertEqual(self.assess().status_code,403)
        self.f.config()
        with main.db_session() as db:
            db.get(main.StudentTutorPolicy,self.pid).daily_limit=0;db.commit()
        with self.mock(self.provider):self.assertEqual(self.assess().status_code,429)
        self.assertEqual(self.calls,[])
    def test_listening_json_and_post_redirect_play_only_new_turn(self):
        body={'csrf_token':self.token,'study_mode':'english','activity':'listening','question':'Prepare a listening practice.'}
        with self.f.f.mock(self.f.provider):result=self.student.post('/mis-tareas/tutor',data=body,headers={'Accept':'application/json'})
        self.assertEqual(result.status_code,200);self.assertEqual(result.json()['locale'],'en-GB')
        self.assertTrue(result.json()['signature']);self.assertEqual(result.json()['count'],1)
        with self.f.f.mock(self.f.provider):result=self.student.post('/mis-tareas/tutor',data=body)
        self.assertEqual(result.status_code,303)
        self.assertIn('data-auto-read="yes"',self.student.get(result.headers['location']).text)
        self.assertIn('data-auto-read="no"',self.student.get(result.headers['location']).text)
    def test_missing_and_non_finite_scores_are_not_fabricated(self):
        with self.assertRaises(ValueError):main.pronunciation.assessment_result({'RecognitionStatus':'Success','NBest':[{'AccuracyScore':float('nan')}]},'en-GB')
        result=main.pronunciation.assessment_result({'RecognitionStatus':'Success','NBest':[{'AccuracyScore':80}]},'en-GB')
        self.assertIsNone(result['overall']);self.assertIsNone(result['fluency'])
    def test_family_reservations_are_shared_between_concurrent_profiles(self):
        from concurrent.futures import ThreadPoolExecutor
        self.enable(minutes=1)
        def reserve(profile_id):
            try:return main.pronunciation.reserve(profile_id,'en-GB','test',20)
            except main.pronunciation.LimitReached:return None
        with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(reserve,[self.pid,self.pid+1,self.pid+2,self.pid+3]))
        self.assertEqual(sum(value is not None for value in results),3)
        self.assertEqual(main.pronunciation.overview()['family_used'],60)
    def test_us_phonemes_are_retained_but_not_invented_for_british(self):
        data={'RecognitionStatus':'Success','NBest':[{'AccuracyScore':80,'Words':[{'Word':'hello','AccuracyScore':80,'Phonemes':[{'Phoneme':'h','AccuracyScore':70}]}]}]}
        self.assertEqual(main.pronunciation.assessment_result(data,'en-US')['words'][0]['sounds'],[{'name':'h','accuracy':70.0}])
        self.assertEqual(main.pronunciation.assessment_result(data,'en-GB')['words'][0]['sounds'],[])
    def test_listening_quota_failure_returns_json_without_call(self):
        with main.db_session() as db:db.get(main.StudentTutorPolicy,self.pid).daily_limit=0;db.commit()
        with self.f.f.mock(self.f.provider):result=self.student.post('/mis-tareas/tutor',data={'csrf_token':self.token,'study_mode':'english','activity':'listening','question':'Start a practice'},headers={'Accept':'application/json'})
        self.assertEqual(result.status_code,429);self.assertIn('error',result.json());self.assertEqual(self.f.calls,[])


if __name__=='__main__':
    try:unittest.main(verbosity=2)
    finally:main.engine.dispose();fixture.fixture.fixture._workspace.cleanup()
