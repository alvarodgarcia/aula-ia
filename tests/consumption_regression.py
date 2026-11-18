import asyncio,io,json,os,unittest,wave
from pathlib import Path
from unittest.mock import patch
import httpx
from fastapi.testclient import TestClient
import security_regression as fixture
from app import accounting
main=fixture.main

class ConsumptionTests(unittest.TestCase):
    def setUp(self):
        self.f=fixture.ResourceSecurityTests('test_valid_voice_and_invalid_csrf');self.f.setUp()
        self.student=self.f.client;self.pid=self.f.profile_id;self.token=self.f.token
        self.admin=TestClient(main.app,follow_redirects=False)
        t=fixture.csrf(self.admin.get('/login'))
        self.admin.post('/login',data={'password':'Test-only-adult-9385','csrf_token':t})
        self.at=fixture.csrf(self.admin.get('/'))
        self.calls=[]
    def tearDown(self):self.admin.close();self.f.tearDown()
    def mock(self,handler):
        client=httpx.AsyncClient
        return patch.object(httpx,'AsyncClient',lambda **kw:client(transport=httpx.MockTransport(handler),**kw))
    def provider(self,request):
        self.calls.append(request);body=json.loads(request.content)
        content={'decision':'apoyo'} if 'Actúa como revisor' in body['messages'][0]['content'] else {'decision':'apoyo','reply':'Prueba a agrupar las unidades.','exercise':None}
        return httpx.Response(200,json={'choices':[{'message':{'content':json.dumps(content)}}],'usage':{'prompt_tokens':100,'completion_tokens':30,'prompt_tokens_details':{'cached_tokens':20}}})
    def ask(self):return self.student.post('/mis-tareas/tutor',data={'csrf_token':self.token,'question':'Explícame las sumas'})
    def budget(self,tokens,block=True,scope=0):
        return self.admin.post('/consumo/limites',data={'scope_id':scope,'monthly_tokens':tokens,'block':str(block).lower(),'csrf_token':self.at})
    def test_student_attribution_internal_calls_and_no_duplicate(self):
        with self.mock(self.provider):self.assertEqual(self.ask().status_code,303)
        self.assertEqual(len(self.calls),2)
        data=accounting.report('mes');self.assertEqual(data['totals']['input']+data['totals']['output'],260)
        with main.db_session() as db:
            rows=db.scalars(main.select(accounting.Consumption)).all()
            self.assertEqual(len(rows),2);self.assertTrue(all(r.profile_id==self.pid and r.actor=='student' for r in rows))
            self.assertTrue(all(r.cached_tokens==20 for r in rows))
        self.assertEqual(accounting.context.get(),(None,'unknown'))
        self.assertIn('max_completion_tokens',json.loads(self.calls[0].content))
    def test_global_and_per_student_blocks_happen_before_network(self):
        self.assertEqual(self.budget(1).status_code,303)
        with self.mock(self.provider):self.assertEqual(self.ask().status_code,303)
        self.assertEqual(len(self.calls),0)
        self.assertIn('presupuesto mensual',self.student.get('/mis-tareas').text)
        with main.db_session() as db:
            self.assertEqual(db.scalar(main.select(main.func.count()).select_from(main.StudentAudit).where(main.StudentAudit.uses_quota.is_(True))),0)
        self.budget(0);self.budget(1,scope=self.pid)
        with self.mock(self.provider):self.ask()
        self.assertEqual(len(self.calls),0)
    def test_warning_mode_does_not_block_and_adult_is_attributed(self):
        self.budget(1,False)
        with self.mock(self.provider):
            self.ask()
            self.admin.post(f'/supervision/{self.pid}/lectura',data={'book':'Obra de prueba','csrf_token':self.at})
        self.assertEqual(len(self.calls),3)
        with main.db_session() as db:
            adults=db.scalars(main.select(accounting.Consumption).where(accounting.Consumption.actor=='adult')).all()
            self.assertEqual(len(adults),1);self.assertEqual(adults[0].profile_id,self.pid)
        page=self.admin.get('/consumo');self.assertEqual(page.status_code,200)
        self.assertIn('Presupuesto alcanzado',page.text)
        if os.getenv('AULA_PREVIEW_DIR'):
            Path(os.environ['AULA_PREVIEW_DIR'],'consumo-adulto.html').write_text(page.text,encoding='utf-8')
    def test_usage_survives_invalid_tutor_content_and_unknown_usage(self):
        def invalid(request):return httpx.Response(200,json={'choices':[{'message':{'content':'not JSON'}}],'usage':{'prompt_tokens':10,'completion_tokens':5}})
        with self.mock(invalid):self.ask()
        self.assertEqual(accounting.report('mes')['totals']['text_tokens'],15)
        def unknown(request):return httpx.Response(200,json={'choices':[{'message':{'content':'not JSON'}}]})
        with self.mock(unknown):self.ask()
        data=accounting.report('mes');self.assertEqual(data['totals']['text_tokens'],15)
        self.assertGreater(data['totals']['reserved'],0);self.assertEqual(data['totals']['unknown'],1)
    def test_old_usage_is_retained_without_inventing_profile(self):
        with main.db_session() as db:
            db.add(main.AIUsage(provider='openai',model='old',task='old',input_tokens=70,output_tokens=30,cost_usd=0.01,elapsed_ms=10));db.commit()
        data=accounting.report('todo');self.assertEqual(data['totals']['text_tokens'],100);self.assertEqual(data['legacy_count'],1)
        self.assertIsNone(data['rows'][0]['profile_id'])
        self.assertEqual(accounting.report('todo',self.pid)['totals']['text_tokens'],0)
    def test_access_csrf_and_filters(self):
        self.assertEqual(self.student.get('/consumo').status_code,403)
        self.assertEqual(self.student.post('/consumo/limites',data={'scope_id':0,'monthly_tokens':1,'csrf_token':self.token}).status_code,403)
        self.assertEqual(self.admin.post('/consumo/limites',data={'scope_id':0,'monthly_tokens':1,'csrf_token':'invalid'}).status_code,403)
        self.assertEqual(self.admin.get('/consumo?perfil=9999').status_code,404)
        self.assertEqual(self.admin.get('/consumo?periodo=invalid').status_code,400)
        self.assertEqual(self.admin.post('/consumo/limites',data={'scope_id':0,'monthly_tokens':-1,'csrf_token':self.at}).status_code,422)
    def test_audio_duration_and_azure_units_are_not_tokens(self):
        tok=accounting.context.set((self.pid,'student'))
        try:
            with self.mock(lambda r:httpx.Response(200,json={'text':'Una nota','usage':{'type':'duration','seconds':12.5}})):
                self.assertEqual(asyncio.run(main.voice.transcribe_class_audio(b'test','.wav','test-key')),'Una nota')
            out=io.BytesIO()
            with wave.open(out,'wb') as w:w.setparams((1,2,24000,0,'NONE','not compressed'));w.writeframes(b'\0\0'*2400)
            with patch.dict(os.environ,{'TUTOR_VOICE_PROVIDER':'azure','AZURE_SPEECH_REGION':'northeurope','AZURE_SPEECH_KEY':'test-key'}),self.mock(lambda r:httpx.Response(200,content=out.getvalue())):
                asyncio.run(main.voice.azure_voice.synthesize('Cinco veces doce.','nora','teen','test-key'))
        finally:accounting.context.reset(tok)
        data=accounting.report('mes');self.assertEqual(data['totals']['seconds'],12.5)
        self.assertEqual(data['totals']['azure_chars'],17);self.assertEqual(data['totals']['input']+data['totals']['output'],0)
        self.assertEqual(data['totals']['unknown'],1)
    def test_timeout_keeps_uncertain_reservation_and_rejection_releases_it(self):
        def timeout(request):raise httpx.ReadTimeout('simulated timeout',request=request)
        with self.mock(timeout):self.ask()
        self.assertGreater(accounting.report('mes')['totals']['reserved'],0)
        before=accounting.report('mes')['totals']['reserved']
        with self.mock(lambda request:httpx.Response(401,json={'error':'invalid key'})):self.ask()
        self.assertEqual(accounting.report('mes')['totals']['reserved'],before)
    def test_partial_provider_counts_do_not_double_the_reservation(self):
        t=accounting.context.set((self.pid,'student'))
        try:
            event=accounting.begin('text','openai','test','test',reserved_tokens=100)
            accounting.finish(event,usage={'input_tokens':30})
            with main.db_session() as db:self.assertEqual(accounting.spent(db,self.pid),100)
            data=accounting.report('mes');self.assertEqual(data['totals']['reserved'],70)
            self.assertEqual(data['totals']['unknown'],1)
        finally:accounting.context.reset(t)

    def test_concurrent_requests_keep_their_own_pupil(self):
        from concurrent.futures import ThreadPoolExecutor
        with main.db_session() as db:
            p=main.Profile(name='Otro perfil',age=14,stage='ESO',cycle='1.º ciclo',course='3.º');db.add(p);db.flush();other_id=p.id
            salt='33'*16
            db.add(main.StudentAccess(profile_id=p.id,pin_salt=salt,pin_hash=main.pin_digest('123456',salt),session_version='other'))
            db.add(main.StudentLoginCode(profile_id=p.id,code='OTHER1234567'));db.commit()
        other=TestClient(main.app,follow_redirects=False)
        try:
            t=fixture.csrf(other.get('/login/alumno'))
            other.post('/login/alumno',data={'login_code':'OTHER1234567','pin':'123456','csrf_token':t})
            token=fixture.csrf(other.get('/mis-tareas'))
            with self.mock(self.provider),ThreadPoolExecutor(max_workers=2) as pool:
                first=pool.submit(self.ask)
                second=pool.submit(other.post,'/mis-tareas/tutor',data={'csrf_token':token,'question':'Explícame una suma'})
                self.assertEqual(first.result().status_code,303);self.assertEqual(second.result().status_code,303)
            data=accounting.report('mes');counts={r['profile_id']:r['text_tokens'] for r in data['rows']}
            self.assertEqual(counts,{self.pid:260,other_id:260})
        finally:other.close()

    def test_outstanding_reservations_cannot_oversubscribe(self):
        self.budget(100)
        token=accounting.context.set((self.pid,'student'))
        try:
            first=accounting.begin('text','openai','test','test',reserved_tokens=60)
            with self.assertRaises(accounting.BudgetExceeded):accounting.begin('text','openai','test','test',reserved_tokens=60)
            accounting.finish(first,usage={'input_tokens':20,'output_tokens':10})
            second=accounting.begin('text','openai','test','test',reserved_tokens=60)
            accounting.fail(second)
            self.assertEqual(accounting.report('mes')['totals']['reserved'],60)
        finally:accounting.context.reset(token)

if __name__=='__main__':
    try:unittest.main(verbosity=2)
    finally:main.engine.dispose();fixture._workspace.cleanup()
